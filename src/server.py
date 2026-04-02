"""
server.py — FastAPI backend for the RAG pipeline.

Run from the project root:
    uvicorn src.server:app --reload --port 8000
"""

import asyncio
import json
import os
import sys
import uuid
import shutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

sys.path.insert(0, os.path.dirname(__file__))

from chunker      import chunk_pages
from config       import PDF_DIR
from embedder     import embed_chunks, load_model
from generator    import generate
from pdf_loader   import load_pdfs
from retriever    import load_reranker, retrieve
from vector_store import get_collection, store_chunks

# ── Rate limiter ───────────────────────────────────────────────────────────────
# Reads X-Forwarded-For when behind a proxy (Nginx, Caddy), falls back to direct IP.

def _get_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host  # type: ignore[union-attr]


limiter = Limiter(key_func=_get_ip)

# ── Paths ──────────────────────────────────────────────────────────────────────

_ROOT = Path(__file__).parent.parent
_DIST = _ROOT / "frontend" / "dist"
_DATA = _ROOT / PDF_DIR


# ── Startup / shutdown ─────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading RAG pipeline…")
    app.state.pipeline      = await asyncio.to_thread(_load_pipeline)
    app.state.inference_sem = asyncio.Semaphore(1)  # serialise CPU inference
    app.state.ingest_lock   = asyncio.Lock()         # prevent concurrent writes
    app.state.jobs: dict[str, dict] = {}
    print("Pipeline ready.\n")
    yield


def _load_pipeline() -> dict:
    """Load all models and open the vector store. Runs in a thread at startup."""
    import torch
    physical_cores = max(1, (os.cpu_count() or 2) // 2)
    torch.set_num_threads(physical_cores)
    return {
        "embed_model": load_model(),
        "reranker":    load_reranker(),
        "collection":  get_collection(),
    }


# ── App ────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Docs RAG", lifespan=lifespan)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev server
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.get("/api/status")
@limiter.limit("60/minute")
def api_status(request: Request):
    col   = request.app.state.pipeline["collection"]
    count = col.count()
    docs  = sorted(f.name for f in _DATA.glob("*.pdf")) if _DATA.exists() else []
    return {"chunks": count, "ready": count > 0, "docs": docs}


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)


@app.post("/api/query")
@limiter.limit("10/minute;60/hour;200/day")
async def api_query(req: QueryRequest, request: Request):
    pipeline = request.app.state.pipeline
    sem      = request.app.state.inference_sem

    # Retrieve — CPU-bound, serialised by semaphore
    async with sem:
        hits = await asyncio.to_thread(
            retrieve,
            query_text  = req.question,
            embed_model = pipeline["embed_model"],
            collection  = pipeline["collection"],
            reranker    = pipeline["reranker"],
        )

    async def event_stream():
        if not hits:
            yield _sse({"type": "error", "text": "No relevant documents found."})
            return

        # Emit sources first so the UI can render citations straight away
        sources = [{"source": h["source"], "page": h["page"]} for h in hits]
        yield _sse({"type": "sources", "sources": sources})

        # Bridge the synchronous generator → async via asyncio.Queue +
        # call_soon_threadsafe (no thread blocked on q.get; no extra thread consumed)
        q:    asyncio.Queue = asyncio.Queue()
        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

        def _run() -> None:
            try:
                for delta in generate(req.question, hits):
                    loop.call_soon_threadsafe(q.put_nowait, delta)
            except Exception as exc:
                loop.call_soon_threadsafe(q.put_nowait, exc)
            finally:
                loop.call_soon_threadsafe(q.put_nowait, None)  # sentinel

        loop.run_in_executor(None, _run)

        while True:
            item = await q.get()
            if item is None:
                yield _sse({"type": "done"})
                break
            if isinstance(item, Exception):
                yield _sse({"type": "error", "text": str(item)})
                break
            yield _sse({"type": "delta", "text": item})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/ingest")
@limiter.limit("3/minute;10/hour")
async def api_ingest(request: Request, files: list[UploadFile] = File(...)):
    _DATA.mkdir(exist_ok=True)

    for upload in files:
        if not (upload.filename or "").lower().endswith(".pdf"):
            raise HTTPException(400, f"'{upload.filename}' is not a PDF.")
        dest    = _DATA / (upload.filename or "upload.pdf")
        content = await upload.read()
        dest.write_bytes(content)

    job_id = str(uuid.uuid4())
    request.app.state.jobs[job_id] = {"status": "pending", "detail": "Queued"}

    asyncio.create_task(_run_ingest(request.app, job_id))
    return {"job_id": job_id}


@app.get("/api/ingest/status/{job_id}")
@limiter.limit("60/minute")
def api_ingest_status(job_id: str, request: Request):
    job = request.app.state.jobs.get(job_id)
    if not job:
        raise HTTPException(404, "Job not found.")
    return job


async def _run_ingest(app: FastAPI, job_id: str) -> None:
    async with app.state.ingest_lock:
        app.state.jobs[job_id] = {"status": "running", "detail": "Ingesting…"}
        try:
            embed_model = app.state.pipeline["embed_model"]
            collection  = app.state.pipeline["collection"]

            def _ingest():
                pages  = load_pdfs()
                chunks = chunk_pages(pages)
                chunks = embed_chunks(chunks, embed_model)
                store_chunks(chunks, collection)

            await asyncio.to_thread(_ingest)
            app.state.jobs[job_id] = {"status": "done", "detail": "Complete"}

        except Exception as exc:
            app.state.jobs[job_id] = {"status": "error", "detail": str(exc)}


# ── Serve built frontend (production) ─────────────────────────────────────────
# API routes must be registered BEFORE mounting StaticFiles, or it intercepts them.

if _DIST.exists():
    _assets = _DIST / "assets"
    if _assets.exists():
        app.mount("/assets", StaticFiles(directory=str(_assets)), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str):
        return FileResponse(_DIST / "index.html")


# ── Helpers ────────────────────────────────────────────────────────────────────

def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"

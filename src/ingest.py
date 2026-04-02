"""
ingest.py — Orchestrates the full data ingestion pipeline.

Usage:
    python ingest.py

Drop your PDF files into the `data/` folder, then run this script.
The vector store will be saved to `vector_store/` and is ready
to be queried by the retrieval layer.

Pipeline:
    PDF files  →  pages  →  chunks  →  embeddings  →  Chroma vector store
"""

import sys
import os

# make src/ importable when running from the project root
sys.path.insert(0, os.path.dirname(__file__))

from pdf_loader  import load_pdfs
from chunker     import chunk_pages
from embedder    import load_model, embed_chunks
from vector_store import get_collection, store_chunks


def run_pipeline():
    print("=" * 55)
    print("  RAG Ingestion Pipeline")
    print("=" * 55)

    # ── Step 1: Load PDFs ──────────────────────────────────
    print("\n[Step 1/4] Loading PDFs …")
    pages = load_pdfs()

    # ── Step 2: Chunk pages ────────────────────────────────
    print("[Step 2/4] Chunking text …")
    chunks = chunk_pages(pages)

    # ── Step 3: Embed chunks ───────────────────────────────
    print("[Step 3/4] Generating embeddings …")
    model  = load_model()
    chunks = embed_chunks(chunks, model)

    # ── Step 4: Store in Chroma ────────────────────────────
    print("[Step 4/4] Storing in vector database …")
    collection = get_collection()
    store_chunks(chunks, collection)

    print("=" * 55)
    print("  Ingestion complete! Vector store is ready.")
    print("=" * 55)

    return model, collection   # returned so the query demo below can reuse them


if __name__ == "__main__":
    model, collection = run_pipeline()

    # ── Quick sanity-check query ───────────────────────────
    from vector_store import query_store

    print("\n--- Sanity check: test query ---")
    test_query = input("Enter a test question (or press Enter to skip): ").strip()

    if test_query:
        hits = query_store(test_query, model, collection, top_k=3)
        print(f"\nTop {len(hits)} results:\n")
        for i, hit in enumerate(hits, 1):
            print(f"  [{i}] score={hit['score']}  source={hit['source']}  page={hit['page']}")
            print(f"      {hit['text'][:200]} …\n")

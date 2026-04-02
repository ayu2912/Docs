# ─────────────────────────────────────────────
# config.py  —  Central config for the RAG pipeline
# Tweak these values to customise behaviour.
# ─────────────────────────────────────────────

# ── Paths ──────────────────────────────────────
PDF_DIR          = "data"          # folder where PDFs are placed
VECTOR_STORE_DIR = "vector_store"  # Chroma persists here

# ── Chunking ────────────────────────────────────
# Token-based sizing (tiktoken cl100k_base); falls back to chars/4 if tiktoken absent.
# Research: 400-token chunks with 15% overlap optimal for factoid/QA queries.
CHUNK_SIZE    = 200   # tokens per chunk
CHUNK_OVERLAP = 30    # overlap tokens (~15% of chunk size)

# ── Embedding model ─────────────────────────────
# BAAI/bge-base-en-v1.5: MTEB retrieval score 53.3 vs all-MiniLM-L6-v2's ~41.
# 512-token context (vs MiniLM's 256), 768-dim vectors, 109M params.
EMBEDDING_MODEL  = "BAAI/bge-base-en-v1.5"
EMBED_BATCH_SIZE = 8   # CPU-optimal; 32+ is for GPU

# ── Chroma / HNSW index ─────────────────────────
# WARNING: HNSW params are frozen at collection-creation time.
# Delete vector_store/ and re-ingest if you change these.
#
# M=32, ef_construction=200 → "balanced production" profile from OpenSearch benchmark
# targeting ~97% recall@5.
COLLECTION_NAME      = "pdf_rag"
HNSW_M               = 32    # connections per node; higher = better recall, larger index
HNSW_EF_CONSTRUCTION = 200   # candidate list size at build time; governs graph quality
HNSW_EF_SEARCH       = 100   # candidate list size at query time; primary recall lever

# ── Retrieval ────────────────────────────────────
TOP_K       = 5    # number of chunks to return per query
CANDIDATE_K = 20   # ANN over-fetch before reranking (must be ≥ 2×TOP_K)
MMR_LAMBDA  = 0.7  # relevance weight in MMR (1.0 = pure relevance, 0.0 = pure diversity)

# ── Reranker ─────────────────────────────────────
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"

# ── LLM (Claude via Anthropic API) ───────────────
LLM_MODEL       = "claude-haiku-4-5-20251001"
LLM_MAX_TOKENS  = 512
LLM_TEMPERATURE = 0.2

# ── Misc ─────────────────────────────────────────
VERBOSE_EMBED = False  # set True to show tqdm progress bar during embedding

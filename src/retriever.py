
import numpy as np
from sentence_transformers import CrossEncoder

from config import (
    CANDIDATE_K,
    MMR_LAMBDA,
    RERANKER_MODEL,
    TOP_K,
)
from embedder import embed_query

# Stage 1 — ANN candidate fetch


def _fetch_candidates(
    query_text:  str,
    embed_model,           
    collection,         
    candidate_k: int,
) -> list[dict]:
    
    query_vector = embed_query(query_text, embed_model)

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=candidate_k, 
        include=["documents", "metadatas", "distances", "embeddings"],
    )

    hits = []
    for doc, meta, dist, emb in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        results["embeddings"][0],
    ):
        hits.append({
            "text":      doc,
            "source":    meta["source"],
            "page":      meta["page"],
            "score":     round(1.0 - dist, 4), 
            "embedding": emb,
        })

    return hits


# Stage 2 

def _rerank(
    query_text: str,
    hits:       list[dict],
    reranker:   CrossEncoder,
) -> list[dict]:
    
    pairs  = [(query_text, h["text"]) for h in hits]
    scores = reranker.predict(pairs, show_progress_bar=False)

    for hit, score in zip(hits, scores):
        hit["rerank_score"] = float(score)

    hits.sort(key=lambda h: h["rerank_score"], reverse=True)
    return hits

# Stage 3 — MMR diversity filter


def _mmr(
    hits:  list[dict],
    top_n: int,
    lam:   float,
) -> list[dict]:

    if len(hits) <= top_n:
        return hits

    score_key = "rerank_score" if "rerank_score" in hits[0] else "score"

    raw    = np.array([h[score_key] for h in hits], dtype=np.float32)
    span   = raw.max() - raw.min()
    scores = (raw - raw.min()) / (span if span > 1e-9 else 1.0)

    embs = np.array([h["embedding"] for h in hits], dtype=np.float32)

    selected: list[int] = []
    remaining = list(range(len(hits)))

    # Seed with the top-ranked candidate
    seed = int(np.argmax(scores))
    selected.append(seed)
    remaining.remove(seed)

    while len(selected) < top_n and remaining:
        rem      = np.array(remaining)               
        sel_embs = embs[selected]                     

        max_sims   = (embs[rem] @ sel_embs.T).max(axis=1)
        mmr_scores = lam * scores[rem] - (1.0 - lam) * max_sims

        best_local = int(np.argmax(mmr_scores))
        best_idx   = int(rem[best_local])

        selected.append(best_idx)
        remaining.remove(best_idx)

    return [hits[i] for i in selected]


# Public API


def load_reranker(model_name: str = RERANKER_MODEL) -> CrossEncoder:
    
    print(f"  Loading re-ranker: {model_name}")
    reranker = CrossEncoder(model_name)
    print("  → Re-ranker ready\n")
    return reranker


def retrieve(
    query_text:  str,
    embed_model,                    
    collection,                     
    reranker:    CrossEncoder,      
    top_n:       int   = TOP_K,
    candidate_k: int   = CANDIDATE_K,
    mmr_lambda:  float = MMR_LAMBDA,
) -> list[dict]:
    
    if collection.count() == 0:
        print("  [retriever] Vector store is empty — run ingest.py first.")
        return []

    if candidate_k < top_n * 2:
        raise ValueError(
            f"candidate_k ({candidate_k}) must be ≥ 2×top_n ({top_n}). "
            "Too little over-fetch defeats reranking."
        )

    # Stage 1
    candidates = _fetch_candidates(query_text, embed_model, collection, candidate_k)

    # Stage 2
    candidates = _rerank(query_text, candidates, reranker)

    # Stage 3
    results = _mmr(candidates, top_n, lam=mmr_lambda)

    # Strip embeddings (not needed)
    for r in results:
        r.pop("embedding", None)

    return results


def format_context(hits: list[dict]) -> str:
    
    if not hits:
        return "No relevant context found."

    blocks = []
    for i, h in enumerate(hits, 1):
        header = f"[{i}] Source: {h['source']}, Page {h['page']}"
        blocks.append(f"{header}\n{h['text']}")

    return "\n\n---\n\n".join(blocks)

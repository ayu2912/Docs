import chromadb
from config import (
    VECTOR_STORE_DIR,
    COLLECTION_NAME,
    HNSW_M,
    HNSW_EF_CONSTRUCTION,
    HNSW_EF_SEARCH,
    TOP_K,
)


def get_collection(
    persist_dir:     str = VECTOR_STORE_DIR,
    collection_name: str = COLLECTION_NAME,
) -> chromadb.Collection:
    
    client = chromadb.PersistentClient(path=persist_dir)
    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={
            "hnsw:space":           "cosine",
            "hnsw:M":               HNSW_M,
            "hnsw:construction_ef": HNSW_EF_CONSTRUCTION,
            "hnsw:search_ef":       HNSW_EF_SEARCH,
        },
    )
    return collection


def store_chunks(chunks: list[dict], collection: chromadb.Collection) -> None:
  
    ids        = [c["chunk_id"]  for c in chunks]
    embeddings = [c["embedding"] for c in chunks]
    documents  = [c["text"]      for c in chunks]
    metadatas  = [{"source": c["source"], "page": c["page"]} for c in chunks]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=documents,
        metadatas=metadatas,
    )

    print(f"  → {len(chunks)} chunks upserted into collection '{collection.name}'")
    print(f"  → Total documents in store: {collection.count()}\n")


def query_store(
    query_text: str,
    model,
    collection: chromadb.Collection,
    top_k:      int = TOP_K,
) -> list[dict]:
  
    from embedder import embed_query
    query_vector = embed_query(query_text, model)

    results = collection.query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "text":   doc,
            "source": meta["source"],
            "page":   meta["page"],
            "score":  round(1 - dist, 4),   
        })

    # Sorting the highest similarity first
    hits.sort(key=lambda h: h["score"], reverse=True)
    return hits

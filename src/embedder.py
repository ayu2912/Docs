#forming the embeddings
from sentence_transformers import SentenceTransformer
from config import EMBEDDING_MODEL, EMBED_BATCH_SIZE, VERBOSE_EMBED

# BGE query-side task prefix (applied to queries only, not to ingested chunks)
_BGE_QUERY_PREFIX = "Represent this sentence for searching relevant passages: "


def load_model(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    print(f"  Loading embedding model: {model_name}")
    model = SentenceTransformer(model_name)
    print(f"   Model completed  (vector dim: {model.get_sentence_embedding_dimension()})\n")
    return model


def embed_chunks(
    chunks:     list[dict],
    model:      SentenceTransformer,
    batch_size: int = EMBED_BATCH_SIZE,
) -> list[dict]:
   
    texts = [c["text"] for c in chunks]
    print(f"  Embedding {len(texts)} chunks (batch_size={batch_size}) …")

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=VERBOSE_EMBED,  
        convert_to_numpy=True,
        normalize_embeddings=True,
    )

    for chunk, vector in zip(chunks, embeddings):
        chunk["embedding"] = vector.tolist()

    print(f"   Each vector has {len(embeddings[0])} dimensions.\n")
    return chunks


def embed_query(query_text: str, model: SentenceTransformer) -> list[float]:
   
    prefixed = _BGE_QUERY_PREFIX + query_text
    return model.encode(
        prefixed,
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).tolist()

"""
pipeline.py — End-to-end RAG query interface.

Loads all models once at startup, then runs the full pipeline for each query:

    query → retrieve() → generate() → streamed answer

Run interactively:
    python pipeline.py

Or import ask() into other scripts:
    from pipeline import ask
    answer = ask("What is the attention mechanism?")
"""

import os
import torch

from embedder import load_model
from generator import generate
from retriever import load_reranker, retrieve
from vector_store import get_collection


def build_pipeline() -> dict:
    """
    Load all models and open the vector store.
    Call once at startup — each component is reused across queries.
    """
    # Pin PyTorch to physical CPU cores only.
    # Hyper-threading hurts transformer inference — OpenMP threads fight for the
    # same execution units.  os.cpu_count() returns logical cores; // 2 gives physical.
    physical_cores = max(1, (os.cpu_count() or 2) // 2)
    torch.set_num_threads(physical_cores)

    print("Initialising RAG pipeline…\n")
    return {
        "embed_model": load_model(),
        "collection":  get_collection(),
        "reranker":    load_reranker(),
    }


def ask(question: str, pipeline: dict, stream: bool = True) -> str:
    """
    Run the full retrieval + generation pipeline for a single question.

    Args:
        question: Natural-language question string.
        pipeline: Dict returned by build_pipeline().
        stream:   If True, print tokens as they arrive and return full answer.
                  If False, return full answer silently.

    Returns:
        The complete answer string.
    """
    hits = retrieve(
        query_text  = question,
        embed_model = pipeline["embed_model"],
        collection  = pipeline["collection"],
        reranker    = pipeline["reranker"],
    )

    if not hits:
        msg = "No relevant documents found in the vector store."
        print(msg)
        return msg

    answer_parts = []
    for delta in generate(question, hits):
        if stream:
            print(delta, end="", flush=True)
        answer_parts.append(delta)

    if stream:
        print()   # newline after streamed output

    return "".join(answer_parts)


# ──────────────────────────────────────────────────────────────────────────────
# Interactive REPL
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    rag = build_pipeline()
    print("─" * 60)
    print("RAG pipeline ready. Type 'quit' to exit.\n")

    while True:
        try:
            query = input("Question: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not query:
            continue
        if query.lower() in {"quit", "exit", "q"}:
            print("Bye.")
            break

        print("\nAnswer: ", end="")
        ask(query, rag, stream=True)
        print()

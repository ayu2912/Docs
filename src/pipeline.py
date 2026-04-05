

import os
import torch

from embedder import load_model
from generator import generate
from retriever import load_reranker, retrieve
from vector_store import get_collection


def build_pipeline() -> dict:
  
    physical_cores = max(1, (os.cpu_count() or 2) // 2)
    torch.set_num_threads(physical_cores)

    print("Initialising RAG pipeline…\n")
    return {
        "embed_model": load_model(),
        "collection":  get_collection(),
        "reranker":    load_reranker(),
    }


def ask(question: str, pipeline: dict, stream: bool = True) -> str:
   
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
        print()   

    return "".join(answer_parts)


# Interactive REPL


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

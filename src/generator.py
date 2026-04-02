import os
from collections.abc import Generator

import anthropic
from dotenv import load_dotenv

from config import LLM_MAX_TOKENS, LLM_MODEL, LLM_TEMPERATURE
from retriever import format_context

load_dotenv()

# Prompt templates

_SYSTEM_PROMPT = """\
You are a precise question-answering assistant.
You are given numbered context passages retrieved from a document collection.
Answer the user's question using ONLY the information in those passages.
Cite every claim with its passage number in square brackets, e.g. [1] or [2][3].
If the passages do not contain enough information to answer, say:
"I don't have enough information in the provided context to answer that question."
Do not speculate or use knowledge outside the provided context.\
"""

_USER_TEMPLATE = """\
Context passages:
{context}

Question: {question}\
"""

def _build_messages(question: str, context: str) -> list[dict]:
    return [
        {
            "role": "user",
            "content": _USER_TEMPLATE.format(context=context, question=question),
        }
    ]

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
        if not api_key or api_key == "your-key-here":
            raise EnvironmentError(
                "ANTHROPIC_API_KEY is not set. "
                "Add your key to the .env file: ANTHROPIC_API_KEY=sk-ant-..."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client

# Public API

def generate(
    question: str,
    hits:     list[dict],
    model:    str = LLM_MODEL,
) -> Generator[str, None, None]:

    context  = format_context(hits)
    messages = _build_messages(question, context)
    client   = _get_client()

    last_exc: Exception | None = None
    for attempt in range(3):
        yielded = False
        try:
            with client.messages.stream(
                model=model,
                max_tokens=LLM_MAX_TOKENS,
                temperature=LLM_TEMPERATURE,
                system=_SYSTEM_PROMPT,
                messages=messages,
            ) as stream:
                for delta in stream.text_stream:
                    yielded = True
                    yield delta
            return   # clean completion — exit generator
        except anthropic.APIStatusError as exc:
            if exc.status_code in {429, 500, 529} and attempt < 2 and not yielded:
                last_exc = exc
                continue
            raise
        except anthropic.APIConnectionError as exc:
            if attempt < 2 and not yielded:
                last_exc = exc
                continue
            raise

    raise RuntimeError(
        f"generate() failed after 3 attempts. Last error: {last_exc}"
    ) from last_exc


def generate_sync(
    question: str,
    hits:     list[dict],
    model:    str = LLM_MODEL,
) -> str:
    return "".join(generate(question, hits, model=model))

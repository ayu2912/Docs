from config import CHUNK_SIZE, CHUNK_OVERLAP

# tokenizing
try:
    import tiktoken
    enc = tiktoken.get_encoding("cl100k_base")
    def _token_len(text: str) -> int:
        return len(enc.encode(text))
except ImportError:
    def _token_len(text: str) -> int:     # type: ignore[misc]
        return max(1, len(text) // 4)

SEPARATORS = ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""]


def split_recursive(
    text:       str,
    chunk_size: int,
    separators: list[str],
) -> list[str]:
    if _token_len(text) <= chunk_size:
        stripped = text.strip()
        return [stripped] if stripped else []

    sep = separators[0]
    tail_seps = separators[1:]

    if sep == "":
        # Last-resort hard cut: approximate chars-per-token as 4
        char_limit = chunk_size * 4
        return [text[i : i + char_limit].strip() for i in range(0, len(text), char_limit) if text[i : i + char_limit].strip()]

    parts = text.split(sep)
    chunks: list[str] = []
    current = ""

    for part in parts:
        candidate = (current + sep + part) if current else part

        if _token_len(candidate) <= chunk_size:
            current = candidate
        else:
            if current.strip():
                chunks.append(current.strip())
            # Part itself may be too large — recurse with next separator
            if _token_len(part) > chunk_size and tail_seps:
                chunks.extend(split_recursive(part, chunk_size, tail_seps))
                current = ""
            else:
                current = part

    if current.strip():
        chunks.append(current.strip())

    return chunks


def add_overlap(chunks: list[str], overlap_tokens: int) -> list[str]:
    if overlap_tokens <= 0 or len(chunks) <= 1:
        return chunks

    overlap_chars = overlap_tokens * 4
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        tail = chunks[i - 1][-overlap_chars:]
        result.append((tail + " " + chunks[i]).strip())

    return result

def chunk_pages(
    pages:      list[dict],
    chunk_size: int = CHUNK_SIZE,
    overlap:    int = CHUNK_OVERLAP,
) -> list[dict]:
    
    all_chunks: list[dict] = []

    for page in pages:
        raw = split_recursive(page["text"], chunk_size, SEPARATORS)
        raw = add_overlap(raw, overlap)

        for idx, chunk_text in enumerate(raw):
            all_chunks.append({
                "text":     chunk_text,
                "source":   page["source"],
                "page":     page["page"],
                "chunk_id": f"{page['source']}_p{page['page']}_c{idx}",
            })

    print(
        f"  → {len(all_chunks)} chunks created "
        f"(size≈{chunk_size} tokens, overlap≈{overlap} tokens)\n"
    )
    return all_chunks

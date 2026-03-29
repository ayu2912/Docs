import os
import re
import pymupdf4llm
from config import PDF_DIR


def _clean_text(text: str) -> str:
    text = re.sub(r"-\n", "", text)           
    text = re.sub(r" {2,}", " ", text)        
    text = re.sub(r"\n{3,}", "\n\n", text) 
    return text.strip()


def load_pdfs(pdf_dir: str = PDF_DIR) -> list[dict]:
    if not os.path.exists(pdf_dir):
        raise FileNotFoundError(f"PDF directory not found: '{pdf_dir}'")

    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith(".pdf")]

    if not pdf_files:
        raise ValueError(f"No PDF files found in '{pdf_dir}'")

    pages = []

    for filename in pdf_files:
        filepath = os.path.join(pdf_dir, filename)
        print(f"  Loading: {filename}")

        # page_chunks=True → returns a list of per-page dicts instead of one big string
        page_chunks = pymupdf4llm.to_markdown(filepath, page_chunks=True)

        for page_num, chunk in enumerate(page_chunks, start=1):
            text = _clean_text(chunk["text"])
            if not text:
                continue  # skip blank/image-only pages

            pages.append({
                "text":   text,
                "source": filename,
                "page":   page_num,
            })

    print(f"  → {len(pages)} pages extracted from {len(pdf_files)} PDF(s)\n")
    return pages

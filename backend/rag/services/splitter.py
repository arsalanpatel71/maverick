# Added this because we needed two chunking strategies and might swap between them.
# Will change to a better option (e.g. semantic splitting) in future — change CHUNKING_BACKEND to switch.
from __future__ import annotations

from typing import Literal

# Change this one line to switch backend: "manual" = word-based, "langchain" = character-based
CHUNKING_BACKEND: Literal["manual", "langchain"] = "langchain"


def split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """Split text into overlapping chunks using the configured backend."""
    if CHUNKING_BACKEND == "langchain":
        return _langchain_split(text, chunk_size, chunk_overlap)
    return _manual_split(text, chunk_size, chunk_overlap)


# ─── Manual (word-based sliding window) ──────────────────────────────────────


def _manual_split(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    words = text.split()

    if len(words) <= chunk_size:
        return [text]

    # Guard: overlap must be smaller than chunk to avoid infinite loop
    if chunk_overlap >= chunk_size:
        chunk_overlap = chunk_size // 2

    step = chunk_size - chunk_overlap
    if step <= 0:
        step = 1

    chunks: list[str] = []
    for i in range(0, len(words), step):
        chunk = " ".join(words[i : i + chunk_size])
        if chunk.strip():
            chunks.append(chunk)
        if i + chunk_size >= len(words):
            break

    return chunks


# ─── LangChain (character-based recursive) ───────────────────────────────────


def _langchain_split(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " ", ""],
    )
    return splitter.split_text(text)

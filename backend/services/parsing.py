"""Document parsing and chunking.

Supported inputs: .txt and .md (read as UTF-8 text).
Chunking: paragraph-aware sliding window sized in words, with overlap,
which keeps chunks around the 500-1,000 token range recommended for RAG.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import List

SUPPORTED_EXTENSIONS = {".txt", ".md"}

CHUNK_TARGET_WORDS = 220   # ~300 tokens
CHUNK_OVERLAP_WORDS = 40


class UnsupportedFileError(ValueError):
    pass


class CorruptedFileError(ValueError):
    pass


def parse_bytes(filename: str, raw: bytes) -> str:
    """Convert an uploaded file to raw text. Raises on unsupported/corrupted input."""
    ext = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in SUPPORTED_EXTENSIONS:
        raise UnsupportedFileError(
            f"Unsupported file type '{ext or 'none'}'. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    if b"\x00" in raw:
        raise CorruptedFileError(
            f"File '{filename}' contains binary data and cannot be indexed as text."
        )
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CorruptedFileError(
            f"File '{filename}' is not valid UTF-8 text and could not be parsed."
        ) from exc
    text = text.replace("\r\n", "\n").strip()
    if not text:
        raise CorruptedFileError(f"File '{filename}' contains no readable text.")
    return text


@dataclass
class Chunk:
    chunk_id: str
    text: str
    position: int  # order within the document


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def chunk_text(doc_id: str, text: str) -> List[Chunk]:
    """Paragraph-aware chunking with a word budget and overlap."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[Chunk] = []
    buffer: List[str] = []
    buffer_words = 0

    def flush() -> None:
        nonlocal buffer, buffer_words
        if not buffer:
            return
        body = "\n\n".join(buffer)
        position = len(chunks)
        chunks.append(
            Chunk(chunk_id=f"{doc_id}::chunk{position}", text=body, position=position)
        )
        # keep an overlap tail so context isn't lost at boundaries
        words = body.split()
        tail = " ".join(words[-CHUNK_OVERLAP_WORDS:]) if len(words) > CHUNK_OVERLAP_WORDS else ""
        buffer = [tail] if tail else []
        buffer_words = len(tail.split())

    for para in paragraphs:
        para_words = len(para.split())
        if buffer_words + para_words > CHUNK_TARGET_WORDS and buffer_words > 0:
            flush()
        buffer.append(para)
        buffer_words += para_words
        # very long single paragraph: hard-split
        while buffer_words > CHUNK_TARGET_WORDS * 2:
            flush()
    flush()
    return chunks

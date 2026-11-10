from pathlib import Path

CHUNK_WORDS = 400
OVERLAP_WORDS = 50


def read_text(path: Path) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ValueError(f"{path.name} is not a valid UTF-8 text file.") from error
    if not text.strip():
        raise ValueError(f"{path.name} is empty.")
    return text


def chunk_text(
    text: str,
    chunk_words: int = CHUNK_WORDS,
    overlap_words: int = OVERLAP_WORDS,
) -> list[str]:
    words = text.split()
    step = chunk_words - overlap_words
    chunks = []
    for start in range(0, len(words), step):
        chunks.append(" ".join(words[start : start + chunk_words]))
        if start + chunk_words >= len(words):
            break
    return chunks

import json
import threading
from pathlib import Path

import faiss
import numpy as np

from services.embeddings import embed_texts
from services.parsing import chunk_text, read_text

DATA_DIR = Path(__file__).parent.parent / "data"
DOCS_DIR = DATA_DIR / "sample-docs"
INDEX_DIR = DATA_DIR / "index"
DIMENSIONS = 384
store_lock = threading.Lock()


def to_matrix(vectors: list[list[float]]) -> np.ndarray:
    matrix = np.array(vectors, dtype="float32")
    faiss.normalize_L2(matrix)
    return matrix


def build_index(docs_dir: Path = DOCS_DIR, index_dir: Path = INDEX_DIR) -> dict:
    # ponytail: rebuilds the whole index, the embedding cache makes unchanged files free
    chunks = []
    skipped = []
    for doc in sorted(docs_dir.glob("*.txt")):
        try:
            text = read_text(doc)
        except ValueError as error:
            skipped.append(str(error))
            continue
        chunks += [{"source": doc.name, "text": chunk} for chunk in chunk_text(text)]
    if not chunks:
        raise ValueError("no readable documents to index")

    vectors, cache_hits = embed_texts([chunk["text"] for chunk in chunks])
    index = faiss.IndexFlatIP(DIMENSIONS)
    index.add(to_matrix(vectors))

    index_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_dir / "index.faiss"))
    (index_dir / "chunks.json").write_text(json.dumps(chunks))
    return {"chunks": len(chunks), "cache_hits": cache_hits, "skipped": skipped}


def search(question: str, k: int = 3, index_dir: Path = INDEX_DIR) -> list[dict]:
    index = faiss.read_index(str(index_dir / "index.faiss"))
    chunks = json.loads((index_dir / "chunks.json").read_text())
    vectors, _ = embed_texts([question])
    scores, ids = index.search(to_matrix(vectors), k)
    return [
        {**chunks[chunk_id], "score": float(score)}
        for score, chunk_id in zip(scores[0], ids[0])
        if chunk_id != -1
    ]

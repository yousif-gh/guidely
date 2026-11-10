import hashlib
import json
from functools import lru_cache
from pathlib import Path

from fastembed import TextEmbedding
from services.metrics import record_cache

MODEL_NAME = "BAAI/bge-small-en-v1.5"
CACHE_PATH = Path(__file__).parent.parent / "data" / "embedding_cache.json"


@lru_cache(maxsize=1)
def get_model() -> TextEmbedding:
    return TextEmbedding(MODEL_NAME)


def cache_key(text: str) -> str:
    return hashlib.sha256(f"{MODEL_NAME}\n{text}".encode("utf-8")).hexdigest()


def embed_texts(
    texts: list[str],
    cache_path: Path = CACHE_PATH,
) -> tuple[list[list[float]], int]:
    # ponytail: whole cache is one JSON file, move to SQLite if it gets slow
    cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
    keys = [cache_key(text) for text in texts]
    missing = {key: text for key, text in zip(keys, texts) if key not in cache}
    if missing:
        vectors = get_model().embed(list(missing.values()))
        for key, vector in zip(missing, vectors):
            cache[key] = vector.tolist()
        cache_path.write_text(json.dumps(cache))
    hits = len(texts) - len(missing)
    record_cache(hits, len(missing))
    return [cache[key] for key in keys], hits

"""Embedding providers with a persistent on-disk cache.

Providers (set EMBEDDINGS_PROVIDER in .env):
  - "openai": OpenAI embeddings API (needs OPENAI_API_KEY)
  - "ollama": local Ollama server (OLLAMA_BASE_URL, OLLAMA_EMBED_MODEL)
  - "local":  deterministic feature-hashing embeddings, no network / no key.
              Useful for dev, tests and grading runs without credentials.

Cache: every chunk embedding is keyed by sha256(provider|model|text) and stored
in backend/data/embeddings_cache.json. Unchanged text is never re-embedded,
and every hit/miss is counted so /metrics can prove cache effectiveness.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import threading
from pathlib import Path
from typing import Dict, List, Tuple

import httpx

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
CACHE_PATH = DATA_DIR / "embeddings_cache.json"

LOCAL_DIM = 384


class MissingAPIKeyError(RuntimeError):
    pass


class EmbeddingProviderError(RuntimeError):
    pass


class EmbeddingCache:
    """Thread-safe JSON-backed embedding cache with hit/miss counters."""

    def __init__(self, path: Path = CACHE_PATH):
        self.path = path
        self._lock = threading.Lock()
        self.hits = 0
        self.misses = 0
        self._store: Dict[str, List[float]] = {}
        if path.exists():
            try:
                self._store = json.loads(path.read_text())
            except json.JSONDecodeError:
                self._store = {}

    def key(self, provider: str, model: str, text: str) -> str:
        return hashlib.sha256(f"{provider}|{model}|{text}".encode("utf-8")).hexdigest()

    def get(self, key: str):
        with self._lock:
            vec = self._store.get(key)
            if vec is not None:
                self.hits += 1
            return vec

    def put(self, key: str, vector: List[float]) -> None:
        with self._lock:
            self.misses += 1
            self._store[key] = vector

    def flush(self) -> None:
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self._store))

    def stats(self) -> dict:
        with self._lock:
            total = self.hits + self.misses
            return {
                "hits": self.hits,
                "misses": self.misses,
                "hit_rate": round(self.hits / total, 4) if total else None,
                "entries": len(self._store),
            }


cache = EmbeddingCache()


def _l2_normalize(vec: List[float]) -> List[float]:
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


# ---------------------------------------------------------------- providers

_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for",
    "from", "has", "have", "how", "i", "if", "in", "is", "it", "its", "may",
    "must", "my", "of", "on", "or", "our", "per", "should", "that", "the",
    "their", "them", "they", "this", "to", "was", "we", "what", "when", "where",
    "which", "who", "why", "will", "with", "you", "your",
}


def _light_stem(tok: str) -> str:
    """Tiny suffix stripper so 'travelling'/'travels'/'traveled' -> 'travel'."""
    for suffix in ("ings", "ing", "edly", "ed", "es", "s", "ly"):
        if tok.endswith(suffix) and len(tok) - len(suffix) >= 3:
            tok = tok[: -len(suffix)]
            break
    # collapse doubled final consonant left by -ing/-ed stripping (travell -> travel)
    if len(tok) >= 4 and tok[-1] == tok[-2] and tok[-1] not in "aeiou":
        tok = tok[:-1]
    return tok


def _embed_local(texts: List[str]) -> List[List[float]]:
    """Deterministic feature-hashing embedding: stopword removal, light
    stemming, word features + character trigrams for fuzzy matching, and
    sublinear term frequency (no network, no key). Good enough for dev/tests;
    switch EMBEDDINGS_PROVIDER=openai or =ollama for production quality."""

    def _hash_into(vec: List[float], feature: str, weight: float) -> None:
        h = int(hashlib.md5(feature.encode()).hexdigest(), 16)
        idx = h % LOCAL_DIM
        sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
        vec[idx] += sign * weight

    out = []
    for text in texts:
        vec = [0.0] * LOCAL_DIM
        tokens = [
            _light_stem(t)
            for t in re.findall(r"[a-z0-9]+", text.lower())
            if t not in _STOPWORDS
        ]
        counts: Dict[str, int] = {}
        for tok in tokens:
            counts[tok] = counts.get(tok, 0) + 1
        for tok, tf in counts.items():
            weight = 1.0 + math.log(tf)
            _hash_into(vec, f"w:{tok}", weight)
            # character trigrams give partial credit to near-matches
            padded = f"^{tok}$"
            for i in range(len(padded) - 2):
                _hash_into(vec, f"c:{padded[i:i + 3]}", 0.35 * weight)
        out.append(_l2_normalize(vec))
    return out


def _embed_openai(texts: List[str], model: str) -> List[List[float]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise MissingAPIKeyError(
            "OPENAI_API_KEY is not set. Add it to your .env or switch EMBEDDINGS_PROVIDER=local."
        )
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"model": model, "input": texts},
            timeout=30,
        )
        resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise EmbeddingProviderError(f"OpenAI embeddings request failed: {exc}") from exc
    data = resp.json()["data"]
    return [_l2_normalize(item["embedding"]) for item in data]


def _embed_ollama(texts: List[str], model: str) -> List[List[float]]:
    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    out = []
    for text in texts:
        try:
            resp = httpx.post(
                f"{base}/api/embeddings", json={"model": model, "prompt": text}, timeout=60
            )
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise EmbeddingProviderError(f"Ollama embeddings request failed: {exc}") from exc
        out.append(_l2_normalize(resp.json()["embedding"]))
    return out


def provider_info() -> Tuple[str, str]:
    provider = os.getenv("EMBEDDINGS_PROVIDER", "local").lower()
    default_models = {
        "openai": "text-embedding-3-small",
        "ollama": "nomic-embed-text",
        "local": f"feature-hash-v3-{LOCAL_DIM}",
    }
    model = os.getenv("EMBEDDINGS_MODEL", default_models.get(provider, "unknown"))
    return provider, model


def embed_texts(texts: List[str]) -> Tuple[List[List[float]], int, int]:
    """Embed texts through the cache. Returns (vectors, new_count, cached_count)."""
    provider, model = provider_info()
    vectors: List[List[float]] = [None] * len(texts)  # type: ignore
    pending: List[Tuple[int, str, str]] = []  # (index, key, text)

    for i, text in enumerate(texts):
        key = cache.key(provider, model, text)
        hit = cache.get(key)
        if hit is not None:
            vectors[i] = hit
        else:
            pending.append((i, key, text))

    if pending:
        pending_texts = [t for _, _, t in pending]
        if provider == "openai":
            fresh = _embed_openai(pending_texts, model)
        elif provider == "ollama":
            fresh = _embed_ollama(pending_texts, model)
        else:
            fresh = _embed_local(pending_texts)
        for (i, key, _), vec in zip(pending, fresh):
            cache.put(key, vec)
            vectors[i] = vec
        cache.flush()

    cached_count = len(texts) - len(pending)
    return vectors, len(pending), cached_count

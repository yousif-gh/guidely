import json
import logging
import statistics
import threading
from collections import Counter, deque

logger = logging.getLogger("guidely")

# ponytail: in memory, resets on restart, write to a file or database to keep history
_lock = threading.Lock()
_ask_ms = deque(maxlen=1000)
_counts = Counter()
_failures = Counter()


def record_request(method: str, path: str, status: int, ms: float) -> None:
    logger.info(
        json.dumps(
            {"event": "request", "method": method, "path": path, "status": status, "ms": round(ms, 1)}
        )
    )
    with _lock:
        if status >= 400:
            _failures[str(status)] += 1
        elif path == "/ask":
            _counts["queries_served"] += 1
            _ask_ms.append(ms)


def record_cache(hits: int, misses: int) -> None:
    logger.info(json.dumps({"event": "embedding_cache", "hits": hits, "misses": misses}))
    with _lock:
        _counts["cache_hits"] += hits
        _counts["cache_misses"] += misses


def snapshot() -> dict:
    with _lock:
        latencies = list(_ask_ms)
        counts = dict(_counts)
        failures = dict(_failures)
    median = p95 = None
    if latencies:
        median = statistics.median(latencies)
        p95 = median
    if len(latencies) >= 2:
        p95 = statistics.quantiles(latencies, n=20, method="inclusive")[-1]
    hits = counts.get("cache_hits", 0)
    misses = counts.get("cache_misses", 0)
    return {
        "queries_served": counts.get("queries_served", 0),
        "latency_ms": {
            "median": None if median is None else round(median, 1),
            "p95": None if p95 is None else round(p95, 1),
        },
        "embedding_cache": {
            "hits": hits,
            "misses": misses,
            "hit_rate": round(hits / (hits + misses), 3) if hits + misses else None,
        },
        "failures": failures,
    }

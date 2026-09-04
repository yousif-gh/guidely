"""Auto-logged metrics: latency, cache effectiveness, failure counts.

Every query is appended to backend/data/logs/queries.jsonl with timestamp,
latency, retrieved sources and cache stats, so metrics survive restarts.
/metrics aggregates them (median + p95 latency); /metrics/export.csv dumps
the raw query log for the bonus requirement.
"""
from __future__ import annotations

import csv
import io
import json
import statistics
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"
QUERY_LOG = LOG_DIR / "queries.jsonl"
ERROR_LOG = LOG_DIR / "errors.jsonl"

_lock = threading.Lock()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_query(
    question: str,
    latency_ms: float,
    sources: List[dict],
    cache_hits: int,
    cache_misses: int,
) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": _now(),
        "question": question,
        "latency_ms": round(latency_ms, 2),
        "sources": [{"file": s["file"], "chunk_id": s["chunk_id"], "score": s["score"]} for s in sources],
        "cache_hits": cache_hits,
        "cache_misses": cache_misses,
    }
    with _lock, QUERY_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def log_error(error_type: str, detail: str, status_code: int) -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    entry = {"ts": _now(), "type": error_type, "detail": detail, "status": status_code}
    with _lock, ERROR_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def _read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def latency_stats() -> Optional[dict]:
    entries = _read_jsonl(QUERY_LOG)
    latencies = [e["latency_ms"] for e in entries if "latency_ms" in e]
    if not latencies:
        return None
    ordered = sorted(latencies)
    p95_idx = max(0, int(round(0.95 * len(ordered))) - 1)
    return {
        "count": len(ordered),
        "median_ms": round(statistics.median(ordered), 2),
        "p95_ms": round(ordered[p95_idx], 2),
        "min_ms": round(ordered[0], 2),
        "max_ms": round(ordered[-1], 2),
    }


def error_stats() -> dict:
    entries = _read_jsonl(ERROR_LOG)
    counts: dict = {}
    for e in entries:
        counts[e.get("type", "unknown")] = counts.get(e.get("type", "unknown"), 0) + 1
    return {"total": len(entries), "by_type": counts}


def queries_served() -> int:
    return len(_read_jsonl(QUERY_LOG))


def export_csv() -> str:
    entries = _read_jsonl(QUERY_LOG)
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["timestamp", "question", "latency_ms", "cache_hits", "cache_misses", "sources"])
    for e in entries:
        writer.writerow(
            [
                e.get("ts"),
                e.get("question"),
                e.get("latency_ms"),
                e.get("cache_hits"),
                e.get("cache_misses"),
                "; ".join(s["file"] + "#" + s["chunk_id"] for s in e.get("sources", [])),
            ]
        )
    return buf.getvalue()

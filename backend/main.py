"""Guidely — internal knowledge assistant API.

Run from the backend/ directory:
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Load .env from the project root before any service reads env vars.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, Response  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from routes import documents, search  # noqa: E402
from services import metrics  # noqa: E402
from services.embeddings import cache, provider_info as embed_provider_info  # noqa: E402
from services.llm import provider_info as llm_provider_info  # noqa: E402
from services.vector_store import store  # noqa: E402

app = FastAPI(
    title="Guidely API",
    description="Semantic search over internal docs with LLM answers and cited sources.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router)
app.include_router(search.router)


@app.get("/health")
def health():
    embed_provider, embed_model = embed_provider_info()
    llm_provider, llm_model = llm_provider_info()
    return {
        "status": "ok",
        "index": store.stats(),
        "providers": {
            "embeddings": f"{embed_provider}:{embed_model}",
            "llm": f"{llm_provider}:{llm_model}",
        },
    }


@app.get("/metrics")
def get_metrics():
    return {
        "index": store.stats(),
        "queries_served": metrics.queries_served(),
        "latency": metrics.latency_stats(),
        "embedding_cache": cache.stats(),
        "errors": metrics.error_stats(),
    }


@app.get("/metrics/export.csv")
def export_metrics_csv():
    return Response(
        content=metrics.export_csv(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=query_log.csv"},
    )

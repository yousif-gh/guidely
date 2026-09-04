"""Question answering: embed query -> vector search -> LLM answer with sources."""
from __future__ import annotations

import os
import time

from fastapi import APIRouter, HTTPException

from models.record import AskRequest, AskResponse, SourceRef, TranslateRequest, TranslateResponse
from services import metrics
from services.embeddings import (
    EmbeddingProviderError,
    MissingAPIKeyError,
    cache,
    embed_texts,
    provider_info as embed_provider_info,
)
from services.llm import (
    LLMProviderError,
    MissingAPIKeyError as LLMMissingKey,
    generate_answer,
    needs_translation,
    provider_info as llm_provider_info,
    translate_text,
    translate_to_english,
)
from services.vector_store import store

router = APIRouter(tags=["search"])

SNIPPET_CHARS = 320


def _snippet(text: str) -> str:
    text = " ".join(text.split())
    return text[:SNIPPET_CHARS] + ("…" if len(text) > SNIPPET_CHARS else "")


@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    t0 = time.perf_counter()

    if not payload.question or not payload.question.strip():
        metrics.log_error("empty_query", "Question was empty.", 400)
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if store.stats()["chunks"] == 0:
        metrics.log_error("no_documents_indexed", "Index is empty.", 409)
        raise HTTPException(
            status_code=409,
            detail="No documents are indexed yet. Upload documents or run /documents/reindex first.",
        )

    hits_before, misses_before = cache.hits, cache.misses

    question = payload.question.strip()
    retrieval_query = translate_to_english(question) if needs_translation(question) else question

    try:
        vectors, _, _ = embed_texts([retrieval_query])
    except MissingAPIKeyError as exc:
        metrics.log_error("missing_model_key", str(exc), 503)
        raise HTTPException(status_code=503, detail=str(exc))
    except EmbeddingProviderError as exc:
        metrics.log_error("embedding_provider_error", str(exc), 502)
        raise HTTPException(status_code=502, detail=str(exc))

    top_k = max(1, min(payload.top_k, 10))
    results = store.search(vectors[0], top_k=top_k, tags=payload.tags)
    min_score = float(os.getenv("MIN_RELEVANCE_SCORE", "0.05"))
    results = [r for r in results if r["score"] >= min_score]
    if not results:
        metrics.log_error("no_results_found", f"No matches for: {question[:80]}", 404)
        raise HTTPException(
            status_code=404,
            detail="No relevant passages were found for that question. Try rephrasing it.",
        )

    doc_meta = store.documents
    contexts = [
        {
            "file": doc_meta.get(r["doc_id"], {}).get("filename", r["doc_id"]),
            "chunk_id": r["chunk_id"],
            "text": r["text"],
            "score": r["score"],
        }
        for r in results
    ]

    try:
        answer = generate_answer(question, contexts, payload.history)
    except LLMMissingKey as exc:
        metrics.log_error("missing_model_key", str(exc), 503)
        raise HTTPException(status_code=503, detail=str(exc))
    except LLMProviderError as exc:
        metrics.log_error("llm_provider_error", str(exc), 502)
        raise HTTPException(status_code=502, detail=str(exc))

    latency_ms = (time.perf_counter() - t0) * 1000
    query_cache = {
        "hits": cache.hits - hits_before,
        "misses": cache.misses - misses_before,
    }
    sources = [
        SourceRef(
            file=c["file"],
            chunk_id=c["chunk_id"],
            score=round(c["score"], 4),
            snippet=_snippet(c["text"]),
        )
        for c in contexts
    ]
    metrics.log_query(
        question=question,
        latency_ms=latency_ms,
        sources=[s.model_dump() for s in sources],
        cache_hits=query_cache["hits"],
        cache_misses=query_cache["misses"],
    )
    embed_provider, embed_model = embed_provider_info()
    llm_provider, llm_model = llm_provider_info()
    return AskResponse(
        answer=answer,
        sources=sources,
        latency_ms=round(latency_ms, 2),
        cache=query_cache,
        provider={
            "embeddings": f"{embed_provider}:{embed_model}",
            "llm": f"{llm_provider}:{llm_model}",
        },
    )


@router.post("/translate", response_model=TranslateResponse)
def translate(payload: TranslateRequest):
    try:
        translated = translate_text(payload.text, payload.target_lang)
    except LLMMissingKey as exc:
        metrics.log_error("missing_model_key", str(exc), 503)
        raise HTTPException(status_code=503, detail=str(exc))
    except LLMProviderError as exc:
        metrics.log_error("llm_provider_error", str(exc), 502)
        raise HTTPException(status_code=502, detail=str(exc))
    return TranslateResponse(translated=translated)

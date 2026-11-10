from fastapi import APIRouter, HTTPException

from models.record import SearchRequest
from services.llm import LLMError, answer_question
from services.metrics import logger
from services.vector_store import INDEX_DIR, search, store_lock

router = APIRouter(tags=["search"])

# Measured on sample docs: off-topic questions reached 0.52, on-topic started at 0.57.
MIN_SCORE = 0.52
NO_RESULTS = "no answer found in the documents"


def retrieve(question: str, k: int) -> list[dict]:
    with store_lock:
        if not (INDEX_DIR / "index.faiss").exists():
            raise HTTPException(409, "index not built, call POST /documents/reindex")
        return search(question, k)


@router.post("/search")
def search_documents(request: SearchRequest) -> list[dict]:
    return retrieve(request.question, request.k)


@router.post("/ask")
def ask(request: SearchRequest) -> dict:
    chunks = [
        chunk
        for chunk in retrieve(request.question, request.k)
        if chunk["score"] >= MIN_SCORE
    ]
    if not chunks:
        raise HTTPException(404, NO_RESULTS)
    try:
        result = answer_question(request.question, chunks)
    except LLMError as error:
        logger.error("model error: %s, cause: %r", error.message, error.__cause__)
        raise HTTPException(error.status_code, error.message) from error
    if result is None:
        raise HTTPException(404, NO_RESULTS)
    return result

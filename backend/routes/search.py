from fastapi import APIRouter, HTTPException

from models.record import SearchRequest
from services.vector_store import INDEX_DIR, search, store_lock

router = APIRouter(tags=["search"])


@router.post("/search")
def search_documents(request: SearchRequest) -> list[dict]:
    with store_lock:
        if not (INDEX_DIR / "index.faiss").exists():
            raise HTTPException(409, "index not built, call POST /documents/reindex")
        return search(request.question, request.k)

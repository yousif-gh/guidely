import json
import logging
import time

from fastapi import FastAPI, Request

from routes.documents import router as documents_router
from routes.search import router as search_router
from services.metrics import record_request, snapshot
from services.vector_store import DOCS_DIR, INDEX_DIR, store_lock

logging.basicConfig(level=logging.INFO, format="%(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

app = FastAPI(title="Guidely")
app.include_router(documents_router)
app.include_router(search_router)


@app.middleware("http")
async def track_requests(request: Request, call_next):
    started = time.perf_counter()
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        ms = (time.perf_counter() - started) * 1000
        record_request(request.method, request.url.path, status, ms)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    chunks_path = INDEX_DIR / "chunks.json"
    with store_lock:
        chunks = json.loads(chunks_path.read_text()) if chunks_path.exists() else []
    return {
        "documents": len(list(DOCS_DIR.glob("*.txt"))),
        "chunks": len(chunks),
        **snapshot(),
    }

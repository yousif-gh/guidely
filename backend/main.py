from fastapi import FastAPI

from routes.documents import router as documents_router
from routes.search import router as search_router

app = FastAPI(title="Guidely")
app.include_router(documents_router)
app.include_router(search_router)


@app.get("/health")
def health():
    return {"status": "ok"}

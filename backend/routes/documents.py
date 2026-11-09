from __future__ import annotations

import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from models.record import (
    DocumentInfo,
    DocumentListResponse,
    ReindexResponse,
    UploadResponse,
)
from services import metrics
from services.embeddings import (
    EmbeddingProviderError,
    MissingAPIKeyError,
    embed_texts,
)
from services.parsing import (
    CorruptedFileError,
    UnsupportedFileError,
    chunk_text,
    parse_bytes,
    sha256_text,
)
from services.vector_store import store

router = APIRouter(prefix="/documents", tags=["documents"])

DOCS_DIR = Path(__file__).resolve().parent.parent / "data" / "sample-docs"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _doc_id(filename: str) -> str:
    return filename.rsplit(".", 1)[0].lower().replace(" ", "-")


def _index_text(doc_id: str, filename: str, text: str, tags: Optional[List[str]] = None):
    """Chunk + embed + upsert one document. Returns (chunks, new, cached)."""
    digest = sha256_text(text)
    chunks = chunk_text(doc_id, text)
    vectors, new_count, cached_count = embed_texts([c.text for c in chunks])
    store.upsert_document(
        doc_id=doc_id,
        filename=filename,
        sha256=digest,
        chunks=[{"chunk_id": c.chunk_id, "text": c.text, "position": c.position} for c in chunks],
        vectors=vectors,
        tags=tags,
        indexed_at=_now(),
    )
    return chunks, new_count, cached_count


def _raise_for(exc: Exception) -> None:
    """Map service errors to clean HTTP responses and log them."""
    if isinstance(exc, (UnsupportedFileError, CorruptedFileError)):
        metrics.log_error("corrupted_or_unsupported_file", str(exc), 400)
        raise HTTPException(status_code=400, detail=str(exc))
    if isinstance(exc, MissingAPIKeyError):
        metrics.log_error("missing_model_key", str(exc), 503)
        raise HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, EmbeddingProviderError):
        metrics.log_error("embedding_provider_error", str(exc), 502)
        raise HTTPException(status_code=502, detail=str(exc))
    raise exc


@router.get("", response_model=DocumentListResponse)
def list_documents():
    docs = []
    for doc_id, meta in sorted(store.documents.items()):
        path = DOCS_DIR / meta["filename"]
        docs.append(
            DocumentInfo(
                id=doc_id,
                filename=meta["filename"],
                size_bytes=path.stat().st_size if path.exists() else 0,
                num_chunks=meta["num_chunks"],
                sha256=meta["sha256"],
                indexed_at=meta.get("indexed_at"),
                tags=meta.get("tags", []),
            )
        )
    return DocumentListResponse(documents=docs)


@router.get("/{doc_id}/content")
def get_document_content(doc_id: str):
    meta = store.documents.get(doc_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    path = DOCS_DIR / meta["filename"]
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"File for '{doc_id}' is missing on disk.")
    return {"id": doc_id, "filename": meta["filename"], "content": path.read_text()}


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_document(file: UploadFile = File(...), tags: str = Form("")):
    """Upload a .txt/.md file, save it to sample-docs, embed and index it."""
    t0 = time.perf_counter()
    raw = await file.read()
    try:
        text = parse_bytes(file.filename, raw)
        DOCS_DIR.mkdir(parents=True, exist_ok=True)
        (DOCS_DIR / file.filename).write_text(text)
        tag_list = [t.strip() for t in tags.split(",") if t.strip()]
        doc_id = _doc_id(file.filename)
        chunks, new, cached = _index_text(doc_id, file.filename, text, tag_list)
    except Exception as exc:  # noqa: BLE001
        _raise_for(exc)
    elapsed = (time.perf_counter() - t0) * 1000
    meta = store.documents[doc_id]
    return UploadResponse(
        document=DocumentInfo(
            id=doc_id,
            filename=file.filename,
            size_bytes=len(raw),
            num_chunks=meta["num_chunks"],
            sha256=meta["sha256"],
            indexed_at=meta["indexed_at"],
            tags=meta.get("tags", []),
        ),
        chunks_created=len(chunks),
        embeddings_new=new,
        embeddings_cached=cached,
        elapsed_ms=round(elapsed, 2),
    )


@router.put("/{doc_id}", response_model=UploadResponse)
def edit_document(doc_id: str, payload: dict):
    """Replace a document's text content and re-index it."""
    t0 = time.perf_counter()
    meta = store.documents.get(doc_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    content = (payload or {}).get("content", "")
    if not content.strip():
        metrics.log_error("empty_document_edit", f"Empty content for '{doc_id}'", 400)
        raise HTTPException(status_code=400, detail="Document content cannot be empty.")
    path = DOCS_DIR / meta["filename"]
    path.write_text(content)
    try:
        chunks, new, cached = _index_text(doc_id, meta["filename"], content, meta.get("tags"))
    except Exception as exc:  # noqa: BLE001
        _raise_for(exc)
    elapsed = (time.perf_counter() - t0) * 1000
    meta = store.documents[doc_id]
    return UploadResponse(
        document=DocumentInfo(
            id=doc_id,
            filename=meta["filename"],
            size_bytes=path.stat().st_size,
            num_chunks=meta["num_chunks"],
            sha256=meta["sha256"],
            indexed_at=meta["indexed_at"],
            tags=meta.get("tags", []),
        ),
        chunks_created=len(chunks),
        embeddings_new=new,
        embeddings_cached=cached,
        elapsed_ms=round(elapsed, 2),
    )


@router.delete("/{doc_id}", status_code=200)
def delete_document(doc_id: str):
    meta = store.documents.get(doc_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Document '{doc_id}' not found.")
    path = DOCS_DIR / meta["filename"]
    store.delete_document(doc_id)
    if path.exists():
        path.unlink()
    return {"deleted": doc_id}


@router.post("/reindex", response_model=ReindexResponse)
def reindex():
    """Re-index everything under data/sample-docs. Unchanged files are skipped
    (same sha256), and unchanged chunks hit the embedding cache anyway."""
    t0 = time.perf_counter()
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    indexed, skipped = [], []
    total_chunks = new_total = cached_total = 0
    for path in sorted(DOCS_DIR.iterdir()):
        if path.suffix.lower() not in {".txt", ".md"}:
            continue
        try:
            text = parse_bytes(path.name, path.read_bytes())
        except Exception as exc:  # noqa: BLE001
            metrics.log_error("corrupted_or_unsupported_file", f"{path.name}: {exc}", 400)
            continue  # skip bad files during bulk reindex, but log them
        doc_id = _doc_id(path.name)
        if store.file_hash(doc_id) == sha256_text(text):
            skipped.append(path.name)
            total_chunks += store.documents[doc_id]["num_chunks"]
            continue
        try:
            existing_tags = (store.documents.get(doc_id) or {}).get("tags", [])
            chunks, new, cached = _index_text(doc_id, path.name, text, existing_tags)
        except Exception as exc:  # noqa: BLE001
            _raise_for(exc)
        indexed.append(path.name)
        total_chunks += len(chunks)
        new_total += new
        cached_total += cached
    elapsed = (time.perf_counter() - t0) * 1000
    return ReindexResponse(
        indexed=indexed,
        skipped_unchanged=skipped,
        total_chunks=total_chunks,
        embeddings_new=new_total,
        embeddings_cached=cached_total,
        elapsed_ms=round(elapsed, 2),
    )

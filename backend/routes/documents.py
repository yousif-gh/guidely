import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, UploadFile

from services.parsing import decode_text
from services.vector_store import DOCS_DIR, build_index, store_lock

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_UPLOAD_BYTES = 1_000_000


@router.get("")
def list_documents() -> list[dict]:
    return [
        {"name": doc.name, "bytes": doc.stat().st_size}
        for doc in sorted(DOCS_DIR.glob("*.txt"))
    ]


@router.post("", status_code=201)
def upload_document(file: UploadFile) -> dict:
    name = Path(file.filename or "").name
    if not re.fullmatch(r"[\w .-]+\.txt", name):
        raise HTTPException(415, "only .txt files with a plain name are supported")
    content = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, "file is larger than 1 MB")
    try:
        decode_text(content, name)
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    with store_lock:
        (DOCS_DIR / name).write_bytes(content)
        return {"name": name, "index": build_index()}


@router.post("/reindex")
def reindex() -> dict:
    with store_lock:
        try:
            return build_index()
        except ValueError as error:
            raise HTTPException(400, str(error)) from error

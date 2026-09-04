"""Pydantic models shared across the Guidely API."""
from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class DocumentInfo(BaseModel):
    """Metadata for one indexed document."""
    id: str
    filename: str
    size_bytes: int
    num_chunks: int
    sha256: str
    indexed_at: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class DocumentListResponse(BaseModel):
    documents: List[DocumentInfo]


class UploadResponse(BaseModel):
    """Returned by upload (POST /documents) and edit (PUT /documents/{id})."""
    document: DocumentInfo
    chunks_created: int
    embeddings_new: int
    embeddings_cached: int
    elapsed_ms: float


class ReindexResponse(BaseModel):
    indexed: List[str]
    skipped_unchanged: List[str]
    total_chunks: int
    embeddings_new: int
    embeddings_cached: int
    elapsed_ms: float


class SourceRef(BaseModel):
    """A source citation attached to an answer."""
    file: str
    chunk_id: str
    score: float
    snippet: str


class AskRequest(BaseModel):
    question: str = Field("", description="Natural-language question")
    top_k: int = Field(3, ge=1, le=10)
    tags: Optional[List[str]] = None
    history: Optional[List[Dict[str, str]]] = None  # [{role, content}] for follow-ups


class AskResponse(BaseModel):
    answer: str
    sources: List[SourceRef]
    latency_ms: float
    cache: Dict[str, int]
    provider: Dict[str, str]


class TranslateRequest(BaseModel):
    text: str = Field(..., min_length=1)
    target_lang: str = Field("Arabic", description="Language name to translate into")


class TranslateResponse(BaseModel):
    translated: str

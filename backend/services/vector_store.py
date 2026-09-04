"""FAISS-backed vector store with sidecar metadata, persisted to disk.

Vectors are L2-normalized upstream, so inner product == cosine similarity.
The store is rebuilt in memory from metadata whenever documents change
(FAISS flat indexes don't support cheap deletes) and saved alongside a
manifest of file hashes so re-indexing skips unchanged files.
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Dict, List, Optional

import faiss
import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
INDEX_PATH = DATA_DIR / "faiss.index"
META_PATH = DATA_DIR / "index_meta.json"


class VectorStore:
    def __init__(self):
        self._lock = threading.Lock()
        self.dim: Optional[int] = None
        self.index: Optional[faiss.IndexFlatIP] = None
        # parallel arrays: metadata[i] corresponds to index vector i
        self.metadata: List[dict] = []
        self.vectors: List[List[float]] = []
        # documents: doc_id -> {filename, sha256, num_chunks, indexed_at, tags}
        self.documents: Dict[str, dict] = {}
        self._load()

    # ------------------------------------------------------------ persistence
    @staticmethod
    def _embedding_signature() -> str:
        """provider:model of the active embedder. If it changes, stored
        vectors live in a different space and must be discarded."""
        from services.embeddings import provider_info  # local import, no cycle

        provider, model = provider_info()
        return f"{provider}:{model}"

    def _load(self) -> None:
        if META_PATH.exists():
            blob = json.loads(META_PATH.read_text())
            if blob.get("embedding_signature") != self._embedding_signature():
                # Embedding provider/model changed: old vectors are unusable.
                self.metadata, self.vectors, self.documents = [], [], {}
                self.dim = None
                return
            self.metadata = blob.get("metadata", [])
            self.vectors = blob.get("vectors", [])
            self.documents = blob.get("documents", {})
            self.dim = blob.get("dim")
        if self.vectors and self.dim:
            self._rebuild_index()

    def _save(self) -> None:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        META_PATH.write_text(
            json.dumps(
                {
                    "embedding_signature": self._embedding_signature(),
                    "dim": self.dim,
                    "metadata": self.metadata,
                    "vectors": self.vectors,
                    "documents": self.documents,
                }
            )
        )
        if self.index is not None:
            faiss.write_index(self.index, str(INDEX_PATH))

    def _rebuild_index(self) -> None:
        arr = np.array(self.vectors, dtype="float32")
        self.index = faiss.IndexFlatIP(self.dim)
        if len(arr):
            self.index.add(arr)

    # ------------------------------------------------------------- mutations
    def upsert_document(
        self,
        doc_id: str,
        filename: str,
        sha256: str,
        chunks: List[dict],
        vectors: List[List[float]],
        tags: Optional[List[str]] = None,
        indexed_at: str = "",
    ) -> None:
        """Replace all vectors for a document and rebuild the index."""
        with self._lock:
            if self.dim is None and vectors:
                self.dim = len(vectors[0])
            keep = [
                (m, v)
                for m, v in zip(self.metadata, self.vectors)
                if m["doc_id"] != doc_id
            ]
            self.metadata = [m for m, _ in keep]
            self.vectors = [v for _, v in keep]
            for chunk, vec in zip(chunks, vectors):
                self.metadata.append({"doc_id": doc_id, **chunk})
                self.vectors.append(list(vec))
            self.documents[doc_id] = {
                "filename": filename,
                "sha256": sha256,
                "num_chunks": len(chunks),
                "indexed_at": indexed_at,
                "tags": tags or [],
            }
            self._rebuild_index()
            self._save()

    def delete_document(self, doc_id: str) -> bool:
        with self._lock:
            if doc_id not in self.documents:
                return False
            keep = [
                (m, v)
                for m, v in zip(self.metadata, self.vectors)
                if m["doc_id"] != doc_id
            ]
            self.metadata = [m for m, _ in keep]
            self.vectors = [v for _, v in keep]
            del self.documents[doc_id]
            if self.vectors:
                self._rebuild_index()
            else:
                self.index = None
            self._save()
            return True

    # --------------------------------------------------------------- queries
    def search(
        self, query_vector: List[float], top_k: int = 3, tags: Optional[List[str]] = None
    ) -> List[dict]:
        with self._lock:
            if self.index is None or not self.metadata:
                return []
            q = np.array([query_vector], dtype="float32")
            k = min(max(top_k * 4, top_k), len(self.metadata))  # overfetch for tag filter
            scores, ids = self.index.search(q, k)
            results = []
            allowed = set(tags) if tags else None
            for score, idx in zip(scores[0], ids[0]):
                if idx < 0:
                    continue
                meta = self.metadata[int(idx)]
                if allowed is not None:
                    doc = self.documents.get(meta["doc_id"], {})
                    if not allowed.intersection(doc.get("tags", [])):
                        continue
                results.append({**meta, "score": float(score)})
                if len(results) >= top_k:
                    break
            return results

    # ----------------------------------------------------------------- stats
    def stats(self) -> dict:
        with self._lock:
            return {
                "documents": len(self.documents),
                "chunks": len(self.metadata),
                "dim": self.dim,
            }

    def file_hash(self, doc_id: str) -> Optional[str]:
        doc = self.documents.get(doc_id)
        return doc["sha256"] if doc else None


store = VectorStore()

from __future__ import annotations
"""
In-memory vector store used as a fallback when Qdrant is unavailable.
Used in tests and for small schemas (< SCHEMA_RAG_MIN_TABLES tables).
Not suitable for production with large schemas.
"""
import math
from typing import Any


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class MemoryVectorStore:
    """Simple in-memory vector store for development and testing."""

    def __init__(self):
        self._store: dict[str, list[tuple[list[float], dict[str, Any]]]] = {}

    def upsert(self, collection: str, doc_id: str, vector: list[float], payload: dict) -> None:
        if collection not in self._store:
            self._store[collection] = []
        # Remove existing entry with same id
        self._store[collection] = [
            (v, p) for v, p in self._store[collection] if p.get("id") != doc_id
        ]
        self._store[collection].append((vector, {"id": doc_id, **payload}))

    def search(self, collection: str, query_vector: list[float], top_k: int = 10) -> list[dict]:
        if collection not in self._store:
            return []
        scored = [
            (payload, _cosine_similarity(query_vector, vec))
            for vec, payload in self._store[collection]
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [payload for payload, _ in scored[:top_k]]

    def delete_collection(self, collection: str) -> None:
        self._store.pop(collection, None)

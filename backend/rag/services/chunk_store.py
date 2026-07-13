import logging
from datetime import datetime
from typing import Any
from uuid import uuid4

from services.utils import utc_now as _utc_now

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchAny,
    MatchValue,
    PointStruct,
    VectorParams,
)

from rag.schemas import RAGChunk
from rag.services.retrieval import (
    ScoredDoc,
    apply_score_threshold,
    mmr_score,
    time_aware_score,
    top_k_sorted,
)

logger = logging.getLogger(__name__)

_instance: "ChunkStore | None" = None


def configure_chunk_store(url: str, api_key: str | None = None) -> None:
    global _instance
    _instance = ChunkStore(url=url, api_key=api_key)


def get_chunk_store_instance() -> "ChunkStore":
    if _instance is None:
        raise RuntimeError("ChunkStore is not configured; call configure_chunk_store at startup")
    return _instance


def _payload_to_chunk(point_id: str, payload: dict) -> RAGChunk:
    created = payload.get("created_at")
    if isinstance(created, str):
        created = datetime.fromisoformat(created)
    elif created is None:
        created = _utc_now()
    return RAGChunk(
        id=point_id,
        rag_id=payload["rag_id"],
        name=payload["name"],
        data=payload["data"],
        source=payload.get("source"),
        metadata=payload.get("metadata", {}),
        created_at=created,
    )


def _build_qdrant_filter(filters: dict | None) -> Filter | None:
    if not filters:
        return None

    def _condition(c: dict) -> FieldCondition:
        # Filter keys are relative to the metadata dict in the payload
        key = f"metadata.{c['key']}"
        match_cfg = c.get("match", {})
        if "value" in match_cfg:
            return FieldCondition(key=key, match=MatchValue(value=match_cfg["value"]))
        if "any" in match_cfg:
            return FieldCondition(key=key, match=MatchAny(any=match_cfg["any"]))
        raise ValueError(f"Unsupported filter match type: {match_cfg}")

    must = [_condition(c) for c in filters.get("must", [])]
    should = [_condition(c) for c in filters.get("should", [])]
    must_not = [_condition(c) for c in filters.get("must_not", [])]

    return Filter(
        must=must or None,
        should=should or None,
        must_not=must_not or None,
    )


class ChunkStore:
    def __init__(self, url: str, api_key: str | None = None):
        self._client = QdrantClient(url=url, api_key=api_key or None, timeout=30)

    # ── Collection lifecycle ──────────────────────────────────────────────────

    def create_collection(self, rag_id: str, embedding_dimensions: int) -> None:
        self._client.create_collection(
            collection_name=rag_id,
            vectors_config=VectorParams(size=embedding_dimensions, distance=Distance.COSINE),
        )

    def delete_collection(self, rag_id: str) -> bool:
        try:
            self._client.delete_collection(collection_name=rag_id)
            return True
        except Exception:
            return False

    # ── Data insertion ────────────────────────────────────────────────────────

    def insert_many(
        self,
        *,
        rag_id: str,
        name: str,
        parts: list[str],
        source: str | None = None,
        metadata: dict[str, Any] | None = None,
        embeddings: list[list[float]] | None = None,
    ) -> list[RAGChunk]:
        multi = len(parts) > 1
        now = _utc_now()

        points: list[PointStruct] = []
        chunks: list[RAGChunk] = []

        for i, part in enumerate(parts):
            chunk_id = str(uuid4())
            chunk_name = f"{name} [{i + 1}/{len(parts)}]" if multi else name
            chunk_metadata = {
                **(metadata or {}),
                "chunk_index": i,
                "total_chunks": len(parts),
            }
            payload = {
                "rag_id": rag_id,
                "name": chunk_name,
                "data": part,
                "source": source,
                "metadata": chunk_metadata,
                "created_at": now.isoformat(),
            }
            points.append(
                PointStruct(
                    id=chunk_id,
                    vector=embeddings[i] if embeddings else [],
                    payload=payload,
                )
            )
            chunks.append(_payload_to_chunk(chunk_id, payload))

        self._client.upsert(collection_name=rag_id, points=points)
        return chunks

    # ── Data listing ──────────────────────────────────────────────────────────

    def list_for_rag(self, rag_id: str) -> list[RAGChunk]:
        records, _ = self._client.scroll(
            collection_name=rag_id,
            with_payload=True,
            with_vectors=False,
            limit=10_000,
        )
        chunks = [_payload_to_chunk(str(r.id), r.payload or {}) for r in records]
        return sorted(chunks, key=lambda c: c.created_at, reverse=True)

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def search_scored(
        self,
        *,
        rag_id: str,
        query_embedding: list[float],
        retrieval_type: str,
        top_k: int,
        lambda_param: float,
        score_threshold: float,
        time_decay_factor: float,
        filters: dict | None,
    ) -> list[tuple[RAGChunk, float]]:
        qdrant_filter = _build_qdrant_filter(filters)

        if retrieval_type in ("basic", "hyde"):
            response = self._client.query_points(
                collection_name=rag_id,
                query=query_embedding,
                limit=top_k,
                with_payload=True,
                query_filter=qdrant_filter,
                score_threshold=score_threshold if score_threshold > 0 else None,
            )
            return [(_payload_to_chunk(str(r.id), r.payload or {}), r.score) for r in response.points]

        if retrieval_type == "mmr":
            # Overfetch candidates with vectors, then apply MMR in memory
            response = self._client.query_points(
                collection_name=rag_id,
                query=query_embedding,
                limit=min(top_k * 5, 500),
                with_payload=True,
                with_vectors=True,
                query_filter=qdrant_filter,
            )
            if not response.points:
                return []
            docs: list[dict] = [
                {"_id": str(r.id), "embedding": list(r.vector), **r.payload}
                for r in response.points
            ]
            scored: list[ScoredDoc] = mmr_score(docs, query_embedding, lambda_param, top_k)
            scored = apply_score_threshold(scored, score_threshold)
            return [
                (_payload_to_chunk(doc["_id"], doc), s)
                for doc, s in top_k_sorted(scored, top_k)
            ]

        if retrieval_type == "time_aware":
            # Overfetch with vectors + payload, apply time-decay reranking in memory
            response = self._client.query_points(
                collection_name=rag_id,
                query=query_embedding,
                limit=min(top_k * 10, 1000),
                with_payload=True,
                with_vectors=True,
                query_filter=qdrant_filter,
            )
            if not response.points:
                return []
            docs = [
                {"_id": str(r.id), "embedding": list(r.vector), **r.payload}
                for r in response.points
            ]
            scored = time_aware_score(docs, query_embedding, time_decay_factor)
            return [
                (_payload_to_chunk(doc["_id"], doc), s)
                for doc, s in top_k_sorted(scored, top_k)
            ]

        return []

    # ── Deletion ──────────────────────────────────────────────────────────────

    def delete_for_rag(self, rag_id: str) -> None:
        self.delete_collection(rag_id)

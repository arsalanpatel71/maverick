from datetime import datetime
from uuid import uuid4

from pymongo import ReturnDocument

from agents.services.agent_store import rags_collection
from rag.schemas import (
    EmbeddingModel,
    RAGResponse,
    VectorStoreProvider,
    _PROVIDER_MODELS,
    embedding_dimensions_for,
)
from services.utils import name_filter, utc_now as _utc_now


def _infer_provider(model_value: str) -> str:
    for provider, models in _PROVIDER_MODELS.items():
        if model_value in models:
            return provider
    return "openai"


def _doc_to_response(doc: dict) -> RAGResponse:
    created = doc["created_at"]
    updated = doc["updated_at"]
    if isinstance(created, str):
        created = datetime.fromisoformat(created)
    if isinstance(updated, str):
        updated = datetime.fromisoformat(updated)
    model = EmbeddingModel(doc["embedding_model"])
    return RAGResponse(
        id=doc["_id"],
        name=doc["name"],
        description=doc.get("description"),
        vector_store=VectorStoreProvider(doc["vector_store"]),
        embedding_provider=doc.get("embedding_provider") or _infer_provider(model.value),
        embedding_model=model,
        embedding_dimensions=int(doc["embedding_dimensions"]),
        created_at=created,
        updated_at=updated,
    )


class RagStore:
    def create(
        self,
        *,
        name: str,
        description: str | None,
        vector_store: VectorStoreProvider,
        embedding_provider: str,
        embedding_model: EmbeddingModel,
    ) -> RAGResponse:
        coll = rags_collection()
        rag_id = str(uuid4())
        now = _utc_now()
        dims = embedding_dimensions_for(embedding_model)
        doc = {
            "_id": rag_id,
            "name": name,
            "description": description,
            "vector_store": vector_store.value,
            "embedding_provider": embedding_provider,
            "embedding_model": embedding_model.value,
            "embedding_dimensions": dims,
            "created_at": now,
            "updated_at": now,
        }
        coll.insert_one(doc)
        return _doc_to_response(doc)

    def get(self, rag_id: str) -> RAGResponse | None:
        coll = rags_collection()
        doc = coll.find_one({"_id": rag_id})
        return _doc_to_response(doc) if doc else None

    def list_all(self, q: str | None = None) -> list[RAGResponse]:
        coll = rags_collection()
        query = name_filter(q, "name", "description")
        return [_doc_to_response(doc) for doc in coll.find(query).sort("updated_at", -1)]

    def update(self, rag_id: str, description: str | None) -> RAGResponse | None:
        coll = rags_collection()
        result = coll.find_one_and_update(
            {"_id": rag_id},
            {"$set": {"description": description, "updated_at": _utc_now()}},
            return_document=ReturnDocument.AFTER,
        )
        return _doc_to_response(result) if result else None

    def delete(self, rag_id: str) -> bool:
        coll = rags_collection()
        return coll.delete_one({"_id": rag_id}).deleted_count > 0

    def delete_many(self, rag_ids: list[str]) -> int:
        coll = rags_collection()
        return coll.delete_many({"_id": {"$in": rag_ids}}).deleted_count

from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from settings import DEFAULT_EMBEDDING_MODELS, EMBEDDING_PROVIDER


class VectorStoreProvider(str, Enum):
    qdrant = "qdrant"
    weaviate = "weaviate"
    pinecone = "pinecone"


class EmbeddingModel(str, Enum):
    # OpenAI
    text_embedding_3_small = "text-embedding-3-small"
    text_embedding_3_large = "text-embedding-3-large"
    text_embedding_ada_002 = "text-embedding-ada-002"
    # Google Gemini
    text_embedding_004 = "text-embedding-004"
    embedding_001 = "embedding-001"
    gemini_embedding_001 = "gemini-embedding-001"
    gemini_embedding_2 = "gemini-embedding-2"
    gemini_embedding_2_preview = "gemini-embedding-2-preview"


# Added this because Qdrant requires a fixed vector size at collection creation time.
# Maps each model to its output dimension; used in RAGCreate and chunk_store.create_collection.
EMBEDDING_DIMENSIONS: dict[EmbeddingModel, int] = {
    EmbeddingModel.text_embedding_3_small: 1536,
    EmbeddingModel.text_embedding_3_large: 3072,
    EmbeddingModel.text_embedding_ada_002: 1536,
    EmbeddingModel.text_embedding_004: 768,
    EmbeddingModel.embedding_001: 768,
    EmbeddingModel.gemini_embedding_001: 3072,
    EmbeddingModel.gemini_embedding_2: 3072,
    EmbeddingModel.gemini_embedding_2_preview: 3072,
}


def embedding_dimensions_for(model: EmbeddingModel) -> int:
    return EMBEDDING_DIMENSIONS[model]


# Added this because we need per-provider model validation without hitting the API.
# Used in RAGCreate.resolve_and_validate_model to reject mismatched provider/model pairs.
_PROVIDER_MODELS: dict[str, set[str]] = {
    "openai": {"text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"},
    "gemini": {"text-embedding-004", "embedding-001", "gemini-embedding-001", "gemini-embedding-2", "gemini-embedding-2-preview"},
}


# ── RAG config CRUD ───────────────────────────────────────────────────────────

class RAGCreate(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "name": "My RAG",
                    "description": "A knowledge base using Gemini embeddings.",
                    "vector_store": "qdrant",
                    "embedding_provider": "gemini",
                    "embedding_model": "text-embedding-004",
                },
                {
                    "name": "My RAG",
                    "description": "A knowledge base using OpenAI embeddings.",
                    "vector_store": "qdrant",
                    "embedding_provider": "openai",
                    "embedding_model": "text-embedding-3-small",
                },
            ]
        }
    )

    name: str = Field(default="Untitled RAG", min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=500)
    vector_store: VectorStoreProvider
    embedding_provider: Literal["openai", "gemini"] = Field(default=EMBEDDING_PROVIDER)
    embedding_model: EmbeddingModel | None = Field(default=None)

    @model_validator(mode="after")
    def resolve_and_validate_model(self) -> "RAGCreate":
        if self.embedding_model is None:
            self.embedding_model = EmbeddingModel(DEFAULT_EMBEDDING_MODELS[self.embedding_provider])
        elif self.embedding_model.value not in _PROVIDER_MODELS[self.embedding_provider]:
            valid = sorted(_PROVIDER_MODELS[self.embedding_provider])
            raise ValueError(
                f"Model '{self.embedding_model.value}' does not belong to provider "
                f"'{self.embedding_provider}'. Valid models: {valid}"
            )
        return self


class RAGUpdate(BaseModel):
    description: str | None = Field(default=None, max_length=500)


class RAGDeleteBulkRequest(BaseModel):
    ids: list[str] = Field(..., min_length=1)


class RAGDeleteBulkResponse(BaseModel):
    deleted: int


class RAGResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    vector_store: VectorStoreProvider
    embedding_provider: str
    embedding_model: EmbeddingModel
    embedding_dimensions: int
    created_at: datetime
    updated_at: datetime


# ── Chunks ────────────────────────────────────────────────────────────────────

class RAGChunk(BaseModel):
    id: str
    rag_id: str
    name: str
    data: str
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


class RAGTextInsert(BaseModel):
    name: str = Field(..., min_length=1)
    data: str = Field(..., min_length=1)
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    chunk_size: int = Field(default=1000, ge=100, le=8000)
    chunk_overlap: int = Field(default=200, ge=0, le=2000)


class RAGInsertResponse(BaseModel):
    chunks_created: int
    chunks: list["RAGChunk"]


# ── Chat / retrieval ──────────────────────────────────────────────────────────

class RAGChunkResult(RAGChunk):
    # Added this to surface retrieval score alongside chunk data in the query response.
    score: float


class RAGChatRequest(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(default=10, ge=1, le=100)
    retrieval_type: Literal["basic", "mmr", "hyde", "time_aware"] = Field(default="basic")
    lambda_param: float = Field(default=0.6, ge=0.0, le=1.0)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    time_decay_factor: float = Field(default=0.7, ge=0.0, le=1.0)
    filters: dict[str, Any] | None = None


class RAGChatResponse(BaseModel):
    query: str
    retrieval_type: str
    top_k: int
    total_found: int
    chunks: list[RAGChunkResult]

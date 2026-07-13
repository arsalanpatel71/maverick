import asyncio
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, File, Form, status

from rag.schemas import (
    RAGChatRequest,
    RAGChatResponse,
    RAGChunk,
    RAGChunkResult,
    RAGCreate,
    RAGDeleteBulkRequest,
    RAGDeleteBulkResponse,
    RAGInsertResponse,
    RAGResponse,
    RAGTextInsert,
    RAGUpdate,
)
from rag.services.chunk_store import ChunkStore, get_chunk_store_instance
from rag.services.embedder import embed_texts, _resolve_provider
from rag.services.rag_store import RagStore
from rag.services.splitter import split_text
from services.pagination import PageParams, PagedResponse, get_page_params, paginate
from settings import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/rags", tags=["rags"])

# Added this because we only want to accept plain text-type files to keep parsing simple.
# Used in insert_file to reject binary formats before reading the file.
_SUPPORTED_TEXT_TYPES = {
    "text/plain", "text/markdown", "text/csv", "text/html",
    "application/json", "application/xml", "text/xml",
}


def get_rag_store() -> RagStore:
    return RagStore()


def get_chunk_store() -> ChunkStore:
    return get_chunk_store_instance()


# Added this because embedding API key resolution differs by provider (Gemini vs OpenAI).
# Used in insert_text, insert_file, and chat_with_rag.
def _api_key_for_model(model: str, settings: Settings) -> str:
    return settings.google_api_key if _resolve_provider(model) == "gemini" else settings.openai_api_key


# Added this because splitting and embedding always happen together before any insert.
# Returns (parts, embeddings); used in insert_text and insert_file.
async def _split_and_embed(
    text: str,
    chunk_size: int,
    chunk_overlap: int,
    embedding_model: str,
    api_key: str,
) -> tuple[list[str], list[list[float]]]:
    parts = await asyncio.to_thread(split_text, text, chunk_size, chunk_overlap)
    if not api_key:
        raise ValueError(f"No API key configured for embedding model '{embedding_model}'")
    embeddings = await embed_texts(parts, embedding_model, api_key)
    return parts, embeddings


async def _embed_query(text: str, embedding_model: str, api_key: str) -> list[float]:
    if not api_key:
        raise ValueError(f"No API key configured for embedding model '{embedding_model}'")
    vectors = await embed_texts([text], embedding_model, api_key)
    if not vectors:
        raise ValueError("Embedding API returned an empty response")
    return vectors[0]


# Added this to improve retrieval quality — generates a hypothetical answer doc first (HyDE).
# Used in chat_with_rag when retrieval_type == "hyde". Falls back to original query on error.
async def _generate_hyde_doc(query: str, model: str, settings: Settings) -> str:
    prompt = (
        "Write a detailed, factual document that directly answers the following "
        "question. Return only the document content — no preamble, no labels.\n\n"
        f"Question: {query}"
    )
    try:
        if _resolve_provider(model) == "gemini" and settings.google_api_key:
            from google import genai
            client = genai.Client(api_key=settings.google_api_key)
            resp = await client.aio.models.generate_content(model="gemini-2.0-flash", contents=prompt)
            return resp.text or query

        if settings.openai_api_key:
            from openai import AsyncOpenAI
            client = AsyncOpenAI(api_key=settings.openai_api_key)
            resp = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=512,
                temperature=0.7,
            )
            return resp.choices[0].message.content or query
    except Exception:
        logger.exception("HyDE document generation failed — using original query")
    return query


# ── RAG config CRUD ───────────────────────────────────────────────────────────

@router.post("/", response_model=RAGResponse, status_code=status.HTTP_201_CREATED)
async def create_rag(
    body: RAGCreate,
    store: RagStore = Depends(get_rag_store),
    chunks: ChunkStore = Depends(get_chunk_store),
) -> RAGResponse:
    rag = await asyncio.to_thread(
        lambda: store.create(
            name=body.name,
            description=body.description,
            vector_store=body.vector_store,
            embedding_provider=body.embedding_provider,
            embedding_model=body.embedding_model,
        )
    )
    await asyncio.to_thread(chunks.create_collection, rag.id, rag.embedding_dimensions)
    return rag


@router.get("/", response_model=PagedResponse)
async def list_rags(
    q: str | None = Query(None),
    paging: PageParams = Depends(get_page_params),
    store: RagStore = Depends(get_rag_store),
) -> PagedResponse:
    items = await asyncio.to_thread(store.list_all, q)
    return paginate(items, paging)


@router.get("/{rag_id}", response_model=RAGResponse)
async def get_rag(rag_id: str, store: RagStore = Depends(get_rag_store)) -> RAGResponse:
    rag = await asyncio.to_thread(store.get, rag_id)
    if rag is None:
        raise HTTPException(status_code=404, detail="RAG not found")
    return rag


@router.patch("/{rag_id}", response_model=RAGResponse)
async def update_rag(
    rag_id: str,
    body: RAGUpdate,
    store: RagStore = Depends(get_rag_store),
) -> RAGResponse:
    updated = await asyncio.to_thread(store.update, rag_id, body.description)
    if updated is None:
        raise HTTPException(status_code=404, detail="RAG not found")
    return updated


@router.delete("/{rag_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rag(
    rag_id: str,
    store: RagStore = Depends(get_rag_store),
    chunks: ChunkStore = Depends(get_chunk_store),
) -> Response:
    ok = await asyncio.to_thread(store.delete, rag_id)
    if not ok:
        raise HTTPException(status_code=404, detail="RAG not found")
    await asyncio.to_thread(chunks.delete_for_rag, rag_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/bulk-delete", response_model=RAGDeleteBulkResponse)
async def bulk_delete_rags(
    body: RAGDeleteBulkRequest,
    store: RagStore = Depends(get_rag_store),
    chunks: ChunkStore = Depends(get_chunk_store),
) -> RAGDeleteBulkResponse:
    deleted = await asyncio.to_thread(store.delete_many, body.ids)
    for rag_id in body.ids:
        await asyncio.to_thread(chunks.delete_for_rag, rag_id)
    return RAGDeleteBulkResponse(deleted=deleted)


# ── Data listing ──────────────────────────────────────────────────────────────

@router.get("/{rag_id}/data", response_model=list[RAGChunk])
async def list_rag_data(
    rag_id: str,
    store: RagStore = Depends(get_rag_store),
    chunks: ChunkStore = Depends(get_chunk_store),
) -> list[RAGChunk]:
    rag = await asyncio.to_thread(store.get, rag_id)
    if rag is None:
        raise HTTPException(status_code=404, detail="RAG not found")
    return await asyncio.to_thread(chunks.list_for_rag, rag_id)


# ── Data ingestion ────────────────────────────────────────────────────────────

@router.post("/{rag_id}/data/text", response_model=RAGInsertResponse, status_code=status.HTTP_201_CREATED)
async def insert_text(
    rag_id: str,
    body: RAGTextInsert,
    store: RagStore = Depends(get_rag_store),
    chunks: ChunkStore = Depends(get_chunk_store),
    settings: Settings = Depends(get_settings),
) -> RAGInsertResponse:
    rag = await asyncio.to_thread(store.get, rag_id)
    if rag is None:
        raise HTTPException(status_code=404, detail="RAG not found")

    try:
        parts, embeddings = await _split_and_embed(
            text=body.data,
            chunk_size=body.chunk_size,
            chunk_overlap=body.chunk_overlap,
            embedding_model=rag.embedding_model.value,
            api_key=_api_key_for_model(rag.embedding_model.value, settings),
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding failed: {e}")

    def _store() -> list[RAGChunk]:
        return chunks.insert_many(
            rag_id=rag_id, name=body.name, parts=parts,
            source=body.source, metadata=body.metadata, embeddings=embeddings,
        )

    created = await asyncio.to_thread(_store)
    return RAGInsertResponse(chunks_created=len(created), chunks=created)


@router.post("/{rag_id}/data/files", response_model=RAGInsertResponse, status_code=status.HTTP_201_CREATED)
async def insert_file(
    rag_id: str,
    file: UploadFile = File(...),
    name: str | None = Form(default=None),
    source: str | None = Form(default=None),
    chunk_size: int = Form(default=1000, ge=100, le=8000),
    chunk_overlap: int = Form(default=200, ge=0, le=2000),
    store: RagStore = Depends(get_rag_store),
    chunks: ChunkStore = Depends(get_chunk_store),
    settings: Settings = Depends(get_settings),
) -> RAGInsertResponse:
    rag = await asyncio.to_thread(store.get, rag_id)
    if rag is None:
        raise HTTPException(status_code=404, detail="RAG not found")

    content_type = (file.content_type or "").split(";")[0].strip()
    if content_type and content_type not in _SUPPORTED_TEXT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type '{content_type}'. Supported: {sorted(_SUPPORTED_TEXT_TYPES)}",
        )

    raw = await file.read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="File could not be decoded as UTF-8 text.")

    if not text.strip():
        raise HTTPException(status_code=422, detail="File is empty.")

    chunk_name = name or file.filename or "Uploaded file"
    file_metadata = {"filename": file.filename or "", "content_type": content_type}

    try:
        parts, embeddings = await _split_and_embed(
            text=text,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            embedding_model=rag.embedding_model.value,
            api_key=_api_key_for_model(rag.embedding_model.value, settings),
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding failed: {e}")

    def _store() -> list[RAGChunk]:
        return chunks.insert_many(
            rag_id=rag_id, name=chunk_name, parts=parts,
            source=source, metadata=file_metadata, embeddings=embeddings,
        )

    created = await asyncio.to_thread(_store)
    return RAGInsertResponse(chunks_created=len(created), chunks=created)


# ── Retrieval ─────────────────────────────────────────────────────────────────

@router.post("/{rag_id}/chat", response_model=RAGChatResponse)
async def chat_with_rag(
    rag_id: str,
    body: RAGChatRequest,
    store: RagStore = Depends(get_rag_store),
    chunks: ChunkStore = Depends(get_chunk_store),
    settings: Settings = Depends(get_settings),
) -> RAGChatResponse:
    rag = await asyncio.to_thread(store.get, rag_id)
    if rag is None:
        raise HTTPException(status_code=404, detail="RAG not found")

    embedding_model = rag.embedding_model.value
    api_key = _api_key_for_model(embedding_model, settings)

    try:
        if body.retrieval_type == "hyde":
            hyde_doc = await _generate_hyde_doc(body.query, embedding_model, settings)
            query_embedding = await _embed_query(hyde_doc, embedding_model, api_key)
        else:
            query_embedding = await _embed_query(body.query, embedding_model, api_key)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Embedding failed: {e}")

    def _run() -> list[tuple[RAGChunk, float]]:
        return chunks.search_scored(
            rag_id=rag_id,
            query_embedding=query_embedding,
            retrieval_type=body.retrieval_type,
            top_k=body.top_k,
            lambda_param=body.lambda_param,
            score_threshold=body.score_threshold,
            time_decay_factor=body.time_decay_factor,
            filters=body.filters,
        )

    scored_results = await asyncio.to_thread(_run)
    chunk_results = [
        RAGChunkResult(**chunk.model_dump(), score=round(score, 6))
        for chunk, score in scored_results
    ]

    return RAGChatResponse(
        query=body.query,
        retrieval_type=body.retrieval_type,
        top_k=body.top_k,
        total_found=len(chunk_results),
        chunks=chunk_results,
    )

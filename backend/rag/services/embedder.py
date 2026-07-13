"""Text embedding implementations.

Provider and backend are controlled by rag/config.py — edit that file to switch.

Provider routing
────────────────
  EMBEDDING_PROVIDER = "openai"  →  OpenAI SDK or LangChain (per OPENAI_EMBEDDING_BACKEND)
  EMBEDDING_PROVIDER = "gemini"  →  Google GenAI SDK

Model-name override: if a model name unambiguously belongs to one provider
(e.g. "text-embedding-004" for Gemini), that provider is always used regardless
of EMBEDDING_PROVIDER. This keeps existing RAGs working even if you change the default.
"""
from __future__ import annotations

from settings import EMBEDDING_PROVIDER, OPENAI_EMBEDDING_BACKEND

_GEMINI_MODELS = {"text-embedding-004", "embedding-001", "gemini-embedding-001", "gemini-embedding-2", "gemini-embedding-2-preview"}
_OPENAI_MODELS = {"text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"}


def is_gemini_model(model: str) -> bool:
    return model in _GEMINI_MODELS


def _resolve_provider(model: str) -> str:
    """Determine the embedding provider for a given model name.

    Explicit model names take priority over the EMBEDDING_PROVIDER config so
    that RAGs created under one provider keep working after the config changes.
    """
    if model in _GEMINI_MODELS:
        return "gemini"
    if model in _OPENAI_MODELS:
        return "openai"
    return EMBEDDING_PROVIDER  


async def embed_texts(
    texts: list[str],
    model: str,
    api_key: str,
) -> list[list[float]]:
    """Embed a batch of texts. Returns one float vector per input text."""
    provider = _resolve_provider(model)
    if provider == "gemini":
        return await _gemini_embed(texts, model, api_key)
    if OPENAI_EMBEDDING_BACKEND == "langchain":
        return await _langchain_embed(texts, model, api_key)
    return await _openai_embed(texts, model, api_key)


# ─── Google Gemini ────────────────────────────────────────────────────────────


async def _gemini_embed(texts: list[str], model: str, api_key: str) -> list[list[float]]:
    import httpx

    embeddings: list[list[float]] = []
    async with httpx.AsyncClient(timeout=30.0) as http:
        for text in texts:
            resp = await http.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{model}:embedContent",
                params={"key": api_key},
                json={
                    "model": f"models/{model}",
                    "content": {"parts": [{"text": text}]},
                    "taskType": "RETRIEVAL_DOCUMENT",
                },
            )
            resp.raise_for_status()
            embeddings.append(resp.json()["embedding"]["values"])
    return embeddings


# ─── Raw OpenAI SDK ───────────────────────────────────────────────────────────


async def _openai_embed(texts: list[str], model: str, api_key: str) -> list[list[float]]:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=api_key)
    response = await client.embeddings.create(model=model, input=texts)
    ordered = sorted(response.data, key=lambda e: e.index)
    return [item.embedding for item in ordered]


# ─── LangChain ────────────────────────────────────────────────────────────────


async def _langchain_embed(texts: list[str], model: str, api_key: str) -> list[list[float]]:
    from langchain_openai import OpenAIEmbeddings

    embedder = OpenAIEmbeddings(model=model, api_key=api_key)
    return await embedder.aembed_documents(texts)

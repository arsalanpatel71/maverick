"""WebSocket endpoint for real-time agent tracing.

Each connection handles one request-response cycle and emits JSON trace events
as the agent works: memory load → RAG retrieval → LLM call → response.
All events are also persisted to the `traces` MongoDB collection.

Event envelope:
    {"event": "trace",    "type": "<step>",   "data": {...}, "ts": "<iso>"}
    {"event": "response", "content": "...",   "usage": {...}, "trace_id": "..."}
    {"event": "error",    "detail": "..."}
    {"event": "done",     "trace_id": "..."}
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect

from agents.registry import PROVIDERS
from agents.schemas import (
    AgentChatRequest,
    AgentResponse,
    ConversationMessage,
    RAGConfig,
)
from services.structured import StructuredParser
from agents.services.agent_store import (
    AgentStore,
    SessionMemory,
    TraceStore,
)
from agents.system_prompt import append_extra_prompt, build_agent_system_prompt, build_manager_system_prompt
from rag.services.chunk_store import ChunkStore
from rag.services.rag_store import RagStore
from rag.services.embedder import embed_texts, _resolve_provider
from services.guardrails import GuardrailViolation, check_input, redact_input, scrub_output
from settings import Settings, get_settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


# ── Dependency helpers ────────────────────────────────────────────────────────

def _agent_store() -> AgentStore:
    return AgentStore()

def _session_memory() -> SessionMemory:
    return SessionMemory()

def _trace_store() -> TraceStore:
    return TraceStore()

def _rag_store() -> RagStore:
    return RagStore()

def _chunk_store(settings: Settings = Depends(get_settings)) -> ChunkStore:
    return ChunkStore(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)


# ── Internal helpers ──────────────────────────────────────────────────────────

def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


async def _send(ws: WebSocket, event: str, **kwargs) -> None:
    await ws.send_json({"event": event, "ts": _ts(), **kwargs})


async def _send_trace(ws: WebSocket, trace_store: TraceStore, trace_id: str, event_type: str, data: dict) -> None:
    await _send(ws, "trace", type=event_type, data=data)
    await asyncio.to_thread(trace_store.append_event, trace_id, event_type, data)


async def _retrieve_rag(
    rag_config: RAGConfig,
    query: str,
    rag_store: RagStore,
    chunk_store: ChunkStore,
    settings: Settings,
) -> tuple[str, list[dict]]:
    """Returns (context_block_for_system_prompt, raw_chunks_for_trace)."""
    all_scored = []

    for rag_id in rag_config.rag_ids:
        rag = await asyncio.to_thread(rag_store.get, rag_id)
        if rag is None:
            logger.warning("RAG %s not found — skipping", rag_id)
            continue

        model = rag.embedding_model.value
        api_key = settings.google_api_key if _resolve_provider(model) == "gemini" else settings.openai_api_key
        try:
            vectors = await embed_texts([query], model, api_key)
            query_embedding = vectors[0]
        except Exception:
            logger.exception("Failed to embed query for RAG %s — skipping", rag_id)
            continue

        def _search(rid=rag_id, emb=query_embedding):
            return chunk_store.search_scored(
                rag_id=rid,
                query_embedding=emb,
                retrieval_type=rag_config.retrieval_type,
                top_k=rag_config.top_k,
                lambda_param=rag_config.lambda_param,
                score_threshold=rag_config.score_threshold,
                time_decay_factor=rag_config.time_decay_factor,
                filters=None,
            )

        try:
            results = await asyncio.to_thread(_search)
            all_scored.extend([(rag_id, chunk, score) for chunk, score in results])
        except Exception:
            logger.exception("RAG search failed for %s — skipping", rag_id)

    if not all_scored:
        return "", []

    all_scored.sort(key=lambda x: x[2], reverse=True)
    top = all_scored[: rag_config.top_k]

    # Build system prompt context block
    lines = ["--- Relevant Context ---"]
    for i, (_, chunk, _score) in enumerate(top, 1):
        source = f" (source: {chunk.source})" if chunk.source else ""
        lines.append(f"[{i}]{source}\n{chunk.data}")
    lines.append("--- End of Context ---")
    context_str = "\n\n".join(lines)

    # Build trace-friendly chunk list
    trace_chunks = [
        {
            "rag_id": rag_id,
            "chunk_id": chunk.id,
            "name": chunk.name,
            "score": round(score, 4),
            "data": chunk.data[:300] + ("…" if len(chunk.data) > 300 else ""),
            "source": chunk.source,
        }
        for rag_id, chunk, score in top
    ]

    return context_str, trace_chunks


# ── Manager routing ──────────────────────────────────────────────────────────

async def _run_manager(
    *,
    websocket: WebSocket,
    trace_store: TraceStore,
    trace_id: str,
    agent: AgentResponse,
    handler,
    agent_store: AgentStore,
    system: str,
    clean_message: str,
    history: list,
    pii_redacted: list,
    settings,
) -> tuple:
    await _send_trace(websocket, trace_store, trace_id, "manager_routing", {
        "managed_agents": [{"id": a.id, "name": a.name} for a in agent.managed_agents],
    })

    routing_system = system
    if agent.response_schema:
        routing_system = (
            f"{system}\n\n"
            f"When answering the user directly (no delegation needed), respond with ONLY valid JSON "
            f"matching the '{agent.response_schema.name}' schema:\n"
            f"{json.dumps(agent.response_schema.json_schema, indent=2)}\n"
            f"Use {{\"delegate\": [...]}} ONLY when delegating — never for direct answers."
        )

    routing_result = await handler(AgentChatRequest(
        prompt=clean_message,
        system=routing_system,
        model=agent.model,
        provider=agent.provider,
        history=history,
    ), settings)

    routing_content = routing_result.content.strip()

    if "```" in routing_content:
        block = routing_content.split("```")[1]
        routing_content = block[4:].strip() if block.startswith("json") else block.strip()

    try:
        decision = json.loads(routing_content)
        delegations = decision.get("delegate", [])
    except (json.JSONDecodeError, ValueError):
        delegations = []

    if not delegations:
        structured_output: dict | None = None
        if agent.response_schema:
            try:
                structured_output = StructuredParser.parse(routing_result.content)
                routing_result.structured_output = structured_output
                routing_result.content = json.dumps(structured_output)
            except ValueError:
                logger.warning("Manager direct answer did not parse as structured JSON")

        routing_result.content = scrub_output(routing_result.content)
        routing_result.pii_redacted = pii_redacted
        usage_dict = None
        if routing_result.usage:
            usage_dict = {
                "input_tokens": routing_result.usage.input_tokens,
                "output_tokens": routing_result.usage.output_tokens,
            }

        await _send_trace(websocket, trace_store, trace_id, "llm_end", {
            "model": routing_result.model,
            "usage": usage_dict,
            "structured_output": structured_output,
        })
        return routing_result, usage_dict

    await _send_trace(websocket, trace_store, trace_id, "manager_delegating", {
        "delegations": delegations,
    })

    child_results = []
    for delegation in delegations:
        child_id = delegation.get("agent_id", "")
        child_task = delegation.get("task", clean_message)

        child_agent = await asyncio.to_thread(agent_store.get, child_id)
        if child_agent is None:
            child_results.append({"agent_name": child_id, "task": child_task, "result": "Error: agent not found"})
            continue

        child_handler = PROVIDERS.get(child_agent.provider)
        if child_handler is None:
            child_results.append({"agent_name": child_agent.name, "task": child_task, "result": "Error: provider not found"})
            continue

        await _send_trace(websocket, trace_store, trace_id, "manager_agent_call", {
            "agent_id": child_id,
            "agent_name": child_agent.name,
            "task": child_task,
        })

        child_req = AgentChatRequest(
            prompt=child_task,
            system=build_agent_system_prompt(child_agent.role, child_agent.goal, child_agent.instructions),
            model=child_agent.model,
            provider=child_agent.provider,
        )
        child_result = await child_handler(child_req, settings)

        await _send_trace(websocket, trace_store, trace_id, "manager_agent_result", {
            "agent_id": child_id,
            "agent_name": child_agent.name,
            "result_preview": child_result.content[:300],
        })

        child_results.append({
            "agent_name": child_agent.name,
            "task": child_task,
            "result": child_result.content,
        })

    results_text = "\n\n".join(
        f"**{r['agent_name']}** (task: {r['task']}):\n{r['result']}"
        for r in child_results
    )
    synthesis_prompt = (
        f"Original user question: {clean_message}\n\n"
        f"Results from your agents:\n{results_text}\n\n"
        f"Synthesize a clear, final answer for the user."
    )

    await _send_trace(websocket, trace_store, trace_id, "manager_synthesis", {
        "child_agents_called": len(child_results),
    })

    synthesis_result = await handler(AgentChatRequest(
        prompt=synthesis_prompt,
        system=build_agent_system_prompt(agent.role, agent.goal, agent.instructions),
        model=agent.model,
        provider=agent.provider,
        history=history,
        response_schema=agent.response_schema,
    ), settings)

    synthesis_result.content = scrub_output(synthesis_result.content)
    synthesis_result.pii_redacted = pii_redacted

    usage_dict = None
    if synthesis_result.usage:
        usage_dict = {
            "input_tokens": synthesis_result.usage.input_tokens,
            "output_tokens": synthesis_result.usage.output_tokens,
        }

    await _send_trace(websocket, trace_store, trace_id, "llm_end", {
        "model": synthesis_result.model,
        "usage": usage_dict,
        "structured_output": synthesis_result.structured_output,
    })

    return synthesis_result, usage_dict


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/ws/chat")
async def ws_chat(
    websocket: WebSocket,
    settings: Settings = Depends(get_settings),
) -> None:
    """
    Connect, send one JSON message, receive streaming trace events + final response.

    Send:
        {
            "agent_id": "...",
            "session_id": "...",          // optional — required for memory
            "message": "...",
            "extra_prompt": {}            // optional
        }

    Receive (in order):
        {"event": "trace", "type": "trace_start",    "data": {...}}
        {"event": "trace", "type": "memory_loaded",  "data": {...}}
        {"event": "trace", "type": "rag_start",      "data": {...}}
        {"event": "trace", "type": "rag_result",     "data": {...}}
        {"event": "trace", "type": "llm_start",      "data": {...}}
        {"event": "trace", "type": "llm_end",        "data": {...}}
        {"event": "response", "content": "...", "usage": {...}, "trace_id": "..."}
        {"event": "done", "trace_id": "..."}
    """
    await websocket.accept()

    agent_store = _agent_store()
    session_memory = _session_memory()
    trace_store = _trace_store()
    rag_store = _rag_store()
    chunk_store = ChunkStore(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)

    try:
        while True:
            try:
                payload = await websocket.receive_json()
            except WebSocketDisconnect:
                logger.info("WebSocket client disconnected")
                return
            except Exception:
                await _send(websocket, "error", detail="Invalid JSON payload")
                continue

            agent_id = payload.get("agent_id", "")
            session_id = payload.get("session_id")
            raw_message = payload.get("message", "")
            extra_prompt = payload.get("extra_prompt", {})

            if not agent_id or not raw_message:
                await _send(websocket, "error", detail="agent_id and message are required")
                continue

            # Guardrails
            try:
                check_input(raw_message)
            except GuardrailViolation as e:
                await _send(websocket, "error", detail=e.detail)
                continue

            clean_message, pii_redacted = redact_input(raw_message)

            # Load agent
            agent: AgentResponse | None = await asyncio.to_thread(agent_store.get, agent_id)
            if agent is None:
                await _send(websocket, "error", detail="Agent not found")
                continue

            handler = PROVIDERS.get(agent.provider)
            if handler is None:
                await _send(websocket, "error", detail=f"Provider '{agent.provider.value}' is not implemented")
                continue

            # Create trace
            trace_id = await asyncio.to_thread(
                trace_store.create,
                agent_id=agent_id,
                session_id=session_id,
                query=clean_message,
            )

            try:
                is_manager = len(agent.managed_agents) > 0

                # ── trace_start ───────────────────────────────────────────────
                await _send_trace(websocket, trace_store, trace_id, "trace_start", {
                    "agent_id": agent_id,
                    "agent_role": agent.role,
                    "session_id": session_id,
                    "model": agent.model,
                    "provider": agent.provider.value,
                    "memory_enabled": agent.memory_enabled,
                    "has_rag": agent.rag_config is not None,
                    "is_manager": is_manager,
                    "managed_agents_count": len(agent.managed_agents),
                })

                # ── Memory ────────────────────────────────────────────────────
                use_memory = agent.memory_enabled and session_id is not None
                history: list[ConversationMessage] = []
                if use_memory:
                    history = await asyncio.to_thread(
                        session_memory.get_history,
                        session_id,
                        agent.memory_max_messages or 20,
                    )
                    await _send_trace(websocket, trace_store, trace_id, "memory_loaded", {
                        "session_id": session_id,
                        "messages_loaded": len(history),
                        "window": agent.memory_max_messages,
                        "history": [{"role": m.role, "content": m.content[:200]} for m in history],
                    })

                # ── Build system prompt ───────────────────────────────────────
                base_system = (
                    build_manager_system_prompt(agent.role, agent.goal, agent.instructions, agent.managed_agents)
                    if is_manager
                    else build_agent_system_prompt(agent.role, agent.goal, agent.instructions)
                )
                system = append_extra_prompt(base_system, extra_prompt)

                # ── RAG retrieval ─────────────────────────────────────────────
                if agent.rag_config:
                    await _send_trace(websocket, trace_store, trace_id, "rag_start", {
                        "rag_ids": agent.rag_config.rag_ids,
                        "retrieval_type": agent.rag_config.retrieval_type,
                        "top_k": agent.rag_config.top_k,
                        "query": clean_message,
                    })

                    rag_context, trace_chunks = await _retrieve_rag(
                        agent.rag_config, clean_message, rag_store, chunk_store, settings
                    )

                    await _send_trace(websocket, trace_store, trace_id, "rag_result", {
                        "chunks_found": len(trace_chunks),
                        "chunks": trace_chunks,
                    })

                    if rag_context:
                        system = f"{system}\n\n{rag_context}"

                # ── LLM call ──────────────────────────────────────────────────
                if is_manager:
                    result, usage_dict = await _run_manager(
                        websocket=websocket,
                        trace_store=trace_store,
                        trace_id=trace_id,
                        agent=agent,
                        handler=handler,
                        agent_store=agent_store,
                        system=system,
                        clean_message=clean_message,
                        history=history,
                        pii_redacted=pii_redacted,
                        settings=settings,
                    )
                else:
                    await _send_trace(websocket, trace_store, trace_id, "llm_start", {
                        "model": agent.model,
                        "provider": agent.provider.value,
                        "history_turns": len(history),
                        "has_rag_context": agent.rag_config is not None,
                        "has_response_schema": agent.response_schema is not None,
                    })

                    result = await handler(AgentChatRequest(
                        prompt=clean_message,
                        system=system,
                        model=agent.model,
                        provider=agent.provider,
                        history=history,
                        response_schema=agent.response_schema,
                    ), settings)
                    result.content = scrub_output(result.content)
                    result.pii_redacted = pii_redacted

                    usage_dict = None
                    if result.usage:
                        usage_dict = {
                            "input_tokens": result.usage.input_tokens,
                            "output_tokens": result.usage.output_tokens,
                        }

                    await _send_trace(websocket, trace_store, trace_id, "llm_end", {
                        "model": result.model,
                        "usage": usage_dict,
                        "structured_output": result.structured_output,
                    })

                # ── Save memory ───────────────────────────────────────────────
                if use_memory:
                    await asyncio.to_thread(
                        session_memory.add_turn,
                        session_id,
                        clean_message,
                        result.content,
                    )

                # ── Complete trace + send final response ──────────────────────
                await asyncio.to_thread(trace_store.complete, trace_id, result.content, usage_dict)

                await _send(websocket, "response",
                    content=result.content,
                    structured_output=result.structured_output,
                    usage=usage_dict,
                    pii_redacted=pii_redacted,
                    trace_id=trace_id,
                )
                await _send(websocket, "done", trace_id=trace_id)

            except WebSocketDisconnect:
                logger.info("WebSocket disconnected mid-stream for trace %s", trace_id)
                return
            except Exception as exc:
                logger.exception("WebSocket chat error for trace %s", trace_id)
                try:
                    await _send(websocket, "error", detail=str(exc))
                except Exception:
                    pass

    finally:
        try:
            await websocket.close()
        except Exception:
            pass


# ── Traces REST endpoints ─────────────────────────────────────────────────────

def _serialise_trace(doc: dict) -> dict:
    """Convert MongoDB doc to JSON-safe dict."""
    def _conv(v):
        if isinstance(v, datetime):
            return v.isoformat()
        if isinstance(v, dict):
            return {k: _conv(vv) for k, vv in v.items()}
        if isinstance(v, list):
            return [_conv(i) for i in v]
        return v
    return {k: _conv(v) for k, v in doc.items()}


@router.get("/{agent_id}/traces", tags=["agents"])
async def list_agent_traces(
    agent_id: str,
    limit: int = 50,
) -> list[dict]:
    """List recent traces for an agent (newest first). Events array omitted for brevity."""
    store = _trace_store()
    docs = await asyncio.to_thread(store.list_for_agent, agent_id, limit)
    return [_serialise_trace(d) for d in docs]


@router.get("/{agent_id}/traces/{trace_id}", tags=["agents"])
async def get_agent_trace(
    agent_id: str,
    trace_id: str,
) -> dict:
    """Return a single trace with all events."""
    store = _trace_store()
    doc = await asyncio.to_thread(store.get, trace_id)
    if doc is None or doc.get("agent_id") != agent_id:
        raise HTTPException(status_code=404, detail="Trace not found")
    return _serialise_trace(doc)

"""Shared agent execution generator — streams trace events + final response.

Used by both REST chat endpoints (simple + SSE stream). The WebSocket endpoint
keeps its own implementation and is left unchanged.

Each yield is a plain dict matching the existing event envelope:
    {"event": "trace",    "type": "...", "data": {...}, "ts": "..."}
    {"event": "response", "content": "...", "trace_id": "...", ...}
    {"event": "error",    "detail": "...", "ts": "..."}
    {"event": "done",     "trace_id": "...", "ts": "..."}

Internal-only event (consumed by caller, never forwarded to client):
    {"event": "_result",  "result": <AgentChatResponse>, "usage": {...}}
"""

import asyncio
import json
import logging
import re
from collections.abc import AsyncGenerator
from datetime import datetime, timezone

from agents.registry import PROVIDERS
from agents.schemas import AgentChatRequest, AgentProvider, AgentResponse, ConversationMessage, RAGConfig
from agents.services.agent_store import AgentStore, SessionMemory, TraceStore
from agents.system_prompt import append_capsule_tool_rules, append_extra_prompt, append_no_file_disclaimer_rules, append_skills, build_agent_system_prompt, build_manager_system_prompt, format_skills_catalog
from rag.services.chunk_store import ChunkStore
from rag.services.embedder import _resolve_provider, embed_texts
from rag.services.rag_store import RagStore
from services.guardrails import GuardrailViolation, check_input, redact_input, scrub_output
from services.structured import StructuredParser
from settings import Settings

logger = logging.getLogger(__name__)


def _ts() -> str:
    return datetime.now(timezone.utc).isoformat()


def _te(event_type: str, data: dict) -> dict:
    return {"event": "trace", "type": event_type, "data": data, "ts": _ts()}


async def _retrieve_rag(
    rag_config: RAGConfig,
    query: str,
    rag_store: RagStore,
    chunk_store: ChunkStore,
    settings: Settings,
) -> tuple[str, list[dict]]:
    all_scored = []
    for rag_id in rag_config.rag_ids:
        rag = await asyncio.to_thread(rag_store.get, rag_id)
        if rag is None:
            continue
        model = rag.embedding_model.value
        api_key = settings.google_api_key if _resolve_provider(model) == "gemini" else settings.openai_api_key
        try:
            vectors = await embed_texts([query], model, api_key)
            query_embedding = vectors[0]
        except Exception:
            logger.exception("Embed failed for RAG %s", rag_id)
            continue

        def _search(rid=rag_id, emb=query_embedding):
            return chunk_store.search_scored(
                rag_id=rid, query_embedding=emb,
                retrieval_type=rag_config.retrieval_type, top_k=rag_config.top_k,
                lambda_param=rag_config.lambda_param, score_threshold=rag_config.score_threshold,
                time_decay_factor=rag_config.time_decay_factor, filters=None,
            )
        try:
            results = await asyncio.to_thread(_search)
            all_scored.extend([(rag_id, chunk, score) for chunk, score in results])
        except Exception:
            logger.exception("RAG search failed for %s", rag_id)

    if not all_scored:
        return "", []

    all_scored.sort(key=lambda x: x[2], reverse=True)
    top = all_scored[: rag_config.top_k]

    lines = ["--- Relevant Context ---"]
    for i, (_, chunk, _score) in enumerate(top, 1):
        source = f" (source: {chunk.source})" if chunk.source else ""
        lines.append(f"[{i}]{source}\n{chunk.data}")
    lines.append("--- End of Context ---")

    trace_chunks = [
        {
            "rag_id": rid, "chunk_id": chunk.id, "name": chunk.name,
            "score": round(score, 4),
            "data": chunk.data[:300] + ("…" if len(chunk.data) > 300 else ""),
            "source": chunk.source,
        }
        for rid, chunk, score in top
    ]
    return "\n\n".join(lines), trace_chunks


async def _run_tool(
    tc: "ToolCallRequest",
    *,
    agent_id: str,
    session_id: str | None,
    user_id: str | None,
    skill_map: dict[str, dict],
    capsule_ids: list[str],
    settings: "Settings",
) -> tuple[list[dict], str]:
    """Execute one tool call. Returns (trace_events, result_json_string)."""
    from capsules.tools import execute_create_capsule

    if tc.name == "get_skill_content":
        skill_id = tc.input.get("skill_id", "")
        skill = skill_map.get(skill_id)
        name = skill["name"] if skill else skill_id
        fetched = skill["content"] if skill else f"Skill '{skill_id}' not found."
        return [
            _te("skill_tool_call", {"skill_id": skill_id, "skill_name": name}),
            _te("skill_tool_result", {"skill_id": skill_id, "skill_name": name, "content_length": len(fetched)}),
        ], fetched

    if tc.name == "create_capsule":
        capsule_name = tc.input.get("name", "Capsule")
        events: list[dict] = [_te("capsule_creating", {"name": capsule_name, "format_type": tc.input.get("format_type", "text")})]
        try:
            capsule_result = await execute_create_capsule(
                tc.input, agent_id=agent_id, session_id=session_id, user_id=user_id, settings=settings,
            )
            if capsule_result.get("success"):
                capsule_ids.append(capsule_result["capsule_id"])
            events.append(_te("capsule_created", {
                "capsule_id": capsule_result.get("capsule_id"),
                "name": capsule_result.get("name", capsule_name),
                "format_type": capsule_result.get("format_type"),
                "has_file": bool(capsule_result.get("file_url")),
            }))
            return events, json.dumps(capsule_result)
        except Exception as e:
            logger.exception("create_capsule tool failed")
            events.append(_te("capsule_error", {"detail": str(e)}))
            return events, json.dumps({"success": False, "error": str(e)})

    return [], json.dumps({"error": f"Unknown tool: {tc.name}"})


_CODE_BLOCK_RE = re.compile(r"```(\w+)?\n(.*?)```", re.DOTALL)
_LANG_FORMAT: dict[str, str] = {"json": "json", "md": "markdown", "markdown": "markdown"}

# (pattern, capsule format, use_file_output)
_FILE_REQUEST_PATTERNS: list[tuple[re.Pattern, str, bool]] = [
    (re.compile(r"\b(docx?|\.doc|word.doc|write.+doc|create.+doc|make.+doc)\b", re.I), "docx", True),
    (re.compile(r"\bpdf\b", re.I), "pdf", True),
    (re.compile(r"\b(xlsx?|excel|spreadsheet)\b", re.I), "xlsx", True),
    (re.compile(r"\b(pptx?|powerpoint|presentation|slides)\b", re.I), "pptx", True),
    (re.compile(r"\bcsv\b", re.I), "csv", True),
]


def _infer_name(user_message: str, fallback: str) -> str:
    """Derive a short capsule name from the user's request."""
    clean = re.sub(r"\b(write|create|make|generate|give me|show me|a|an|the|me|please)\b", "", user_message, flags=re.I)
    clean = re.sub(r"\s+", " ", clean).strip(" ,.!?")
    return clean[:60] if clean else fallback


async def _auto_detect_capsules(
    content: str,
    *,
    user_message: str = "",
    agent_id: str,
    session_id: str | None,
    user_id: str | None,
    settings: Settings,
) -> list[dict]:
    """
    Create capsules automatically from a non-Anthropic LLM response.

    Two detection paths:
    1. Code blocks in markdown (``` ... ```) → inline code/json capsules
    2. File format keywords in the user message (doc/pdf/xlsx/...) → file capsules
       using the full response content
    """
    from capsules.tools import execute_create_capsule

    created: list[dict] = []
    seen: set[int] = set()
    has_s3 = bool(settings.app_aws_access_key_id and settings.app_aws_storage_bucket_name)

    # ── Path 1: code blocks ───────────────────────────────────────────────────
    for match in _CODE_BLOCK_RE.finditer(content):
        lang = (match.group(1) or "text").lower().strip()
        code = match.group(2).strip()
        if not code or len(code) < 30:
            continue
        key = hash(code)
        if key in seen:
            continue
        seen.add(key)

        fmt = _LANG_FORMAT.get(lang, "code")
        def_match = re.search(r"^(?:def|class|function|func)\s+(\w+)", code, re.MULTILINE)
        name = def_match.group(1) if def_match else (
            f"{lang.capitalize()} script" if lang not in ("text", "code", "") else "Code snippet"
        )
        result = await execute_create_capsule(
            {
                "format_type": fmt,
                "name": name,
                "description": f"Generated {lang} code",
                "data": {"content": code},
                "language": lang if fmt == "code" else None,
            },
            agent_id=agent_id,
            session_id=session_id,
            user_id=user_id,
            settings=settings,
        )
        if result.get("success"):
            created.append(result)

    # ── Path 2: file format request from user message ─────────────────────────
    if user_message and not created:
        for pattern, fmt, wants_file in _FILE_REQUEST_PATTERNS:
            if pattern.search(user_message):
                file_output = wants_file and has_s3
                name = _infer_name(user_message, f"{fmt.upper()} document")
                result = await execute_create_capsule(
                    {
                        "format_type": fmt,
                        "name": name,
                        "description": f"Generated {fmt} from agent response",
                        "data": {"content": content},
                        "file_output": file_output,
                    },
                    agent_id=agent_id,
                    session_id=session_id,
                    user_id=user_id,
                    settings=settings,
                )
                if result.get("success"):
                    created.append(result)
                break

    return created


async def _stream_manager(
    *,
    agent: AgentResponse,
    handler,
    agent_store: AgentStore,
    system: str,
    clean_message: str,
    history: list,
    pii_redacted: list,
    settings: Settings,
) -> AsyncGenerator[dict, None]:
    yield _te("manager_routing", {
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
        prompt=clean_message, system=routing_system,
        model=agent.model, provider=agent.provider, history=history,
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
        structured_output = None
        if agent.response_schema:
            try:
                structured_output = StructuredParser.parse(routing_result.content)
                routing_result.structured_output = structured_output
                routing_result.content = json.dumps(structured_output)
            except ValueError:
                pass

        routing_result.content = scrub_output(routing_result.content)
        routing_result.pii_redacted = pii_redacted
        usage_dict = None
        if routing_result.usage:
            usage_dict = {"input_tokens": routing_result.usage.input_tokens, "output_tokens": routing_result.usage.output_tokens}

        yield _te("llm_end", {"model": routing_result.model, "usage": usage_dict, "structured_output": structured_output})
        yield {"event": "_result", "result": routing_result, "usage": usage_dict}
        return

    yield _te("manager_delegating", {"delegations": delegations})

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

        yield _te("manager_agent_call", {"agent_id": child_id, "agent_name": child_agent.name, "task": child_task})

        child_result = await child_handler(AgentChatRequest(
            prompt=child_task,
            system=build_agent_system_prompt(child_agent.role, child_agent.goal, child_agent.instructions),
            model=child_agent.model, provider=child_agent.provider,
        ), settings)

        yield _te("manager_agent_result", {
            "agent_id": child_id, "agent_name": child_agent.name,
            "result_preview": child_result.content[:300],
        })
        child_results.append({"agent_name": child_agent.name, "task": child_task, "result": child_result.content})

    results_text = "\n\n".join(
        f"**{r['agent_name']}** (task: {r['task']}):\n{r['result']}" for r in child_results
    )
    synthesis_prompt = (
        f"Original user question: {clean_message}\n\n"
        f"Results from your agents:\n{results_text}\n\n"
        f"Synthesize a clear, final answer for the user."
    )

    yield _te("manager_synthesis", {"child_agents_called": len(child_results)})

    synthesis_result = await handler(AgentChatRequest(
        prompt=synthesis_prompt,
        system=build_agent_system_prompt(agent.role, agent.goal, agent.instructions),
        model=agent.model, provider=agent.provider,
        history=history, response_schema=agent.response_schema,
    ), settings)

    synthesis_result.content = scrub_output(synthesis_result.content)
    synthesis_result.pii_redacted = pii_redacted
    usage_dict = None
    if synthesis_result.usage:
        usage_dict = {"input_tokens": synthesis_result.usage.input_tokens, "output_tokens": synthesis_result.usage.output_tokens}

    yield _te("llm_end", {"model": synthesis_result.model, "usage": usage_dict, "structured_output": synthesis_result.structured_output})
    yield {"event": "_result", "result": synthesis_result, "usage": usage_dict}


async def stream_agent_chat(
    *,
    agent_id: str,
    session_id: str | None,
    message: str,
    extra_prompt: dict,
    settings: Settings,
    user_id: str | None = None,
) -> AsyncGenerator[dict, None]:
    agent_store = AgentStore()
    session_memory = SessionMemory()
    trace_store = TraceStore()
    rag_store = RagStore()
    chunk_store = ChunkStore(url=settings.qdrant_url, api_key=settings.qdrant_api_key or None)

    try:
        check_input(message)
    except GuardrailViolation as e:
        yield {"event": "error", "detail": e.detail, "ts": _ts()}
        return

    clean_message, pii_redacted = redact_input(message)

    agent = await asyncio.to_thread(agent_store.get, agent_id)
    if agent is None:
        yield {"event": "error", "detail": "Agent not found", "ts": _ts()}
        return

    handler = PROVIDERS.get(agent.provider)
    if handler is None:
        yield {"event": "error", "detail": f"Provider '{agent.provider.value}' not implemented", "ts": _ts()}
        return

    trace_id = await asyncio.to_thread(
        trace_store.create, agent_id=agent_id, session_id=session_id, query=clean_message
    )
    is_manager = len(agent.managed_agents) > 0

    yield _te("trace_start", {
        "agent_id": agent_id, "agent_role": agent.role, "session_id": session_id,
        "model": agent.model, "provider": agent.provider.value,
        "memory_enabled": agent.memory_enabled, "has_rag": agent.rag_config is not None,
        "is_manager": is_manager, "managed_agents_count": len(agent.managed_agents),
    })

    use_memory = agent.memory_enabled and session_id is not None
    history: list[ConversationMessage] = []
    if use_memory:
        history = await asyncio.to_thread(session_memory.get_history, session_id, agent.memory_max_messages or 20)
        yield _te("memory_loaded", {
            "session_id": session_id, "messages_loaded": len(history),
            "window": agent.memory_max_messages,
            "history": [{"role": m.role, "content": m.content[:200]} for m in history],
        })

    base_system = (
        build_manager_system_prompt(agent.role, agent.goal, agent.instructions, agent.managed_agents)
        if is_manager
        else build_agent_system_prompt(agent.role, agent.goal, agent.instructions)
    )
    skill_docs: list[dict] = []
    if agent.skill_ids:
        from skills.store import SkillStore
        skill_docs = await asyncio.to_thread(SkillStore().get_many, agent.skill_ids)
        yield _te("skills_loaded", {
            "count": len(skill_docs),
            "skills": [{"id": s["_id"], "name": s["name"]} for s in skill_docs],
        })

    # Build system prompt — Anthropic gets a catalog + tool instruction; others get full content injected
    _tool_providers = {AgentProvider.anthropic, AgentProvider.openai, AgentProvider.google}
    use_skill_tools = bool(skill_docs) and agent.provider in _tool_providers
    if use_skill_tools:
        base_system = format_skills_catalog(base_system, skill_docs)
    elif skill_docs:
        base_system = append_skills(base_system, skill_docs)

    system = append_extra_prompt(base_system, extra_prompt)

    if agent.rag_config:
        yield _te("rag_start", {
            "rag_ids": agent.rag_config.rag_ids, "retrieval_type": agent.rag_config.retrieval_type,
            "top_k": agent.rag_config.top_k, "query": clean_message,
        })
        rag_context, trace_chunks = await _retrieve_rag(agent.rag_config, clean_message, rag_store, chunk_store, settings)
        yield _te("rag_result", {"chunks_found": len(trace_chunks), "chunks": trace_chunks})
        if rag_context:
            system = f"{system}\n\n{rag_context}"

    result = None
    usage_dict = None
    capsule_ids: list[str] = []

    if is_manager:
        async for event in _stream_manager(
            agent=agent, handler=handler, agent_store=agent_store,
            system=system, clean_message=clean_message,
            history=history, pii_redacted=pii_redacted, settings=settings,
        ):
            if event["event"] == "_result":
                result = event["result"]
                usage_dict = event["usage"]
            else:
                yield event

    elif agent.provider == AgentProvider.anthropic:
        from agents.services.anthropic_agent import GET_SKILL_CONTENT_TOOL, MAX_TOOL_TURNS, call_once
        from capsules.tools import CREATE_CAPSULE_TOOL

        system = append_capsule_tool_rules(system)
        skill_map: dict[str, dict] = {s["_id"]: s for s in skill_docs}
        model_name = agent.model or "claude-sonnet-4-6"
        tools: list[dict] = [CREATE_CAPSULE_TOOL]
        if use_skill_tools:
            tools.append(GET_SKILL_CONTENT_TOOL)

        messages: list[dict] = [{"role": m.role, "content": m.content} for m in history]
        messages.append({"role": "user", "content": clean_message})

        total_input = 0
        total_output = 0

        yield _te("llm_start", {
            "model": model_name, "provider": agent.provider.value,
            "history_turns": len(history), "has_rag_context": agent.rag_config is not None,
            "has_response_schema": agent.response_schema is not None,
            "mode": "skill_tools" if use_skill_tools else "capsule_tools",
        })

        for _turn in range(MAX_TOOL_TURNS + 1):
            turn_result = await call_once(model=model_name, messages=messages, system=system, tools=tools, settings=settings)
            if turn_result.usage:
                total_input += turn_result.usage.input_tokens or 0
                total_output += turn_result.usage.output_tokens or 0
            if not turn_result.tool_calls:
                result = turn_result
                break

            assistant_content: list[dict] = []
            if turn_result.content:
                assistant_content.append({"type": "text", "text": turn_result.content})
            for tc in turn_result.tool_calls:
                assistant_content.append({"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.input})
            messages.append({"role": "assistant", "content": assistant_content})

            tool_results_content: list[dict] = []
            for tc in turn_result.tool_calls:
                evts, result_str = await _run_tool(tc, agent_id=agent_id, session_id=session_id, user_id=user_id, skill_map=skill_map, capsule_ids=capsule_ids, settings=settings)
                for ev in evts:
                    yield ev
                tool_results_content.append({"type": "tool_result", "tool_use_id": tc.id, "content": result_str})
            messages.append({"role": "user", "content": tool_results_content})

        if result is None:
            final = await call_once(model=model_name, messages=messages, system=system, tools=[], settings=settings)
            result = final
            if final.usage:
                total_input += final.usage.input_tokens or 0
                total_output += final.usage.output_tokens or 0

        usage_dict = {"input_tokens": total_input, "output_tokens": total_output}
        result.content = scrub_output(result.content)
        result.pii_redacted = pii_redacted
        yield _te("llm_end", {"model": model_name, "usage": usage_dict, "structured_output": result.structured_output})

    elif agent.provider == AgentProvider.openai:
        from agents.services.anthropic_agent import GET_SKILL_CONTENT_TOOL
        from agents.services.openai_compat import MAX_TOOL_TURNS as OAI_MAX_TURNS, anthropic_to_openai_tool, call_once as openai_call_once
        from capsules.tools import CREATE_CAPSULE_TOOL

        system = append_capsule_tool_rules(system)
        skill_map = {s["_id"]: s for s in skill_docs}
        model_name = agent.model or "gpt-4o-mini"

        oa_tools = [anthropic_to_openai_tool(CREATE_CAPSULE_TOOL)]
        if use_skill_tools:
            oa_tools.append(anthropic_to_openai_tool(GET_SKILL_CONTENT_TOOL))

        oa_messages: list[dict] = [{"role": "system", "content": system}]
        for m in history:
            oa_messages.append({"role": m.role, "content": m.content})
        oa_messages.append({"role": "user", "content": clean_message})

        total_input = 0
        total_output = 0

        yield _te("llm_start", {
            "model": model_name, "provider": agent.provider.value,
            "history_turns": len(history), "has_rag_context": agent.rag_config is not None,
            "has_response_schema": agent.response_schema is not None,
            "mode": "skill_tools" if use_skill_tools else "capsule_tools",
        })

        for _turn in range(OAI_MAX_TURNS + 1):
            turn_result = await openai_call_once(
                model=model_name, messages=oa_messages, tools=oa_tools,
                api_key=settings.openai_api_key, provider=AgentProvider.openai,
            )
            if turn_result.usage:
                total_input += turn_result.usage.input_tokens or 0
                total_output += turn_result.usage.output_tokens or 0
            if not turn_result.tool_calls:
                result = turn_result
                break

            oa_messages.append({
                "role": "assistant",
                "content": turn_result.content or None,
                "tool_calls": [
                    {"id": tc.id, "type": "function", "function": {"name": tc.name, "arguments": json.dumps(tc.input)}}
                    for tc in turn_result.tool_calls
                ],
            })
            for tc in turn_result.tool_calls:
                evts, result_str = await _run_tool(tc, agent_id=agent_id, session_id=session_id, user_id=user_id, skill_map=skill_map, capsule_ids=capsule_ids, settings=settings)
                for ev in evts:
                    yield ev
                oa_messages.append({"role": "tool", "tool_call_id": tc.id, "content": result_str})

        if result is None:
            final = await openai_call_once(
                model=model_name, messages=oa_messages, tools=[],
                api_key=settings.openai_api_key, provider=AgentProvider.openai,
            )
            result = final
            if final.usage:
                total_input += final.usage.input_tokens or 0
                total_output += final.usage.output_tokens or 0

        usage_dict = {"input_tokens": total_input, "output_tokens": total_output}
        result.content = scrub_output(result.content)
        result.pii_redacted = pii_redacted
        yield _te("llm_end", {"model": model_name, "usage": usage_dict, "structured_output": result.structured_output})

    elif agent.provider == AgentProvider.google:
        from google.genai import types as gtypes
        from agents.services.anthropic_agent import GET_SKILL_CONTENT_TOOL
        from agents.services.google_agent import MAX_TOOL_TURNS as G_MAX_TURNS, anthropic_to_gemini_tool, call_once as google_call_once
        from capsules.tools import CREATE_CAPSULE_TOOL

        system = append_capsule_tool_rules(system)
        skill_map = {s["_id"]: s for s in skill_docs}
        model_name = agent.model or "gemini-2.0-flash"

        gemini_tool_defs = [CREATE_CAPSULE_TOOL]
        if use_skill_tools:
            gemini_tool_defs.append(GET_SKILL_CONTENT_TOOL)
        gemini_tools = [anthropic_to_gemini_tool(gemini_tool_defs)]

        g_contents: list[gtypes.Content] = []
        for m in history:
            role = "model" if m.role == "assistant" else "user"
            g_contents.append(gtypes.Content(role=role, parts=[gtypes.Part.from_text(text=m.content)]))
        g_contents.append(gtypes.Content(role="user", parts=[gtypes.Part.from_text(text=clean_message)]))

        total_input = 0
        total_output = 0

        yield _te("llm_start", {
            "model": model_name, "provider": agent.provider.value,
            "history_turns": len(history), "has_rag_context": agent.rag_config is not None,
            "has_response_schema": agent.response_schema is not None,
            "mode": "skill_tools" if use_skill_tools else "capsule_tools",
        })

        for _turn in range(G_MAX_TURNS + 1):
            turn_result = await google_call_once(
                model=model_name, contents=g_contents, system=system, tools=gemini_tools, settings=settings,
            )
            if turn_result.usage:
                total_input += turn_result.usage.input_tokens or 0
                total_output += turn_result.usage.output_tokens or 0
            if not turn_result.tool_calls:
                result = turn_result
                break

            model_parts: list[gtypes.Part] = []
            if turn_result.content:
                model_parts.append(gtypes.Part.from_text(turn_result.content))
            for tc in turn_result.tool_calls:
                model_parts.append(gtypes.Part(function_call=gtypes.FunctionCall(name=tc.name, args=tc.input)))
            g_contents.append(gtypes.Content(role="model", parts=model_parts))

            func_response_parts: list[gtypes.Part] = []
            for tc in turn_result.tool_calls:
                evts, result_str = await _run_tool(tc, agent_id=agent_id, session_id=session_id, user_id=user_id, skill_map=skill_map, capsule_ids=capsule_ids, settings=settings)
                for ev in evts:
                    yield ev
                func_response_parts.append(
                    gtypes.Part.from_function_response(name=tc.name, response={"result": result_str})
                )
            g_contents.append(gtypes.Content(role="user", parts=func_response_parts))

        if result is None:
            final = await google_call_once(
                model=model_name, contents=g_contents, system=system, tools=[], settings=settings,
            )
            result = final
            if final.usage:
                total_input += final.usage.input_tokens or 0
                total_output += final.usage.output_tokens or 0

        usage_dict = {"input_tokens": total_input, "output_tokens": total_output}
        result.content = scrub_output(result.content)
        result.pii_redacted = pii_redacted
        yield _te("llm_end", {"model": model_name, "usage": usage_dict, "structured_output": result.structured_output})

    else:
        # Perplexity and any future providers without native tool calling
        system = append_no_file_disclaimer_rules(system)
        yield _te("llm_start", {
            "model": agent.model, "provider": agent.provider.value,
            "history_turns": len(history), "has_rag_context": agent.rag_config is not None,
            "has_response_schema": agent.response_schema is not None,
        })
        result = await handler(AgentChatRequest(
            prompt=clean_message, system=system, model=agent.model,
            provider=agent.provider, history=history, response_schema=agent.response_schema,
        ), settings)
        result.content = scrub_output(result.content)
        result.pii_redacted = pii_redacted
        if result.usage:
            usage_dict = {"input_tokens": result.usage.input_tokens, "output_tokens": result.usage.output_tokens}

        detected = await _auto_detect_capsules(
            result.content,
            user_message=clean_message,
            agent_id=agent_id,
            session_id=session_id,
            user_id=user_id,
            settings=settings,
        )
        for cap in detected:
            capsule_ids.append(cap["capsule_id"])
            yield _te("capsule_created", {
                "capsule_id": cap["capsule_id"],
                "name": cap.get("name", "Capsule"),
                "format_type": cap.get("format_type", "code"),
                "has_file": False,
            })

        yield _te("llm_end", {"model": result.model, "usage": usage_dict, "structured_output": result.structured_output})

    if result is None:
        yield {"event": "error", "detail": "Agent returned no result", "ts": _ts()}
        return

    if use_memory:
        await asyncio.to_thread(session_memory.add_turn, session_id, clean_message, result.content)

    # Compute cost and persist to trace + user balance
    cost_usd = 0.0
    if usage_dict:
        from credits.rates import compute_cost
        cost_usd = compute_cost(
            agent.model,
            usage_dict.get("input_tokens", 0),
            usage_dict.get("output_tokens", 0),
        )

    await asyncio.to_thread(
        trace_store.complete, trace_id, result.content, usage_dict,
        user_id=user_id, model=agent.model,
        provider=agent.provider.value, cost_usd=cost_usd,
    )

    if user_id and cost_usd > 0:
        from users.store import UserStore
        await asyncio.to_thread(UserStore().increment_credits_used, user_id, cost_usd)

    yield {
        "event": "response",
        "content": result.content,
        "structured_output": result.structured_output,
        "usage": usage_dict,
        "pii_redacted": getattr(result, "pii_redacted", []),
        "trace_id": trace_id,
        "capsule_ids": capsule_ids,
        "ts": _ts(),
    }
    yield {"event": "done", "trace_id": trace_id, "ts": _ts()}

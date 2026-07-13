import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents.schemas import AgentCreate, AgentUpdate, AgentResponse
from agents.services.runner import stream_agent_chat
from agents.services.agent_store import AgentStore, SessionMemory
from auth.dependencies import get_current_user, get_optional_user
from services.pagination import PageParams, PagedResponse, get_page_params, paginate
from shares.store import ShareStore
from settings import Settings, get_settings


class AgentMessageRequest(BaseModel):
    agent_id: str
    message: str
    session_id: str | None = None
    extra_prompt: dict[str, str] = {}


class AgentMessageResponse(BaseModel):
    content: str
    structured_output: dict | None = None
    usage: dict | None = None
    trace_id: str
    pii_redacted: list[str] = []


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agents", tags=["agents"])


def get_agent_store() -> AgentStore:
    return AgentStore()


def _resolve_access(agent_id: str, user_id: str) -> str:
    """Return 'owner', 'write', 'read', or 'none'."""
    found, owner_id = AgentStore().get_owner_id(agent_id)
    if not found:
        return "none"
    if owner_id is None or owner_id == user_id:
        return "owner"
    return ShareStore().get_user_access("agent", agent_id, user_id) or "none"


def _require_write(agent_id: str, user_id: str) -> None:
    access = _resolve_access(agent_id, user_id)
    if access == "none":
        raise HTTPException(status_code=404, detail="Agent not found")
    if access == "read":
        raise HTTPException(status_code=403, detail="You have read-only access to this agent")


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def create_agent(
    body: AgentCreate,
    store: AgentStore = Depends(get_agent_store),
    user: dict | None = Depends(get_optional_user),
) -> AgentResponse:
    owner_id = user["id"] if user else None
    return await asyncio.to_thread(
        store.create,
        name=body.name,
        role=body.role,
        goal=body.goal,
        instructions=body.instructions,
        model=body.model,
        provider=body.provider,
        memory_enabled=body.memory_enabled,
        memory_max_messages=body.memory_max_messages,
        rag_config=body.rag_config,
        managed_agents=body.managed_agents or [],
        response_schema=body.response_schema,
        skill_ids=body.skill_ids or [],
        owner_id=owner_id,
    )


@router.get("/", response_model=PagedResponse)
async def list_agents(
    q: str | None = Query(None, description="Filter by name or role"),
    paging: PageParams = Depends(get_page_params),
    store: AgentStore = Depends(get_agent_store),
    user: dict | None = Depends(get_optional_user),
) -> PagedResponse:
    user_id = user["id"] if user else None
    items = await asyncio.to_thread(store.list_for_user, user_id, q=q) if user_id else []
    return paginate(items, paging)


@router.get("/agent-config/{agent_id}", response_model=AgentResponse)
async def get_agent_config(
    agent_id: str,
    store: AgentStore = Depends(get_agent_store),
) -> AgentResponse:
    agent = await asyncio.to_thread(store.get, agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.patch("/{agent_id}", response_model=AgentResponse)
async def update_agent(
    agent_id: str,
    body: AgentUpdate,
    store: AgentStore = Depends(get_agent_store),
    user: dict | None = Depends(get_optional_user),
) -> AgentResponse:
    if user:
        await asyncio.to_thread(_require_write, agent_id, user["id"])

    existing = await asyncio.to_thread(store.get, agent_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    patch = body.model_dump(exclude_unset=True)
    if "provider" in patch and patch["provider"] is not None:
        patch["provider"] = patch["provider"].value
    if not patch or all(v is None for v in patch.values()):
        raise HTTPException(status_code=400, detail="Provide at least one field to update")

    if patch.get("memory_enabled") is False:
        patch["memory_max_messages"] = None

    eff_enabled = patch.get("memory_enabled", existing.memory_enabled)
    eff_max = patch.get("memory_max_messages", existing.memory_max_messages)
    if eff_enabled and eff_max is None:
        raise HTTPException(status_code=400, detail="When memory is enabled, set memory_max_messages (1–500).")

    updated = await asyncio.to_thread(store.update, agent_id, patch)
    if updated is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return updated


@router.post("/message", response_model=AgentMessageResponse)
async def agent_chat(
    body: AgentMessageRequest,
    settings: Settings = Depends(get_settings),
    user: dict | None = Depends(get_optional_user),
) -> AgentMessageResponse:
    user_id = user["id"] if user else None
    response_event = None
    error_event = None

    async for event in stream_agent_chat(
        agent_id=body.agent_id,
        session_id=body.session_id,
        message=body.message,
        extra_prompt=body.extra_prompt,
        settings=settings,
        user_id=user_id,
    ):
        if event["event"] == "response":
            response_event = event
        elif event["event"] == "error":
            error_event = event

    if error_event:
        raise HTTPException(status_code=400, detail=error_event["detail"])
    if not response_event:
        raise HTTPException(status_code=500, detail="Agent returned no response")

    return AgentMessageResponse(
        content=response_event["content"],
        structured_output=response_event.get("structured_output"),
        usage=response_event.get("usage"),
        trace_id=response_event["trace_id"],
        pii_redacted=response_event.get("pii_redacted", []),
    )


@router.post("/message/stream")
async def agent_chat_stream(
    body: AgentMessageRequest,
    settings: Settings = Depends(get_settings),
    user: dict | None = Depends(get_optional_user),
) -> StreamingResponse:
    user_id = user["id"] if user else None

    async def sse():
        async for event in stream_agent_chat(
            agent_id=body.agent_id,
            session_id=body.session_id,
            message=body.message,
            extra_prompt=body.extra_prompt,
            settings=settings,
            user_id=user_id,
        ):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(sse(), media_type="text/event-stream")


@router.get("/{agent_id}/my-access")
async def my_access(
    agent_id: str,
    user: dict = Depends(get_current_user),
):
    access = await asyncio.to_thread(_resolve_access, agent_id, user["id"])
    return {"access": access}


@router.post("/{agent_id}/clone", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
async def clone_agent(
    agent_id: str,
    store: AgentStore = Depends(get_agent_store),
    user: dict | None = Depends(get_optional_user),
) -> AgentResponse:
    owner_id = user["id"] if user else None
    result = await asyncio.to_thread(store.clone, agent_id, owner_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return result


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(
    agent_id: str,
    store: AgentStore = Depends(get_agent_store),
    user: dict | None = Depends(get_optional_user),
) -> Response:
    if user:
        await asyncio.to_thread(_require_write, agent_id, user["id"])
    ok = await asyncio.to_thread(store.delete, agent_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Agent not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{agent_id}/traces")
async def list_traces(agent_id: str):
    from agents.services.agent_store import TraceStore
    return await asyncio.to_thread(TraceStore().list_for_agent, agent_id)


@router.get("/{agent_id}/traces/{trace_id}")
async def get_trace(agent_id: str, trace_id: str):
    from agents.services.agent_store import TraceStore
    trace = await asyncio.to_thread(TraceStore().get, trace_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace

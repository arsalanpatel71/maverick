"""Shared chat.completions flow for OpenAI and OpenAI-compatible APIs (e.g. Perplexity)."""

import json
import logging

from openai import AsyncOpenAI

from agents.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    AgentProvider,
    AgentUsage,
    ToolCallRequest,
)
from services.structured import SchemaBuilder, StructuredParser

logger = logging.getLogger(__name__)

MAX_TOOL_TURNS = 5


def anthropic_to_openai_tool(tool: dict) -> dict:
    return {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["input_schema"],
        },
    }


async def call_once(
    *,
    model: str,
    messages: list[dict],
    tools: list[dict],
    api_key: str,
    base_url: str | None = None,
    provider: AgentProvider = AgentProvider.openai,
) -> AgentChatResponse:
    """Single OpenAI-compatible call that may return tool_calls."""
    client_kwargs: dict = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = AsyncOpenAI(**client_kwargs)

    create_kwargs: dict = {"model": model, "messages": messages}
    if tools:
        create_kwargs["tools"] = tools
        create_kwargs["tool_choice"] = "auto"

    try:
        resp = await client.chat.completions.create(**create_kwargs)
    except Exception:
        logger.exception("%s call_once failed", provider.value)
        raise

    choice = resp.choices[0]
    content = (choice.message.content or "").strip()

    tool_calls: list[ToolCallRequest] = []
    if choice.message.tool_calls:
        for tc in choice.message.tool_calls:
            tool_calls.append(ToolCallRequest(
                id=tc.id,
                name=tc.function.name,
                input=json.loads(tc.function.arguments),
            ))

    usage: AgentUsage | None = None
    u = getattr(resp, "usage", None)
    if u is not None:
        usage = AgentUsage(
            input_tokens=getattr(u, "prompt_tokens", None),
            output_tokens=getattr(u, "completion_tokens", None),
        )

    return AgentChatResponse(
        content=content,
        provider=provider,
        model=model,
        usage=usage,
        tool_calls=tool_calls,
    )


async def run_openai_compatible_chat(
    *,
    api_key: str,
    base_url: str | None,
    request: AgentChatRequest,
    default_model: str,
    provider: AgentProvider,
    native_json_schema: bool = True,
) -> AgentChatResponse:
    model_name = request.model or default_model
    client_kwargs: dict = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url

    client = AsyncOpenAI(**client_kwargs)

    system_text = request.system or ""
    if request.response_schema and not native_json_schema:
        system_text += SchemaBuilder.to_instruction_block(
            request.response_schema.name, request.response_schema.json_schema
        )

    messages: list[dict[str, str]] = []
    if system_text:
        messages.append({"role": "system", "content": system_text})
    for msg in request.history:
        messages.append({"role": msg.role, "content": msg.content})
    messages.append({"role": "user", "content": request.prompt})

    create_kwargs: dict = {"model": model_name, "messages": messages}
    if request.response_schema and native_json_schema:
        create_kwargs["response_format"] = SchemaBuilder.to_openai_format(
            request.response_schema.name, request.response_schema.json_schema
        )

    try:
        resp = await client.chat.completions.create(**create_kwargs)
    except Exception:
        logger.exception("%s chat completion failed", provider.value)
        raise

    choice = resp.choices[0]
    content = (choice.message.content or "").strip()
    if not content:
        raise RuntimeError("Model returned empty content")

    usage: AgentUsage | None = None
    u = getattr(resp, "usage", None)
    if u is not None:
        usage = AgentUsage(
            input_tokens=getattr(u, "prompt_tokens", None),
            output_tokens=getattr(u, "completion_tokens", None),
        )

    structured_output: dict | None = None
    if request.response_schema:
        try:
            structured_output = StructuredParser.parse(content)
            content = json.dumps(structured_output)
        except ValueError:
            logger.warning("Failed to parse structured output for %s", provider.value)

    return AgentChatResponse(
        content=content,
        provider=provider,
        model=model_name,
        usage=usage,
        structured_output=structured_output,
    )

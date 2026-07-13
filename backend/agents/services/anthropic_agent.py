import json
import logging

import anthropic

from agents.schemas import (
    AgentChatRequest,
    AgentChatResponse,
    AgentProvider,
    AgentUsage,
    ToolCallRequest,
)
from services.structured import SchemaBuilder, StructuredParser
from settings import Settings

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-6"

# Maximum agentic loop turns (tool use rounds) before forcing a final answer
MAX_TOOL_TURNS = 5

# The get_skill_content tool definition in Anthropic format
GET_SKILL_CONTENT_TOOL: dict = {
    "name": "get_skill_content",
    "description": (
        "Fetch the full instructions of a skill so you know exactly how to apply it. "
        "Call this when you decide a skill listed in 'Available Skills' is relevant to the user's request."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "skill_id": {
                "type": "string",
                "description": "The ID of the skill to fetch (shown in the Available Skills catalog).",
            },
        },
        "required": ["skill_id"],
    },
}


async def call_once(
    *,
    model: str,
    messages: list[dict],
    system: str,
    tools: list[dict],
    settings: Settings,
) -> AgentChatResponse:
    """Single Anthropic API call — may return tool_calls if stop_reason is tool_use."""
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    kwargs: dict = {
        "model": model,
        "max_tokens": 8096,
        "messages": messages,
    }
    if system:
        kwargs["system"] = system
    if tools:
        kwargs["tools"] = tools

    response = await client.messages.create(**kwargs)

    text = ""
    tool_calls: list[ToolCallRequest] = []
    for block in response.content:
        if block.type == "text":
            text = block.text
        elif block.type == "tool_use":
            tool_calls.append(ToolCallRequest(id=block.id, name=block.name, input=dict(block.input)))

    usage: AgentUsage | None = None
    if response.usage is not None:
        usage = AgentUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    return AgentChatResponse(
        content=text,
        provider=AgentProvider.anthropic,
        model=model,
        usage=usage,
        tool_calls=tool_calls,
    )


async def chat(request: AgentChatRequest, settings: Settings) -> AgentChatResponse:
    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    model_name = request.model or DEFAULT_MODEL
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    # Build message list from history then append current user message
    messages: list[dict] = [
        {"role": msg.role, "content": msg.content} for msg in request.history
    ]
    messages.append({"role": "user", "content": request.prompt})

    system_text = request.system or ""
    if request.response_schema:
        system_text += SchemaBuilder.to_instruction_block(
            request.response_schema.name, request.response_schema.json_schema
        )

    kwargs: dict = {
        "model": model_name,
        "max_tokens": 8096,
        "messages": messages,
    }
    if system_text:
        kwargs["system"] = system_text

    try:
        response = await client.messages.create(**kwargs)
    except Exception:
        logger.exception("Anthropic Claude request failed")
        raise

    if not response.content:
        raise RuntimeError("Model returned no content")

    content = response.content[0].text

    usage: AgentUsage | None = None
    if response.usage is not None:
        usage = AgentUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )

    structured_output: dict | None = None
    if request.response_schema:
        try:
            structured_output = StructuredParser.parse(content)
            content = json.dumps(structured_output)
        except ValueError:
            logger.warning("Failed to parse structured output for Anthropic Claude")

    return AgentChatResponse(
        content=content,
        provider=AgentProvider.anthropic,
        model=model_name,
        usage=usage,
        structured_output=structured_output,
    )

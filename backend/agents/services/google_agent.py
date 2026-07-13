import json
import logging
from uuid import uuid4

from google import genai
from google.genai import types

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

DEFAULT_MODEL = "gemini-2.0-flash"
MAX_TOOL_TURNS = 5


def anthropic_to_gemini_tool(tools: list[dict]) -> types.Tool:
    declarations = [
        types.FunctionDeclaration(
            name=t["name"],
            description=t["description"],
            parameters=t["input_schema"],
        )
        for t in tools
    ]
    return types.Tool(function_declarations=declarations)


async def call_once(
    *,
    model: str,
    contents: list[types.Content],
    system: str,
    tools: list[types.Tool],
    settings: Settings,
) -> AgentChatResponse:
    """Single Gemini call — may return function calls in tool_calls."""
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is not set")

    model_name = model or DEFAULT_MODEL
    client = genai.Client(api_key=settings.google_api_key)

    config_kwargs: dict = {}
    if system:
        config_kwargs["system_instruction"] = system
    if tools:
        config_kwargs["tools"] = tools

    kwargs: dict = {"model": model_name, "contents": contents}
    if config_kwargs:
        kwargs["config"] = types.GenerateContentConfig(**config_kwargs)

    try:
        response = await client.aio.models.generate_content(**kwargs)
    except Exception:
        logger.exception("Google Gemini call_once failed")
        raise

    if not response.candidates:
        raise RuntimeError("Model returned no candidates")

    content = ""
    tool_calls: list[ToolCallRequest] = []
    for part in (response.candidates[0].content.parts or []):
        if hasattr(part, "text") and part.text:
            content += part.text
        if hasattr(part, "function_call") and part.function_call:
            fc = part.function_call
            tool_calls.append(ToolCallRequest(
                id=str(uuid4()),
                name=fc.name,
                input=dict(fc.args),
            ))

    usage: AgentUsage | None = None
    meta = response.usage_metadata
    if meta is not None:
        usage = AgentUsage(
            input_tokens=meta.prompt_token_count,
            output_tokens=meta.candidates_token_count,
        )

    return AgentChatResponse(
        content=content,
        provider=AgentProvider.google,
        model=model_name,
        usage=usage,
        tool_calls=tool_calls,
    )


async def chat(request: AgentChatRequest, settings: Settings) -> AgentChatResponse:
    if not settings.google_api_key:
        raise ValueError("GOOGLE_API_KEY is not set")

    model_name = request.model or DEFAULT_MODEL
    client = genai.Client(api_key=settings.google_api_key)

    contents: list[types.Content] = []
    for msg in request.history:
        role = "model" if msg.role == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=request.prompt)]))

    config_kwargs: dict = {}
    if request.system:
        config_kwargs["system_instruction"] = request.system
    if request.response_schema:
        config_kwargs["response_mime_type"] = "application/json"
        config_kwargs["response_schema"] = SchemaBuilder.to_google_format(request.response_schema.json_schema)

    kwargs: dict = {"model": model_name, "contents": contents}
    if config_kwargs:
        kwargs["config"] = types.GenerateContentConfig(**config_kwargs)

    try:
        response = await client.aio.models.generate_content(**kwargs)
    except Exception:
        logger.exception("Google Gemini request failed")
        raise

    if not response.candidates:
        raise RuntimeError("Model returned no candidates (blocked or empty)")

    content = response.text
    usage: AgentUsage | None = None
    meta = response.usage_metadata
    if meta is not None:
        usage = AgentUsage(
            input_tokens=meta.prompt_token_count,
            output_tokens=meta.candidates_token_count,
        )

    structured_output: dict | None = None
    if request.response_schema:
        try:
            structured_output = StructuredParser.parse(content)
            content = json.dumps(structured_output)
        except ValueError:
            logger.warning("Failed to parse structured output for Google Gemini")

    return AgentChatResponse(
        content=content,
        provider=AgentProvider.google,
        model=model_name,
        usage=usage,
        structured_output=structured_output,
    )

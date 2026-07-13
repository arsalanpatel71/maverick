from agents.schemas import AgentChatRequest, AgentChatResponse, AgentProvider
from agents.services.openai_compat import run_openai_compatible_chat
from settings import Settings

DEFAULT_MODEL = "gpt-4o-mini"


async def chat(request: AgentChatRequest, settings: Settings) -> AgentChatResponse:
    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY is not set")
    return await run_openai_compatible_chat(
        api_key=settings.openai_api_key,
        base_url=None,
        request=request,
        default_model=DEFAULT_MODEL,
        provider=AgentProvider.openai,
    )

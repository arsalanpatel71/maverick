from agents.schemas import AgentChatRequest, AgentChatResponse, AgentProvider
from agents.services.openai_compat import run_openai_compatible_chat
from settings import Settings

# Perplexity Sonar API is OpenAI-compatible; see https://docs.perplexity.ai/guides/chat-completions-guide
PERPLEXITY_API_BASE = "https://api.perplexity.ai"
DEFAULT_MODEL = "sonar"


async def chat(request: AgentChatRequest, settings: Settings) -> AgentChatResponse:
    if not settings.perplexity_api_key:
        raise ValueError("PERPLEXITY_API_KEY is not set")
    return await run_openai_compatible_chat(
        api_key=settings.perplexity_api_key,
        base_url=PERPLEXITY_API_BASE,
        request=request,
        default_model=DEFAULT_MODEL,
        provider=AgentProvider.perplexity,
        native_json_schema=False,
    )

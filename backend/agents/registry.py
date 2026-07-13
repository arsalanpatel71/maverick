from collections.abc import Awaitable, Callable

from agents.services.anthropic_agent import chat as anthropic_chat
from agents.services.google_agent import chat as google_chat
from agents.services.openai_agent import chat as openai_chat
from agents.services.perplexity_agent import chat as perplexity_chat
from agents.schemas import AgentChatRequest, AgentChatResponse, AgentProvider
from settings import Settings

Handler = Callable[[AgentChatRequest, Settings], Awaitable[AgentChatResponse]]

PROVIDERS: dict[AgentProvider, Handler] = {
    AgentProvider.anthropic: anthropic_chat,
    AgentProvider.google: google_chat,
    AgentProvider.openai: openai_chat,
    AgentProvider.perplexity: perplexity_chat,
}

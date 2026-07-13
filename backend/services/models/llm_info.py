from pydantic import BaseModel, Field

from agents.schemas import AgentProvider


class LLMModelEntry(BaseModel):
    id: str = Field(description="Model ID to use in agent `model` field when this provider is selected.")
    description: str | None = Field(
        default=None,
        description="Short human-readable note; verify against provider docs for current availability.",
    )


class LLMProviderModels(BaseModel):
    provider: AgentProvider
    models: list[LLMModelEntry]

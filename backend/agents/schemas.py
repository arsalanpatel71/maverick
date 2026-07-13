from datetime import datetime
from enum import Enum
from typing import Literal, Self

from pydantic import BaseModel, Field, model_validator


class AgentProvider(str, Enum):
    google = "google"
    openai = "openai"
    anthropic = "anthropic"
    perplexity = "perplexity"


class ManagedAgent(BaseModel):
    id: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    usage_description: str = Field(..., min_length=1, description="Tells the manager LLM when and why to call this agent.")


class ResponseSchema(BaseModel):
    name: str = Field(..., min_length=1, description="Schema name used in response_format calls.")
    json_schema: dict = Field(..., description="JSON Schema object defining the expected output structure.")
    description: str | None = Field(default=None, description="Optional human-readable description of what this schema captures.")


class RAGConfig(BaseModel):
    rag_ids: list[str] = Field(
        ...,
        min_length=1,
        description="RAG IDs to query on every agent message. Supports multiple RAGs — results are merged and re-ranked by score.",
    )
    top_k: int = Field(default=10, ge=1, le=100, description="Max chunks to retrieve per RAG.")
    retrieval_type: Literal["basic", "mmr", "hyde", "time_aware"] = Field(
        default="basic",
        description="Retrieval strategy: basic (cosine), mmr (diversity), hyde (hypothetical doc), time_aware (recency).",
    )
    lambda_param: float = Field(default=0.6, ge=0.0, le=1.0, description="MMR trade-off (1.0 = pure relevance).")
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0, description="Drop chunks below this score.")
    time_decay_factor: float = Field(default=0.7, ge=0.0, le=1.0, description="Recency weight for time_aware.")


class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1)
    role: str = Field(..., min_length=1)
    goal: str = Field(..., min_length=1)
    instructions: str = Field(..., min_length=1)
    model: str = Field(..., min_length=1)
    provider: AgentProvider = AgentProvider.google
    memory_enabled: bool = False
    memory_max_messages: int | None = Field(
        default=None,
        ge=1,
        le=500,
        description="Rolling window of prior user+assistant turns to include when memory is on (max 500).",
    )
    rag_config: RAGConfig | None = Field(
        default=None,
        description="Optional RAG configuration. When set, relevant chunks are retrieved and injected into the system prompt on every message.",
    )
    managed_agents: list[ManagedAgent] = Field(
        default_factory=list,
        description="Child agents this agent can delegate to. A non-empty list makes this agent a manager.",
    )
    response_schema: ResponseSchema | None = Field(
        default=None,
        description="Optional JSON Schema the agent must conform to when responding.",
    )
    skill_ids: list[str] = Field(
        default_factory=list,
        description="IDs of skills to inject into this agent's system prompt on every call.",
    )

    @model_validator(mode="after")
    def memory_window_when_enabled(self) -> Self:
        if self.memory_enabled and self.memory_max_messages is None:
            raise ValueError(
                "memory_max_messages is required when memory_enabled is true (use 1–500, e.g. 20–50)"
            )
        return self


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    role: str | None = Field(default=None, min_length=1)
    goal: str | None = Field(default=None, min_length=1)
    instructions: str | None = Field(default=None, min_length=1)
    model: str | None = Field(default=None, min_length=1)
    provider: AgentProvider | None = None
    memory_enabled: bool | None = None
    memory_max_messages: int | None = Field(
        default=None,
        ge=1,
        le=500,
    )
    rag_config: RAGConfig | None = Field(
        default=None,
        description="Set to update RAG config. Pass null to remove RAG from this agent.",
    )
    managed_agents: list[ManagedAgent] | None = Field(
        default=None,
        description="Replace the full managed_agents list. Pass empty list to remove all.",
    )
    response_schema: ResponseSchema | None = Field(
        default=None,
        description="Set to update the response schema. Pass null to remove it.",
    )
    skill_ids: list[str] | None = Field(
        default=None,
        description="Replace the full skill_ids list. Pass empty list to remove all skills.",
    )


class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    goal: str
    instructions: str
    model: str
    provider: AgentProvider
    memory_enabled: bool = False
    memory_max_messages: int | None = None
    rag_config: RAGConfig | None = None
    managed_agents: list[ManagedAgent] = Field(default_factory=list)
    response_schema: ResponseSchema | None = None
    skill_ids: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class ChatWithAgentRequest(BaseModel):
    agent_id: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    session_id: str | None = Field(
        default=None,
        description=(
            "Conversation session identifier. Required to use memory — the agent will recall "
            "prior turns from this session up to memory_max_messages. "
            "Generate a UUID per user/conversation and reuse it across turns."
        ),
    )
    extra_prompt: dict[str, str] = Field(
        default_factory=dict,
        description="Per-request key/value context (e.g. user_data) appended to the system prompt.",
    )


class ConversationMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AgentChatRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    system: str | None = None
    model: str | None = None
    provider: AgentProvider = AgentProvider.google
    history: list[ConversationMessage] = Field(
        default_factory=list,
        description="Prior conversation turns (oldest first). Empty when memory is off or no prior turns exist.",
    )
    response_schema: ResponseSchema | None = Field(
        default=None,
        description="When set, the LLM is instructed to return JSON conforming to this schema.",
    )


class AgentUsage(BaseModel):
    input_tokens: int | None = None
    output_tokens: int | None = None


class ToolCallRequest(BaseModel):
    """A tool call the model wants to make."""
    id: str
    name: str
    input: dict


class AgentChatResponse(BaseModel):
    content: str
    provider: AgentProvider
    model: str
    usage: AgentUsage | None = None
    pii_redacted: list[str] = Field(
        default_factory=list,
        description="Sensitive data types redacted from the prompt before it reached the model (e.g. 'ssn', 'credit_card').",
    )
    structured_output: dict | None = Field(
        default=None,
        description="Parsed structured JSON when a response_schema was set on the agent.",
    )
    tool_calls: list[ToolCallRequest] = Field(
        default_factory=list,
        description="Tool calls the model wants to make (non-empty when stop_reason is tool_use).",
    )

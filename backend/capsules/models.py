from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field

CapsuleFormat = Literal[
    "text", "code", "json", "markdown", "data", "image",
    "csv", "xlsx", "pdf", "docx", "pptx",
]

INLINE_FORMATS: frozenset[str] = frozenset({"text", "code", "json", "markdown", "data", "image"})
FILE_FORMATS: frozenset[str] = frozenset({"csv", "xlsx", "pdf", "docx", "pptx"})


class CapsuleRecord(BaseModel):
    capsule_id: str
    agent_id: str
    session_id: str | None = None
    user_id: str | None = None
    format_type: str
    name: str
    description: str
    data: Any = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: datetime

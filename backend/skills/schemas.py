from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1, description="Full SKILL.md markdown content")
    github_url: str | None = None


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, min_length=1)
    content: str | None = Field(default=None, min_length=1)


class SkillResponse(BaseModel):
    id: str
    name: str
    description: str
    content: str
    source: Literal["builtin", "github", "custom"]
    github_url: str | None
    owner_id: str | None
    created_at: datetime
    updated_at: datetime


class GithubFetchRequest(BaseModel):
    url: str = Field(..., description="GitHub URL to a SKILL.md file (blob or raw URL)")

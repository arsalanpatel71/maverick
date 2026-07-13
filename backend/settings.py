from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: str = Field(default="development")

    super_admin_email: str = Field(default="")
    super_admin_password: str = Field(default="")

    google_api_key: str = Field(default="")
    openai_api_key: str = Field(default="")
    anthropic_api_key: str = Field(default="")
    perplexity_api_key: str = Field(default="")

    mongo_uri: str = Field(default="")
    mongo_database: str = Field(default="sales")

    qdrant_url: str = Field(default="http://localhost:6333")
    qdrant_api_key: str = Field(default="")

    app_aws_access_key_id: str = Field(default="")
    app_aws_secret_access_key: str = Field(default="")
    app_aws_region: str = Field(default="us-east-1")
    aws_storage_bucket_name: str = Field(default="")


@lru_cache
def get_settings() -> Settings:
    return Settings()


# Embedding configuration — not part of Settings because they require code changes to switch
EMBEDDING_PROVIDER: Literal["openai", "gemini"] = "gemini"
OPENAI_EMBEDDING_BACKEND: Literal["sdk", "langchain"] = "langchain"
DEFAULT_EMBEDDING_MODELS: dict[str, str] = {
    "openai": "text-embedding-3-small",
    "gemini": "gemini-embedding-001",
}
DEFAULT_EMBEDDING_MODEL: str = DEFAULT_EMBEDDING_MODELS[EMBEDDING_PROVIDER]

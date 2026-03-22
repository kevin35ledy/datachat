from __future__ import annotations
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=("../.env", ".env"), extra="ignore")

    # App
    app_name: str = "DB-IA"
    debug: bool = False
    show_sql_errors: bool = True  # Set False in production

    # LLM
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    litellm_default_model: str = "claude-sonnet-4-6"
    litellm_summary_model: str = "claude-haiku-4-5-20251001"
    ollama_api_base: str = "http://localhost:11434"

    # Vector store (Qdrant)
    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    schema_rag_min_tables: int = 20  # Skip RAG below this threshold

    # App database
    database_url: str = "sqlite+aiosqlite:///./dbia.db"

    # Security
    secret_key: str = "dev-secret-key-change-in-production"
    jwt_secret: str = "dev-jwt-secret-change-in-production"
    jwt_expiry_minutes: int = 480

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Query limits
    max_query_rows: int = 1000
    query_timeout_seconds: int = 30
    max_audit_tables: int = 500

    # Rate limiting
    rate_limit_enabled: bool = False
    rate_limit_per_minute: int = 60


@lru_cache
def get_settings() -> Settings:
    return Settings()

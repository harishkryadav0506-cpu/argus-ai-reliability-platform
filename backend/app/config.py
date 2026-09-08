"""
ARGUS Configuration

Loads settings from environment variables. Every optional integration
(LLM provider, LangSmith, Redis, Vector DB) must have a sane default so the
app can boot in "local/demo mode" even when none of these are configured.
"""
from functools import lru_cache
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    ARGUS_ENV: str = "development"
    APP_NAME: str = "ARGUS"
    LOG_LEVEL: str = "INFO"

    # --- LLM (optional — app runs in fallback/rule-based mode without it) ---
    LLM_PROVIDER: Optional[str] = None          # "anthropic" | "openai" | "groq" | "gemini" | None
    LLM_MODEL: Optional[str] = None             # e.g. "llama-3.3-70b-versatile" for groq, "gemini-2.0-flash" for gemini
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None

    # --- LangSmith (optional — tracing disabled gracefully without it) ---
    LANGSMITH_API_KEY: Optional[str] = None
    LANGSMITH_PROJECT: str = "ARGUS-dev"
    LANGSMITH_TRACING_V2: bool = False

    # --- Database (required for full functionality, but app should not crash without it) ---
    DATABASE_URL: str = "postgresql://argus:argus@localhost:5432/argus"

    # --- Redis (optional — app falls back to in-memory state without it) ---
    REDIS_URL: Optional[str] = None

    # --- Vector DB (optional — RAG disabled gracefully without it) ---
    VECTOR_DB_PATH: str = "./data/vector_store"

    @property
    def llm_configured(self) -> bool:
        return bool(
            self.LLM_PROVIDER
            and (self.OPENAI_API_KEY or self.ANTHROPIC_API_KEY or self.GROQ_API_KEY or self.GOOGLE_API_KEY)
        )

    @property
    def langsmith_configured(self) -> bool:
        return bool(self.LANGSMITH_API_KEY) and self.LANGSMITH_TRACING_V2

    @property
    def redis_configured(self) -> bool:
        return bool(self.REDIS_URL)


@lru_cache
def get_settings() -> Settings:
    return Settings()

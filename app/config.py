"""Application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    llm_provider: str = Field(default="mock", alias="LLM_PROVIDER")
    llm_model_junior: str = Field(default="low_cost", alias="LLM_MODEL_JUNIOR")
    llm_model_deputy: str = Field(default="mid", alias="LLM_MODEL_DEPUTY")
    llm_model_subleader: str = Field(default="high", alias="LLM_MODEL_SUBLEADER")
    llm_model_router: str = Field(default="low_cost", alias="LLM_MODEL_ROUTER")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    anthropic_api_key: str | None = Field(default=None, alias="ANTHROPIC_API_KEY")
    gemini_api_key: str | None = Field(default=None, alias="GEMINI_API_KEY")

    # Storage
    database_url: str = Field(default="sqlite:///./team_mate.db", alias="DATABASE_URL")

    # Workflow defaults
    default_cost_mode: str = Field(default="balanced", alias="DEFAULT_COST_MODE")
    default_verification_level: str = Field(default="standard", alias="DEFAULT_VERIFICATION_LEVEL")
    default_max_retry: int = Field(default=1, alias="DEFAULT_MAX_RETRY")
    default_budget_cap: float = Field(default=1500.0, alias="DEFAULT_BUDGET_CAP")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()

from typing import Self

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from creative.core.schemas import CandidateCount


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", env_file=".env", extra="ignore")

    ai_model: str = "gateway/openai-responses:gpt-6-luna"
    planner_model: str | None = None
    generator_model: str | None = None
    writer_model: str | None = None
    pydantic_ai_gateway_api_key: str | None = Field(default=None, repr=False)
    pydantic_ai_gateway_base_url: str | None = None
    logfire_enabled: bool = True
    logfire_token: str | None = Field(default=None, repr=False)
    logfire_include_content: bool = False
    ai_base_url: str | None = None
    ai_api_key: str | None = Field(default=None, repr=False)
    api_token: str | None = Field(default=None, repr=False, min_length=16)
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    allowed_hosts: list[str] = ["localhost", "127.0.0.1", "[::1]"]
    allowed_origins: list[str] = []
    candidate_count: CandidateCount = 20
    max_llm_calls: int = Field(default=8, ge=1, le=128)
    max_generations: int = Field(default=4, ge=1, le=100)
    call_timeout_seconds: float = Field(default=180, gt=0)
    generation_timeout_seconds: float = Field(default=600, gt=0)
    transient_retries: int = Field(default=2, ge=0, le=2)

    @model_validator(mode="after")
    def safe_binding(self) -> Self:
        if self.api_token is None and self.host not in {"127.0.0.1", "localhost", "::1"}:
            raise ValueError("API_TOKEN is required when binding beyond localhost")
        if "*" in self.allowed_hosts or "*" in self.allowed_origins:
            raise ValueError("Configure explicit allowed hosts and origins rather than '*'")
        if self.ai_base_url:
            models = [self.ai_model, self.planner_model, self.generator_model, self.writer_model]
            if any(m and not m.startswith("openai-chat:") for m in models):
                raise ValueError("AI_BASE_URL requires explicit openai-chat: model strings")
        return self

    def models(self) -> dict[str, str]:
        return {
            "framework": self.planner_model or self.ai_model,
            "plan": self.planner_model or self.ai_model,
            "candidates": self.generator_model or self.ai_model,
            "writer": self.writer_model or self.ai_model,
        }

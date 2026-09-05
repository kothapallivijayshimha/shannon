from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum


class ProviderType(Enum):
    ANTHROPIC = "anthropic"
    OPENAI = "openai"


@dataclass
class LLMConfig:
    """Configuration for the LLM provider, read from environment variables."""

    provider: ProviderType = ProviderType.ANTHROPIC
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-20250514"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"
    max_tokens: int = 4096
    temperature: float = 0.7
    max_tool_calls_per_run: int = 15
    tool_result_max_chars: int = 10_000
    redis_url: str = "redis://localhost:6379/0"

    @classmethod
    def from_env(cls) -> LLMConfig:
        provider_str = os.getenv("LLM_PROVIDER", "anthropic").lower()
        try:
            provider = ProviderType(provider_str)
        except ValueError:
            provider = ProviderType.ANTHROPIC

        return cls(
            provider=provider,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            openai_embedding_model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "4096")),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.7")),
            max_tool_calls_per_run=int(os.getenv("LLM_MAX_TOOL_CALLS", "15")),
            tool_result_max_chars=int(os.getenv("LLM_TOOL_RESULT_MAX_CHARS", "10000")),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        )

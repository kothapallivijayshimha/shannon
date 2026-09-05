from .base import BaseLLMClient, LLMEvent, LLMStream
from .config import LLMConfig, ProviderType
from .anthropic import AnthropicClient
from .openai import OpenAIClient


def get_llm_client(config: LLMConfig | None = None) -> BaseLLMClient:
    """Resolve the LLM client based on config (reads env vars by default)."""
    cfg = config or LLMConfig.from_env()
    if cfg.provider == ProviderType.ANTHROPIC:
        return AnthropicClient(cfg)
    if cfg.provider == ProviderType.OPENAI:
        return OpenAIClient(cfg)
    raise ValueError(f"Unsupported LLM provider: {cfg.provider}")


__all__ = [
    "BaseLLMClient", "LLMEvent", "LLMStream",
    "LLMConfig", "ProviderType",
    "AnthropicClient", "OpenAIClient",
    "get_llm_client",
]

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Protocol


@dataclass
class LLMEvent:
    """A single event produced by the LLM during generation."""

    type: str  # "text" | "tool_use" | "tool_result" | "error"
    content: Any = None
    tool_name: str | None = None
    tool_input: dict[str, Any] | None = None
    tool_use_id: str | None = None
    done: bool = False


@dataclass
class ToolDefinition:
    """A tool definition formatted for an LLM's tool-use schema."""

    name: str
    description: str
    input_schema: dict[str, Any]  # JSON Schema
    phase: str = ""


LLMStream = AsyncGenerator[LLMEvent, None]


class StreamCallback(Protocol):
    """Callback for streaming events to WebSocket clients."""

    async def __call__(self, event: LLMEvent) -> None: ...


class BaseLLMClient(ABC):
    """Abstract LLM client that supports tool-use and streaming."""

    def __init__(self, config: Any) -> None:
        self.config = config

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        on_stream: StreamCallback | None = None,
    ) -> AsyncGenerator[LLMEvent, None]:
        """Generate a response, yielding events as they arrive.

        When *tools* are provided, the LLM may respond with tool_use events.
        The caller is responsible for executing the tool and passing results
        back via *tool_results* on the next iteration.
        """
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """Generate an embedding vector for the given text."""
        ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts."""
        ...

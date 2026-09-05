from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from anthropic import AsyncAnthropic
from anthropic.types import (
    ContentBlockDeltaEvent,
    MessageStartEvent,
    MessageStopEvent,
    RawContentBlockDeltaEvent,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
)

from .base import BaseLLMClient, LLMEvent, LLMStream, StreamCallback, ToolDefinition


def _to_anthropic_tool(td: ToolDefinition) -> dict[str, Any]:
    return {
        "name": td.name,
        "description": td.description,
        "input_schema": td.input_schema,
    }


def _to_anthropic_tool_result(
    tool_use_id: str, content: str
) -> dict[str, Any]:
    return {
        "type": "tool_result",
        "tool_use_id": tool_use_id,
        "content": content,
    }


class AnthropicClient(BaseLLMClient):
    """LLM client backed by Anthropic's Claude API with native tool_use."""

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self._client = AsyncAnthropic(api_key=config.anthropic_api_key)
        self._model = config.anthropic_model
        self._max_tokens = config.max_tokens
        self._temperature = config.temperature

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        on_stream: StreamCallback | None = None,
    ) -> AsyncGenerator[LLMEvent, None]:
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

        # Append tool results from a previous turn if provided
        if tool_results:
            messages.append({"role": "user", "content": tool_results})

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "messages": messages,
        }
        if system_prompt:
            kwargs["system"] = system_prompt
        if tools:
            kwargs["tools"] = [_to_anthropic_tool(t) for t in tools]

        collected_text: list[str] = []

        async with self._client.messages.stream(**kwargs) as stream:
            current_tool_use_id: str | None = None
            current_tool_name: str | None = None
            current_tool_input_chunks: list[str] = []

            async for event in stream:
                if isinstance(event, RawMessageStartEvent):
                    # Contains a MessageStartEvent wrapper
                    if event.message and event.message.content:
                        for block in event.message.content:
                            if hasattr(block, "type") and block.type == "tool_use":
                                current_tool_use_id = block.id
                                current_tool_name = block.name
                                current_tool_input_chunks = []

                elif isinstance(event, RawContentBlockDeltaEvent):
                    delta = event.delta
                    if hasattr(delta, "type"):
                        if delta.type == "text_delta":
                            text = delta.text or ""
                            collected_text.append(text)
                            evt = LLMEvent(type="text", content=text)
                            if on_stream:
                                await on_stream(evt)
                            yield evt
                        elif delta.type == "input_json_delta":
                            current_tool_input_chunks.append(delta.partial_json or "")

                elif isinstance(event, RawMessageDeltaEvent):
                    # Stop reason / usage — finalisation
                    pass

            # After streaming — handle tool_use if we collected one
            if current_tool_use_id and current_tool_name:
                raw = "".join(current_tool_input_chunks)
                try:
                    tool_input = json.loads(raw) if raw.strip() else {}
                except json.JSONDecodeError:
                    tool_input = {}
                evt = LLMEvent(
                    type="tool_use",
                    content=current_tool_name,
                    tool_name=current_tool_name,
                    tool_input=tool_input,
                    tool_use_id=current_tool_use_id,
                )
                if on_stream:
                    await on_stream(evt)
                yield evt
                return

        # No tool_use — text-only response
        full_text = "".join(collected_text)
        yield LLMEvent(type="text", content=full_text, done=True)

    # ----- Embedding -------------------------------------------------------

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError(
            "Anthropic does not provide embedding endpoints. "
            "Set LLM_PROVIDER=openai or configure OPENAI_API_KEY for embeddings."
        )

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError(
            "Anthropic does not provide embedding endpoints. "
            "Set LLM_PROVIDER=openai or configure OPENAI_API_KEY for embeddings."
        )

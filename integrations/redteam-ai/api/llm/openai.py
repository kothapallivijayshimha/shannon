from __future__ import annotations

import json
from typing import Any, AsyncGenerator

from openai import AsyncOpenAI

from .base import BaseLLMClient, LLMEvent, LLMStream, StreamCallback, ToolDefinition


def _to_openai_tool(td: ToolDefinition) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": td.name,
            "description": td.description,
            "parameters": td.input_schema,
        },
    }


def _to_openai_tool_result(
    tool_call_id: str, content: str
) -> dict[str, Any]:
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


class OpenAIClient(BaseLLMClient):
    """LLM client backed by OpenAI with function-calling support."""

    def __init__(self, config: Any) -> None:
        super().__init__(config)
        self._client = AsyncOpenAI(api_key=config.openai_api_key)
        self._model = config.openai_model
        self._max_tokens = config.max_tokens
        self._temperature = config.temperature
        self._embedding_model = config.openai_embedding_model

    # ----- Generation ------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        tools: list[ToolDefinition] | None = None,
        tool_results: list[dict[str, Any]] | None = None,
        on_stream: StreamCallback | None = None,
    ) -> AsyncGenerator[LLMEvent, None]:
        messages: list[dict[str, Any]] = [{"role": "user", "content": prompt}]

        if tool_results:
            messages.append(tool_results[-1])  # caller must format properly

        kwargs: dict[str, Any] = {
            "model": self._model,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "messages": messages,
            "stream": True,
        }
        if system_prompt:
            kwargs["messages"].insert(
                0, {"role": "system", "content": system_prompt}
            )
        if tools:
            kwargs["tools"] = [_to_openai_tool(t) for t in tools]

        collected_text: list[str] = []
        partial_tool_calls: dict[int, dict[str, Any]] = {}

        stream = await self._client.chat.completions.create(**kwargs)

        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta is None:
                continue

            # Text content
            if delta.content:
                collected_text.append(delta.content)
                evt = LLMEvent(type="text", content=delta.content)
                if on_stream:
                    await on_stream(evt)
                yield evt

            # Tool calls (function calling)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in partial_tool_calls:
                        partial_tool_calls[idx] = {
                            "id": tc.id or "",
                            "name": tc.function.name or "",
                            "arguments": "",
                        }
                    if tc.id:
                        partial_tool_calls[idx]["id"] = tc.id
                    if tc.function and tc.function.name:
                        partial_tool_calls[idx]["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        partial_tool_calls[idx]["arguments"] += (
                            tc.function.arguments
                        )

            # Finish reason — yield tool_use events if any
            finish = chunk.choices[0].finish_reason if chunk.choices else None
            if finish == "tool_calls":
                for p in partial_tool_calls.values():
                    try:
                        parsed_args = json.loads(p["arguments"])
                    except json.JSONDecodeError:
                        parsed_args = {}
                    evt = LLMEvent(
                        type="tool_use",
                        content=p["name"],
                        tool_name=p["name"],
                        tool_input=parsed_args,
                        tool_use_id=p["id"],
                    )
                    if on_stream:
                        await on_stream(evt)
                    yield evt
                return

        # No tool calls — text-only
        yield LLMEvent(type="text", content="".join(collected_text), done=True)

    # ----- Embedding -------------------------------------------------------

    async def embed(self, text: str) -> list[float]:
        resp = await self._client.embeddings.create(
            model=self._embedding_model, input=text
        )
        return resp.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(
            model=self._embedding_model, input=texts
        )
        return [d.embedding for d in resp.data]

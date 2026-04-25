from __future__ import annotations

from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, cast, runtime_checkable

import httpx

if TYPE_CHECKING:
    from anthropic import AsyncAnthropic
    from openai import AsyncOpenAI


@dataclass(frozen=True)
class LLMCall:
    system: str
    user: str
    max_tokens: int
    temperature: float
    model: str | None


@runtime_checkable
class LLMClient(Protocol):
    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str: ...

    def stream(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AsyncIterator[str]: ...


@dataclass
class FakeLLMClient:
    responses: list[str] = field(default_factory=list[str])
    stream_responses: list[list[str]] = field(default_factory=list[list[str]])
    calls: list[LLMCall] = field(default_factory=list[LLMCall])

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str:
        self.calls.append(
            LLMCall(
                system=system,
                user=user,
                max_tokens=max_tokens,
                temperature=temperature,
                model=model,
            )
        )
        if not self.responses:
            raise RuntimeError("FakeLLMClient has no more scripted responses")
        return self.responses.pop(0)

    async def stream(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        self.calls.append(
            LLMCall(
                system=system,
                user=user,
                max_tokens=max_tokens,
                temperature=temperature,
                model=model,
            )
        )
        if not self.stream_responses:
            raise RuntimeError("FakeLLMClient has no more scripted stream responses")
        pieces = self.stream_responses.pop(0)
        for p in pieces:
            yield p


class AnthropicLLMClient:
    def __init__(self, api_key: str, default_model: str) -> None:
        from anthropic import Anthropic

        self._api_key = api_key
        self._client = Anthropic(api_key=api_key)
        self._default_model = default_model
        self._async_client: object | None = None

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str:
        response = self._client.messages.create(
            model=model or self._default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        )
        parts: list[str] = []
        for block in response.content:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                parts.append(text)
        return "".join(parts)

    async def stream(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        from anthropic import AsyncAnthropic

        if self._async_client is None:
            self._async_client = AsyncAnthropic(api_key=self._api_key)
        async_client = cast("AsyncAnthropic", self._async_client)
        async with async_client.messages.stream(
            model=model or self._default_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
        ) as stream:
            async for text in stream.text_stream:
                yield text


class OpenAICompatibleLLMClient:
    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        default_model: str,
        sync_transport: httpx.BaseTransport | None = None,
        async_transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        from openai import OpenAI

        sync_http = httpx.Client(transport=sync_transport) if sync_transport else None
        self._client = OpenAI(
            api_key=api_key,
            base_url=base_url,
            http_client=sync_http,
        )
        self._api_key = api_key
        self._base_url = base_url
        self._default_model = default_model
        self._async_transport = async_transport
        self._async_client: AsyncOpenAI | None = None

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str:
        resp = self._client.chat.completions.create(
            model=model or self._default_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        if not resp.choices:
            return ""
        return resp.choices[0].message.content or ""

    async def stream(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        from openai import AsyncOpenAI

        if self._async_client is None:
            async_http = (
                httpx.AsyncClient(transport=self._async_transport)
                if self._async_transport
                else None
            )
            self._async_client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                http_client=async_http,
            )
        async_client = self._async_client
        stream = await async_client.chat.completions.create(
            model=model or self._default_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

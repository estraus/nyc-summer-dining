import json
from collections.abc import Callable

import httpx
import pytest

from app.services.llm_client import (
    FakeLLMClient,
    LLMClient,
    OpenAICompatibleLLMClient,
)


def test_fake_returns_scripted_response() -> None:
    fake: LLMClient = FakeLLMClient(responses=["hello"])
    out = fake.complete(system="sys", user="hi", max_tokens=100)
    assert out == "hello"


def test_fake_raises_when_exhausted() -> None:
    fake = FakeLLMClient(responses=[])
    with pytest.raises(RuntimeError):
        fake.complete(system="sys", user="hi", max_tokens=100)


def test_fake_records_calls() -> None:
    fake = FakeLLMClient(responses=["a", "b"])
    fake.complete(system="sys", user="u1", max_tokens=50)
    fake.complete(system="sys", user="u2", max_tokens=75)
    assert [c.user for c in fake.calls] == ["u1", "u2"]
    assert fake.calls[0].max_tokens == 50


async def test_fake_stream_yields_chunks() -> None:
    fake = FakeLLMClient(stream_responses=[["ab", "cd", "ef"]])
    chunks: list[str] = []
    async for piece in fake.stream(system="sys", user="u", max_tokens=100):
        chunks.append(piece)
    assert chunks == ["ab", "cd", "ef"]


def _completion_handler(text: str) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["model"] == "test-model"
        assert body["messages"][0]["role"] == "system"
        assert body["messages"][1]["role"] == "user"
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "created": 0,
                "model": "test-model",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": text},
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 1,
                    "completion_tokens": 1,
                    "total_tokens": 2,
                },
            },
        )

    return handler


def _stream_handler(pieces: list[str]) -> Callable[[httpx.Request], httpx.Response]:
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body.get("stream") is True
        chunks: list[str] = []
        for p in pieces:
            payload = {
                "id": "chatcmpl-test",
                "object": "chat.completion.chunk",
                "created": 0,
                "model": "test-model",
                "choices": [{"index": 0, "delta": {"content": p}, "finish_reason": None}],
            }
            chunks.append(f"data: {json.dumps(payload)}\n\n")
        chunks.append("data: [DONE]\n\n")
        return httpx.Response(
            200,
            content="".join(chunks).encode(),
            headers={"content-type": "text/event-stream"},
        )

    return handler


def test_openai_compat_complete_returns_text() -> None:
    transport = httpx.MockTransport(_completion_handler("hi there"))
    client = OpenAICompatibleLLMClient(
        api_key="test-key",
        base_url="https://example.test/v1",
        default_model="test-model",
        sync_transport=transport,
    )
    out = client.complete(system="sys", user="user", max_tokens=50)
    assert out == "hi there"


async def test_openai_compat_stream_reuses_async_client() -> None:
    transport = httpx.MockTransport(_stream_handler(["x"]))
    client = OpenAICompatibleLLMClient(
        api_key="test-key",
        base_url="https://example.test/v1",
        default_model="test-model",
        async_transport=transport,
    )
    async for _ in client.stream(system="s", user="u", max_tokens=10):
        pass
    first = client._async_client
    async for _ in client.stream(system="s", user="u", max_tokens=10):
        pass
    second = client._async_client
    assert first is not None
    assert first is second


async def test_openai_compat_stream_yields_deltas() -> None:
    transport = httpx.MockTransport(_stream_handler(["hello", " world", "!"]))
    client = OpenAICompatibleLLMClient(
        api_key="test-key",
        base_url="https://example.test/v1",
        default_model="test-model",
        async_transport=transport,
    )
    pieces: list[str] = []
    async for chunk in client.stream(system="sys", user="user", max_tokens=50):
        pieces.append(chunk)
    assert pieces == ["hello", " world", "!"]

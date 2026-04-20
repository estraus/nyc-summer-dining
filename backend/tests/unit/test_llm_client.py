import pytest

from app.services.llm_client import FakeLLMClient, LLMClient


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

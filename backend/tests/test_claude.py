from types import SimpleNamespace

import pytest
from pydantic import BaseModel

from app.llm.claude import MAX_OUTPUT_TOKENS, Claude


class Answer(BaseModel):
    text: str


class FakeStream:
    def __init__(self, message):
        self.message = message

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def get_final_message(self):
        return self.message


def fake_client(message, calls: list):
    def stream(**kwargs):
        calls.append(kwargs)
        return FakeStream(message)

    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(stream=stream)))


async def test_generate_streams_structured_output():
    calls: list = []
    message = SimpleNamespace(stop_reason="end_turn", parsed_output=Answer(text="ok"))
    claude = Claude("claude-sonnet-5", client=fake_client(message, calls))

    result = await claude.generate(system="s", prompt="p", schema=Answer, effort="medium")

    assert result == Answer(text="ok")
    assert calls[0]["output_format"] is Answer and calls[0]["max_tokens"] == MAX_OUTPUT_TOKENS
    assert calls[0]["output_config"] == {"effort": "medium"} and "fallbacks" not in calls[0]


async def test_generate_reports_truncated_output():
    message = SimpleNamespace(stop_reason="max_tokens", parsed_output=None)
    claude = Claude("claude-sonnet-5", client=fake_client(message, []))
    with pytest.raises(RuntimeError, match="token limit"):
        await claude.generate(system="s", prompt="p", schema=Answer)

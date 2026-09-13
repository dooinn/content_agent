"""Claude calls used by the pipeline: web research and schema-validated generation."""

import base64
from dataclasses import dataclass, field
from typing import TypeVar

import anthropic
from pydantic import BaseModel

from app.services.media import image_type

T = TypeVar("T", bound=BaseModel)

# Server-side fallback: if a request is declined by safety classifiers, the API re-runs it
# on Anthropic's recommended fallback model instead of returning a refusal.
FALLBACK_BETA = "server-side-fallback-2026-07-01"
FALLBACK_MODELS = {"claude-opus-5", "claude-fable-5-1"}
WEB_SEARCH_TOOL = {"type": "web_search_20260209", "name": "web_search", "max_uses": 10}
MAX_CONTINUATIONS = 5


class ClaudeRefusal(RuntimeError):
    pass


@dataclass
class ResearchResult:
    notes: str
    sources: list[dict] = field(default_factory=list)


def _raise_on_refusal(response) -> None:
    if response.stop_reason == "refusal":
        details = response.stop_details
        reason = details.explanation if details else "no details"
        raise ClaudeRefusal(f"Claude declined the request: {reason}")


class Claude:
    def __init__(
        self,
        model: str,
        api_key: str | None = None,
        client: anthropic.AsyncAnthropic | None = None,
    ):
        self.model = model
        self.client = client or (
            anthropic.AsyncAnthropic(api_key=api_key) if api_key else anthropic.AsyncAnthropic()
        )

    def _fallbacks(self) -> dict:
        # Server-side fallbacks are documented for Opus 5 and Fable 5.1 only; other models
        # surface refusals as ClaudeRefusal.
        if self.model in FALLBACK_MODELS:
            return {"betas": [FALLBACK_BETA], "fallbacks": "default"}
        return {}

    async def generate(
        self,
        *,
        system: str,
        prompt: str,
        schema: type[T],
        effort: str = "high",
        images: list[bytes] | None = None,
    ) -> T:
        content: list[dict] = [
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": image_type(data)[1],
                    "data": base64.standard_b64encode(data).decode(),
                },
            }
            for data in images or []
        ]
        content.append({"type": "text", "text": prompt})
        response = await self.client.beta.messages.parse(
            model=self.model,
            max_tokens=16000,
            system=system,
            messages=[{"role": "user", "content": content}],
            output_format=schema,
            output_config={"effort": effort},
            **self._fallbacks(),
        )
        _raise_on_refusal(response)
        if response.parsed_output is None:
            raise RuntimeError(f"no structured output (stop_reason={response.stop_reason})")
        return response.parsed_output

    async def research(self, *, system: str, prompt: str) -> ResearchResult:
        """Web-search-backed research notes plus the deduplicated sources Claude saw."""
        messages: list[dict] = [{"role": "user", "content": prompt}]
        texts: list[str] = []
        sources: dict[str, str] = {}

        for _ in range(MAX_CONTINUATIONS):
            response = await self.client.beta.messages.create(
                model=self.model,
                max_tokens=16000,
                system=system,
                messages=messages,
                tools=[WEB_SEARCH_TOOL],
                **self._fallbacks(),
            )
            _raise_on_refusal(response)
            for block in response.content:
                if block.type == "text":
                    texts.append(block.text)
                    for citation in block.citations or []:
                        url = getattr(citation, "url", None)
                        if url:
                            sources.setdefault(url, getattr(citation, "title", None) or url)
                elif block.type == "web_search_tool_result" and isinstance(block.content, list):
                    for result in block.content:
                        sources.setdefault(result.url, result.title or result.url)
            # Long server-tool turns can pause; send the partial turn back to continue it.
            if response.stop_reason != "pause_turn":
                break
            messages.append({"role": "assistant", "content": response.content})

        return ResearchResult(
            notes="".join(texts).strip(),
            sources=[
                {"id": f"S{i}", "title": title, "url": url}
                for i, (url, title) in enumerate(sources.items(), start=1)
            ],
        )

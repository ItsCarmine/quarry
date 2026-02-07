"""Claude research backend — Anthropic API via httpx."""

from __future__ import annotations

import json
import logging

import httpx

from backend.backends.base import Claim, ResearchBackend, ResearchResult
from backend.config import settings
from backend.models.source import Source

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
DEFAULT_MODEL = "claude-opus-4-6"

SYSTEM_PROMPT = """\
You are a research assistant. Given a research query and optional source documents, \
produce a thorough, well-sourced research summary.

Respond with valid JSON in this exact format:
{
  "summary": "A comprehensive narrative summary of your findings.",
  "claims": [
    {
      "text": "A specific factual claim.",
      "source_urls": ["https://example.com/source"],
      "confidence": 0.95
    }
  ]
}

Rules:
- Break your findings into discrete, specific claims.
- For each claim, include source URLs you can cite. Use an empty list if no URL is available.
- Set confidence between 0.0 and 1.0 based on how well-supported the claim is.
- The summary should synthesize all claims into a readable narrative.
- If source documents are provided, prioritize information from them.\
"""


class ClaudeBackend:
    """Research backend using Anthropic's Claude API."""

    name: str = "Claude"

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model

    async def research(self, query: str, sources: list[Source]) -> ResearchResult:
        """Execute a research query via Claude and return structured results."""
        user_content = self._build_user_message(query, sources)

        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": self.model,
                    "max_tokens": 16000,
                    "thinking": {
                        "type": "enabled",
                        "budget_tokens": 10000,
                    },
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_content}],
                },
            )
            response.raise_for_status()

        data = response.json()
        # With extended thinking, content has thinking + text blocks
        raw_text = ""
        for block in data["content"]:
            if block["type"] == "text":
                raw_text = block["text"]
                break
        return self._parse_response(raw_text)

    def _build_user_message(self, query: str, sources: list[Source]) -> str:
        """Build the user message from query and optional sources."""
        parts = [f"Research query: {query}"]
        if sources:
            parts.append("\n--- Provided Sources ---")
            for i, source in enumerate(sources, 1):
                parts.append(f"\n[Source {i}] ({source.type.value}):\n{source.content}")
        return "\n".join(parts)

    def _parse_response(self, raw_text: str) -> ResearchResult:
        """Parse Claude's JSON response into a ResearchResult."""
        try:
            text = raw_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]

            parsed = json.loads(text)
            claims = [
                Claim(
                    text=c["text"],
                    source_urls=c.get("source_urls", []),
                    confidence=c.get("confidence", 1.0),
                )
                for c in parsed.get("claims", [])
            ]
            return ResearchResult(
                summary=parsed.get("summary", ""),
                claims=claims,
                raw_response=raw_text,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Failed to parse structured response, using raw text: %s", exc)
            return ResearchResult(
                summary=raw_text,
                claims=[],
                raw_response=raw_text,
            )

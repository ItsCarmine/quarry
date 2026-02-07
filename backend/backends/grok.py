"""Grok research backend — xAI API (OpenAI-compatible)."""

from __future__ import annotations

import json
import logging

import httpx

from backend.backends.base import Claim, ResearchBackend, ResearchResult
from backend.config import settings
from backend.models.source import Source

logger = logging.getLogger(__name__)

XAI_API_URL = "https://api.x.ai/v1/chat/completions"
DEFAULT_MODEL = "grok-4-1-fast"

SYSTEM_PROMPT = """\
You are a research assistant with access to real-time information from X/Twitter, \
news, and current events. Given a research query and optional source documents, \
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
- Leverage your strength in real-time data, news, and social media sources.
- If source documents are provided, prioritize information from them.\
"""


class GrokBackend:
    """Research backend using xAI's Grok API."""

    name: str = "Grok"

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key or settings.xai_api_key
        self.model = model

    async def research(self, query: str, sources: list[Source]) -> ResearchResult:
        """Execute a research query via Grok and return structured results."""
        user_content = self._build_user_message(query, sources)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                XAI_API_URL,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_content},
                    ],
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()

        data = response.json()
        raw_text = data["choices"][0]["message"]["content"]
        return self._parse_response(raw_text)

    def _build_user_message(self, query: str, sources: list[Source]) -> str:
        parts = [f"Research query: {query}"]
        if sources:
            parts.append("\n--- Provided Sources ---")
            for i, source in enumerate(sources, 1):
                parts.append(f"\n[Source {i}] ({source.type.value}):\n{source.content}")
        return "\n".join(parts)

    def _parse_response(self, raw_text: str) -> ResearchResult:
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
            logger.warning("Grok: failed to parse structured response: %s", exc)
            return ResearchResult(summary=raw_text, claims=[], raw_response=raw_text)

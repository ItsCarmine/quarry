"""Gemini Deep Research backend — Google Generative AI API."""

from __future__ import annotations

import json
import logging

import httpx

from backend.backends.base import Claim, ResearchBackend, ResearchResult
from backend.config import settings
from backend.models.source import Source

logger = logging.getLogger(__name__)

GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.5-pro-preview-06-05"

SYSTEM_PROMPT = """\
You are a research assistant specializing in deep, thorough research across \
a broad range of topics. Given a research query and optional source documents, \
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
- Be thorough — explore the topic from multiple angles.
- If source documents are provided, prioritize information from them.\
"""


class GeminiBackend:
    """Research backend using Google's Gemini API."""

    name: str = "Gemini"

    def __init__(self, api_key: str | None = None, model: str = DEFAULT_MODEL) -> None:
        self.api_key = api_key or settings.google_api_key
        self.model = model

    async def research(self, query: str, sources: list[Source]) -> ResearchResult:
        """Execute a research query via Gemini and return structured results."""
        user_content = self._build_user_message(query, sources)
        url = f"{GEMINI_API_URL}/{self.model}:generateContent?key={self.api_key}"

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                url,
                headers={"Content-Type": "application/json"},
                json={
                    "system_instruction": {
                        "parts": [{"text": SYSTEM_PROMPT}],
                    },
                    "contents": [
                        {"parts": [{"text": user_content}]},
                    ],
                    "generationConfig": {
                        "temperature": 0.7,
                        "responseMimeType": "application/json",
                    },
                },
            )
            response.raise_for_status()

        data = response.json()
        raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
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
            logger.warning("Gemini: failed to parse structured response: %s", exc)
            return ResearchResult(summary=raw_text, claims=[], raw_response=raw_text)

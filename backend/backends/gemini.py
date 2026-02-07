"""Gemini Deep Research backend — Google Interactions API."""

from __future__ import annotations

import asyncio
import json
import logging
import re

import httpx

from backend.backends.base import Claim, ResearchBackend, ResearchResult
from backend.config import settings
from backend.models.source import Source

logger = logging.getLogger(__name__)

INTERACTIONS_URL = "https://generativelanguage.googleapis.com/v1beta/interactions"
DEFAULT_AGENT = "deep-research-pro-preview-12-2025"

# Deep Research returns a full prose report, not structured JSON.
# We ask for structured output in a follow-up parse, but the primary
# value is the thorough, multi-step research it performs.
POLL_INTERVAL = 10  # seconds
MAX_POLL_TIME = 600  # 10 minutes max wait


class GeminiBackend:
    """Research backend using Google's Gemini Deep Research agent."""

    name: str = "Gemini Deep Research"

    def __init__(self, api_key: str | None = None, agent: str = DEFAULT_AGENT) -> None:
        self.api_key = api_key or settings.google_api_key
        self.agent = agent

    async def research(self, query: str, sources: list[Source]) -> ResearchResult:
        """Execute a deep research query via Gemini Interactions API."""
        user_input = self._build_input(query, sources)

        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Start the research task
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.api_key,
            }
            response = await client.post(
                INTERACTIONS_URL,
                headers=headers,
                json={
                    "input": user_input,
                    "agent": self.agent,
                    "background": True,
                },
            )
            response.raise_for_status()
            interaction = response.json()
            interaction_id = interaction["id"]
            logger.info("Gemini Deep Research started: %s", interaction_id)

            # 2. Poll for completion
            elapsed = 0
            while elapsed < MAX_POLL_TIME:
                await asyncio.sleep(POLL_INTERVAL)
                elapsed += POLL_INTERVAL

                poll_response = await client.get(
                    f"{INTERACTIONS_URL}/{interaction_id}",
                    headers=headers,
                )
                poll_response.raise_for_status()
                interaction = poll_response.json()
                status = interaction.get("status", "")

                if status == "completed":
                    raw_text = self._extract_output(interaction)
                    logger.info(
                        "Gemini Deep Research completed (%ds, %d chars)",
                        elapsed, len(raw_text),
                    )
                    return self._parse_research_report(raw_text)

                if status == "failed":
                    error = interaction.get("error", "Unknown error")
                    raise RuntimeError(f"Gemini Deep Research failed: {error}")

                logger.debug("Gemini Deep Research polling... (%ds, status=%s)", elapsed, status)

            raise TimeoutError(
                f"Gemini Deep Research did not complete within {MAX_POLL_TIME}s"
            )

    def _build_input(self, query: str, sources: list[Source]) -> str:
        parts = [query]
        if sources:
            parts.append("\n\nReference sources:")
            for i, source in enumerate(sources, 1):
                parts.append(f"\n[Source {i}] ({source.type.value}):\n{source.content}")
        return "\n".join(parts)

    def _extract_output(self, interaction: dict) -> str:
        """Extract the text output from a completed interaction."""
        outputs = interaction.get("outputs", [])
        if outputs:
            # Last output contains the final report
            last = outputs[-1]
            if isinstance(last, dict):
                return last.get("text", str(last))
            return str(last)
        return ""

    def _parse_research_report(self, raw_text: str) -> ResearchResult:
        """Parse Deep Research prose report into structured claims.

        Deep Research returns a full prose report with citations, not JSON.
        We extract claims by splitting the report into key statements.
        """
        # Extract URLs from the report as source citations
        urls = re.findall(r'https?://[^\s\)\]\>\"]+', raw_text)

        # Split into paragraphs and treat each substantive paragraph as a claim
        paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
        claims: list[Claim] = []

        for para in paragraphs:
            # Skip very short lines (headers, labels)
            if len(para) < 40:
                continue
            # Skip markdown headers
            if para.startswith("#"):
                continue

            # Extract any inline URLs from this paragraph
            para_urls = re.findall(r'https?://[^\s\)\]\>\"]+', para)

            claims.append(
                Claim(
                    text=para[:500],  # Cap claim length
                    source_urls=para_urls,
                    confidence=0.85,  # Deep Research is well-sourced
                )
            )

        # Build summary from first few paragraphs
        summary_parts = [p.strip() for p in paragraphs[:3] if len(p.strip()) >= 40]
        summary = " ".join(summary_parts)[:1000]

        return ResearchResult(
            summary=summary or raw_text[:1000],
            claims=claims,
            raw_response=raw_text,
        )

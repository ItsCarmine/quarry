"""Synthesizer — Opus 4.6 'mayoral' brain that merges multi-LLM findings."""

from __future__ import annotations

import json
import logging
from uuid import UUID

import httpx

from backend.backends.base import ResearchResult
from backend.config import settings
from backend.models.report import Citation, Conflict, Report

logger = logging.getLogger(__name__)

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
SYNTHESIS_MODEL = "claude-opus-4-6"

SYNTHESIS_PROMPT = """\
You are the chief research synthesizer. You receive findings from multiple \
AI research assistants (Claude, Grok, Gemini) and must produce a unified, \
authoritative synthesis.

You will be given research results from each backend. Your job:
1. Merge and cross-reference findings across all sources.
2. Identify claims that multiple backends agree on (high confidence).
3. Identify claims unique to one backend (note the source).
4. Detect CONFLICTS where backends disagree — these are critical to flag.
5. Produce a coherent, deduplicated set of claims with proper attribution.

Respond with valid JSON in this exact format:
{
  "claims": [
    {
      "text": "A specific factual claim.",
      "llm_source": "Claude, Grok",
      "source_urls": ["https://example.com"],
      "confidence": 0.95
    }
  ],
  "conflicts": [
    {
      "topic": "Brief description of the disagreement",
      "positions": [
        {"source": "Claude", "claim": "What Claude said"},
        {"source": "Grok", "claim": "What Grok said"}
      ]
    }
  ]
}

Rules:
- Attribute each claim to ALL backends that reported it (comma-separated in llm_source).
- Claims agreed upon by multiple backends get higher confidence.
- Include source URLs from any backend that provided them.
- Flag every contradiction as a conflict — never silently drop disagreements.
- Be thorough but avoid redundancy.\
"""


class Synthesizer:
    """Opus 4.6 mayoral synthesizer — LLM-powered cross-backend merge."""

    def __init__(
        self, api_key: str | None = None, model: str = SYNTHESIS_MODEL
    ) -> None:
        self.api_key = api_key or settings.anthropic_api_key
        self.model = model

    async def synthesize(
        self, brief_id: UUID, results: list[tuple[str, ResearchResult]]
    ) -> Report:
        """Use Opus 4.6 to intelligently merge findings from all backends."""
        if len(results) == 1:
            # Single backend — skip the LLM call, just structure the output
            return self._single_backend(brief_id, results[0])

        # Build the input for the mayoral brain
        user_content = self._build_synthesis_input(results)

        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                response = await client.post(
                    ANTHROPIC_API_URL,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 8192,
                        "system": SYNTHESIS_PROMPT,
                        "messages": [{"role": "user", "content": user_content}],
                    },
                )
                response.raise_for_status()

            data = response.json()
            raw_text = data["content"][0]["text"]
            return self._parse_synthesis(brief_id, raw_text)

        except Exception as exc:
            logger.error("Mayoral synthesis failed, falling back to naive merge: %s", exc)
            return self._naive_merge(brief_id, results)

    def _build_synthesis_input(
        self, results: list[tuple[str, ResearchResult]]
    ) -> str:
        """Format all backend results for the synthesizer."""
        parts: list[str] = []
        for backend_name, result in results:
            parts.append(f"=== {backend_name} ===")
            parts.append(f"Summary: {result.summary}")
            if result.claims:
                parts.append("Claims:")
                for i, claim in enumerate(result.claims, 1):
                    urls = ", ".join(claim.source_urls) if claim.source_urls else "none"
                    parts.append(
                        f"  {i}. {claim.text} "
                        f"[confidence: {claim.confidence}, sources: {urls}]"
                    )
            parts.append("")
        return "\n".join(parts)

    def _parse_synthesis(self, brief_id: UUID, raw_text: str) -> Report:
        """Parse the mayoral synthesis into a Report."""
        try:
            text = raw_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                text = text.rsplit("```", 1)[0]

            parsed = json.loads(text)

            citations = [
                Citation(
                    claim=c["text"],
                    llm_source=c.get("llm_source", "Unknown"),
                    underlying_url=(c.get("source_urls") or [None])[0],
                    confidence=c.get("confidence", 1.0),
                )
                for c in parsed.get("claims", [])
            ]

            conflicts = [
                Conflict(
                    topic=cf["topic"],
                    positions=[
                        Citation(
                            claim=pos["claim"],
                            llm_source=pos["source"],
                        )
                        for pos in cf.get("positions", [])
                    ],
                )
                for cf in parsed.get("conflicts", [])
            ]

            return Report(
                brief_id=brief_id,
                citations=citations,
                conflicts=conflicts,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            logger.warning("Failed to parse synthesis, falling back: %s", exc)
            return Report(brief_id=brief_id, citations=[], conflicts=[])

    def _single_backend(
        self, brief_id: UUID, result: tuple[str, ResearchResult]
    ) -> Report:
        """Structure output from a single backend (no synthesis needed)."""
        backend_name, res = result
        citations = [
            Citation(
                claim=c.text,
                llm_source=backend_name,
                underlying_url=c.source_urls[0] if c.source_urls else None,
                confidence=c.confidence,
            )
            for c in res.claims
        ]
        return Report(brief_id=brief_id, citations=citations)

    def _naive_merge(
        self, brief_id: UUID, results: list[tuple[str, ResearchResult]]
    ) -> Report:
        """Fallback: simple dedup merge without LLM synthesis."""
        citations: list[Citation] = []
        for backend_name, result in results:
            for claim in result.claims:
                url = claim.source_urls[0] if claim.source_urls else None
                citations.append(
                    Citation(
                        claim=claim.text,
                        llm_source=backend_name,
                        underlying_url=url,
                        confidence=claim.confidence,
                    )
                )

        seen: dict[str, Citation] = {}
        for c in citations:
            key = c.claim.strip().lower()
            if key not in seen or c.confidence > seen[key].confidence:
                seen[key] = c
        return Report(brief_id=brief_id, citations=list(seen.values()))

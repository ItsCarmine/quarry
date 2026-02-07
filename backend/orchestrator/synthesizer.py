"""Synthesizer — merges backend results into a structured report."""

from __future__ import annotations

from uuid import UUID

from backend.backends.base import ResearchResult
from backend.models.report import Citation, Report


class Synthesizer:
    """Merges results from one or more backends into a unified Report."""

    def synthesize(
        self, brief_id: UUID, results: list[tuple[str, ResearchResult]]
    ) -> Report:
        """Build a Report from dispatcher results.

        Each (backend_name, ResearchResult) pair is converted into Citations
        with full LLM provenance.  The combined summary is concatenated from
        all backends (MVP; future versions will use an LLM to merge).
        """
        citations: list[Citation] = []
        summary_parts: list[str] = []

        for backend_name, result in results:
            summary_parts.append(result.summary)

            for claim in result.claims:
                # Pick the first source URL if available
                url = claim.source_urls[0] if claim.source_urls else None
                citations.append(
                    Citation(
                        claim=claim.text,
                        llm_source=backend_name,
                        underlying_url=url,
                        confidence=claim.confidence,
                    )
                )

        # Deduplicate claims with identical text, keeping the higher-confidence one
        citations = self._dedup_citations(citations)

        return Report(
            brief_id=brief_id,
            citations=citations,
        )

    def _dedup_citations(self, citations: list[Citation]) -> list[Citation]:
        """Remove duplicate claims, preferring higher confidence."""
        seen: dict[str, Citation] = {}
        for c in citations:
            key = c.claim.strip().lower()
            if key not in seen or c.confidence > seen[key].confidence:
                seen[key] = c
        return list(seen.values())

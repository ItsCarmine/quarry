"""Base protocol for all research backends."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from backend.models.source import Source


@dataclass
class ResearchResult:
    """Result returned by a research backend."""

    summary: str
    claims: list[Claim] = field(default_factory=list)
    raw_response: str = ""


@dataclass
class Claim:
    """A single factual claim with provenance."""

    text: str
    source_urls: list[str] = field(default_factory=list)
    confidence: float = 1.0


@runtime_checkable
class ResearchBackend(Protocol):
    """Interface that all LLM research backends must implement."""

    name: str

    async def research(self, query: str, sources: list[Source]) -> ResearchResult:
        """Execute a research query and return structured results."""
        ...

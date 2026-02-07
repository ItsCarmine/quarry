"""Report and citation data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from backend.models.source import Source


@dataclass
class Citation:
    """A cited claim with full provenance chain."""

    claim: str
    llm_source: str
    underlying_url: str | None = None
    underlying_doc: Source | None = None
    confidence: float = 1.0
    id: UUID = field(default_factory=uuid4)


@dataclass
class Conflict:
    """A disagreement between sources on a factual claim."""

    topic: str
    positions: list[Citation] = field(default_factory=list)
    resolution: str | None = None
    id: UUID = field(default_factory=uuid4)


@dataclass
class Report:
    """A synthesized research report."""

    brief_id: UUID
    typst_source: str = ""
    citations: list[Citation] = field(default_factory=list)
    conflicts: list[Conflict] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)

"""Research brief data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from backend.models.source import Source


@dataclass
class ResearchBrief:
    """A freeform research query submitted by the user."""

    query: str
    sources: list[Source] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)

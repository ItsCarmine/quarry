"""Source data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID, uuid4


class SourceType(Enum):
    PDF = "pdf"
    URL = "url"
    DOC = "doc"
    TEXT = "text"


@dataclass
class Source:
    """A research source — uploaded by the user or discovered by an LLM."""

    type: SourceType
    content: str
    metadata: dict = field(default_factory=dict)
    origin: str = "upload"
    id: UUID = field(default_factory=uuid4)

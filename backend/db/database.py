"""SQLite database layer via aiosqlite."""

from __future__ import annotations

import json
import uuid

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS briefs (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    sources_json TEXT NOT NULL DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reports (
    id TEXT PRIMARY KEY,
    brief_id TEXT NOT NULL REFERENCES briefs(id),
    typst_source TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS citations (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id),
    claim TEXT NOT NULL,
    llm_source TEXT NOT NULL,
    underlying_url TEXT,
    confidence REAL NOT NULL DEFAULT 1.0
);

CREATE TABLE IF NOT EXISTS conflicts (
    id TEXT PRIMARY KEY,
    report_id TEXT NOT NULL REFERENCES reports(id),
    topic TEXT NOT NULL,
    resolution TEXT
);

CREATE TABLE IF NOT EXISTS conflict_positions (
    conflict_id TEXT NOT NULL REFERENCES conflicts(id),
    citation_id TEXT NOT NULL REFERENCES citations(id),
    PRIMARY KEY (conflict_id, citation_id)
);
"""


class Database:
    """Async SQLite database for persisting research data."""

    def __init__(self, path: str = "quarry.db") -> None:
        self.path = path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self.path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)

    async def close(self) -> None:
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        if self._db is None:
            raise RuntimeError("Database not connected — call connect() first")
        return self._db

    # -- Briefs --

    async def create_brief(self, query: str, sources_json: str = "[]") -> str:
        brief_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO briefs (id, query, sources_json) VALUES (?, ?, ?)",
            (brief_id, query, sources_json),
        )
        await self.db.commit()
        return brief_id

    async def get_brief(self, brief_id: str) -> dict | None:
        cursor = await self.db.execute("SELECT * FROM briefs WHERE id = ?", (brief_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    # -- Reports --

    async def create_report(self, brief_id: str) -> str:
        report_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO reports (id, brief_id) VALUES (?, ?)",
            (report_id, brief_id),
        )
        await self.db.commit()
        return report_id

    async def update_report_typst(self, report_id: str, typst_source: str) -> None:
        await self.db.execute(
            "UPDATE reports SET typst_source = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (typst_source, report_id),
        )
        await self.db.commit()

    async def get_report(self, report_id: str) -> dict | None:
        cursor = await self.db.execute("SELECT * FROM reports WHERE id = ?", (report_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_report_by_brief(self, brief_id: str) -> dict | None:
        cursor = await self.db.execute(
            "SELECT * FROM reports WHERE brief_id = ? ORDER BY created_at DESC LIMIT 1",
            (brief_id,),
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    # -- Citations --

    async def add_citation(
        self,
        report_id: str,
        claim: str,
        llm_source: str,
        underlying_url: str | None = None,
        confidence: float = 1.0,
    ) -> str:
        citation_id = str(uuid.uuid4())
        await self.db.execute(
            "INSERT INTO citations (id, report_id, claim, llm_source, underlying_url, confidence) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (citation_id, report_id, claim, llm_source, underlying_url, confidence),
        )
        await self.db.commit()
        return citation_id

    async def get_citations(self, report_id: str) -> list[dict]:
        cursor = await self.db.execute(
            "SELECT * FROM citations WHERE report_id = ?", (report_id,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

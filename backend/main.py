"""Quarry — FastAPI application entry point."""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from uuid import UUID

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.backends.claude import ClaudeBackend
from backend.backends.gemini import GeminiBackend
from backend.backends.grok import GrokBackend
from backend.config import settings
from backend.db.database import Database
from backend.models.brief import ResearchBrief
from backend.orchestrator.dispatcher import Dispatcher
from backend.orchestrator.synthesizer import Synthesizer
from backend.orchestrator.typst_generator import TypstGenerator

logger = logging.getLogger(__name__)

db = Database()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    yield
    await db.close()


app = FastAPI(
    title="Quarry",
    description="Multi-LLM Deep Research Orchestrator",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request / Response models ---


class ResearchRequest(BaseModel):
    query: str


class ResearchResponse(BaseModel):
    brief_id: str
    report_id: str


class ReportResponse(BaseModel):
    report_id: str
    brief_id: str
    typst_source: str
    citations: list[dict]


# --- Routes ---


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/api/research", response_model=ResearchResponse)
async def create_research(req: ResearchRequest):
    """Accept a research brief and kick off research.

    Returns brief_id and report_id immediately.  Connect to the WebSocket
    at /ws/research/{report_id} to stream live Typst updates.
    """
    brief_id = await db.create_brief(req.query)
    report_id = await db.create_report(brief_id)

    # Run research pipeline in background so the POST returns fast
    asyncio.create_task(_run_pipeline(brief_id, report_id, req.query))

    return ResearchResponse(brief_id=brief_id, report_id=report_id)


@app.get("/api/reports/{report_id}", response_model=ReportResponse)
async def get_report(report_id: str):
    """Fetch a completed (or in-progress) report."""
    report = await db.get_report(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="Report not found")

    citations = await db.get_citations(report_id)
    return ReportResponse(
        report_id=report["id"],
        brief_id=report["brief_id"],
        typst_source=report["typst_source"],
        citations=citations,
    )


# --- WebSocket ---

# Active WS connections keyed by report_id
_ws_connections: dict[str, list[WebSocket]] = {}


@app.websocket("/ws/research/{report_id}")
async def research_ws(websocket: WebSocket, report_id: str):
    """Stream live Typst updates for a research report."""
    await websocket.accept()
    _ws_connections.setdefault(report_id, []).append(websocket)
    try:
        # Keep connection alive; client can send follow-up queries here later
        while True:
            data = await websocket.receive_text()
            # MVP: echo back acknowledgement; follow-ups handled in future
            await websocket.send_json({"type": "ack", "data": data})
    except WebSocketDisconnect:
        _ws_connections.get(report_id, []).remove(websocket)


async def _broadcast(report_id: str, message: dict) -> None:
    """Send a message to all WebSocket clients watching a report."""
    for ws in _ws_connections.get(report_id, []):
        try:
            await ws.send_json(message)
        except Exception:
            pass


# --- Pipeline ---


async def _run_pipeline(brief_id: str, report_id: str, query: str) -> None:
    """Execute the full research pipeline and broadcast updates."""
    try:
        # Build backend list from available API keys
        backends = [ClaudeBackend()]  # Always available (Opus 4.6)
        if settings.xai_api_key:
            backends.append(GrokBackend())
        if settings.google_api_key:
            backends.append(GeminiBackend())

        backend_names = [b.name for b in backends]
        logger.info("Dispatching to %d backends: %s", len(backends), backend_names)

        await _broadcast(report_id, {
            "type": "status",
            "stage": "dispatching",
            "backends": [{"name": b.name, "status": "searching"} for b in backends],
        })

        # Dispatch to all backends in parallel with per-backend progress
        brief = ResearchBrief(query=query)
        results: list[tuple[str, ResearchResult]] = []

        async def _run_backend(backend):
            try:
                result = await backend.research(brief.query, brief.sources)
                results.append((backend.name, result))
                await _broadcast(report_id, {
                    "type": "backend_update",
                    "name": backend.name,
                    "status": "done",
                    "claims": len(result.claims),
                })
            except Exception as exc:
                logger.error("Backend %s failed: %s", backend.name, exc)
                await _broadcast(report_id, {
                    "type": "backend_update",
                    "name": backend.name,
                    "status": "failed",
                    "error": str(exc)[:200],
                })

        await asyncio.gather(*[_run_backend(b) for b in backends])

        if not results:
            raise RuntimeError("All backends failed")

        # Mayoral synthesis
        await _broadcast(report_id, {
            "type": "status",
            "stage": "synthesizing",
            "detail": f"Opus 4.6 synthesizing {len(results)} backend results...",
        })

        synthesizer = Synthesizer()
        report = await synthesizer.synthesize(UUID(brief_id), results)

        await _broadcast(report_id, {
            "type": "status",
            "stage": "generating",
            "detail": "Generating Typst report...",
        })

        # Generate Typst
        generator = TypstGenerator()
        typst_source = generator.generate(report, query=query)

        # Persist
        await db.update_report_typst(report_id, typst_source)
        for citation in report.citations:
            await db.add_citation(
                report_id,
                citation.claim,
                citation.llm_source,
                citation.underlying_url,
                citation.confidence,
            )

        # Broadcast final result
        await _broadcast(
            report_id,
            {"type": "report", "typst_source": typst_source},
        )
        await _broadcast(report_id, {"type": "status", "stage": "done"})

    except Exception:
        logger.exception("Pipeline failed for brief %s", brief_id)
        await _broadcast(
            report_id,
            {"type": "error", "detail": "Research pipeline failed"},
        )

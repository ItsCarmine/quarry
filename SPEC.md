# Quarry — Multi-LLM Deep Research Orchestrator

## Overview

Quarry is a web-based research workbench that dispatches research queries across
multiple LLMs, synthesizes their findings, and produces a live-updating
typeset report (PDF via Typst). It is designed to be used with Gas Town (`gt`)
for multi-agent orchestration.

## Core Concept

User submits a freeform research brief → Quarry fans the query out across
specialized LLM backends → results are synthesized, deduplicated, and
cross-referenced → a structured Typst report is generated and rendered live
in the browser → user can highlight text for inline follow-ups or steer
via a chat sidebar → the report evolves iteratively.

---

## Architecture

### Frontend (React + Vite)

- **Live Report Panel** (center): Typst source compiled to SVG/PDF in-browser
  via [typst.ts](https://github.com/Myriad-Dreamin/typst.ts) (WASM).
  Renders in real-time as the backend streams Typst updates.
- **Research Chat Sidebar** (right): Freeform text input for directing
  research. Supports follow-up questions, scope changes, and revision
  requests. Displays agent activity/status.
- **Inline Annotations**: User can highlight any text in the rendered report
  to open a popover for follow-up questions scoped to that section.
- **Source Upload Panel**: Upload PDFs, paste URLs, attach documents. These
  become first-class sources that all LLM backends can reference.
- **WebSocket connection** to backend for live streaming updates.

### Backend (Python / FastAPI)

- **Research Orchestrator**
  - **Dispatcher**: Receives a research brief or follow-up query. Decomposes
    it into sub-queries optimized for each LLM backend's strengths. Fans
    out requests in parallel.
  - **Synthesizer**: Merges responses from all backends. Deduplicates
    findings. Detects and structures conflicts. Builds a citation graph
    with full provenance.
  - **Typst Generator**: Produces and incrementally updates a Typst document
    from synthesized findings. Handles section structure, citations,
    conflict callout boxes, and formatting.

- **LLM Backend Interface** (pluggable adapter pattern)
  Each backend implements a common interface:
  ```python
  class ResearchBackend(Protocol):
      name: str
      async def research(self, query: str, sources: list[Source]) -> ResearchResult
  ```

  Initial backends:
  - **Gemini Deep Research** — Google's multi-step research mode. Best for
    broad topic exploration with Google index access.
  - **Kimi K2.5 (w/ search)** — Moonshot AI. Strong web search, good with
    Chinese-language and international sources.
  - **Grok** — xAI. Real-time X/Twitter data, news, current events.
  - **Claude** — Anthropic. Deep reasoning, analysis, long-context synthesis.
  - **Codex** — OpenAI agent. Code-heavy research, technical documentation.
  - **NotebookLM** — Google. Grounded queries against user-uploaded sources.
    API: https://docs.cloud.google.com/gemini/enterprise/notebooklm-enterprise/docs/api-notebooks
  - *(Extensible — add Perplexity, Tavily, etc. via the same interface)*

- **Source Store**
  - Uploaded PDFs parsed and chunked (PyMuPDF or similar)
  - URL snapshots fetched and cached
  - All sources tracked with metadata for citation

- **Provenance Tracking**
  Full chain: `LLM said X → citing [source URL/document]`
  Every claim in the report links back to:
  1. Which LLM(s) reported it
  2. What underlying source(s) the LLM cited
  3. The original source URL or document reference

### Data Model

```
ResearchBrief
  ├── id: uuid
  ├── query: str (freeform text)
  ├── sources: list[Source]  (user-uploaded)
  └── report: Report

Report
  ├── id: uuid
  ├── typst_source: str
  ├── sections: list[Section]
  ├── citations: list[Citation]
  └── conflicts: list[Conflict]

Citation
  ├── claim: str
  ├── llm_source: str  (which LLM)
  ├── underlying_url: str | None
  ├── underlying_doc: Source | None
  └── confidence: float

Conflict
  ├── claim_a: Citation
  ├── claim_b: Citation
  └── resolution: str | None  (user can resolve)

Source
  ├── type: "pdf" | "url" | "doc" | "text"
  ├── content: str (parsed text)
  ├── metadata: dict
  └── origin: str (upload vs discovered)
```

### Conflict Handling

Conflicts are first-class elements in the report, rendered as structured
callout boxes in Typst:

```typst
#conflict-box(
  topic: "Revenue figures for Acme Corp (2025)",
  positions: (
    (source: "Gemini", claim: "$2.1B", citation: "Reuters, Jan 2026"),
    (source: "Grok", claim: "$1.8B", citation: "@analyst_jane on X, Dec 2025"),
  ),
  resolution: none,
)
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 19 + Vite |
| Typst Rendering | typst.ts (WASM, in-browser) |
| Backend | Python 3.12+ / FastAPI |
| WebSocket | FastAPI WebSocket + frontend WS client |
| Database | SQLite (via aiosqlite) for reports, citations, sources |
| PDF Parsing | PyMuPDF (fitz) |
| LLM APIs | httpx (async HTTP client) per backend |
| Task Queue | (optional) Celery or arq for long-running research jobs |

---

## Project Structure

```
quarry/
├── SPEC.md
├── pyproject.toml
│
├── backend/
│   ├── __init__.py
│   ├── main.py                  # FastAPI app entry
│   ├── config.py                # API keys, settings
│   ├── orchestrator/
│   │   ├── __init__.py
│   │   ├── dispatcher.py        # Query decomposition & fan-out
│   │   ├── synthesizer.py       # Merge, dedup, conflict detection
│   │   └── typst_generator.py   # Typst document builder
│   ├── backends/
│   │   ├── __init__.py
│   │   ├── base.py              # ResearchBackend protocol
│   │   ├── gemini.py
│   │   ├── kimi.py
│   │   ├── grok.py
│   │   ├── claude.py
│   │   ├── codex.py
│   │   └── notebooklm.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── brief.py
│   │   ├── report.py
│   │   ├── citation.py
│   │   └── source.py
│   ├── sources/
│   │   ├── __init__.py
│   │   ├── parser.py            # PDF/URL/doc parsing
│   │   └── store.py             # Source storage & retrieval
│   └── db/
│       ├── __init__.py
│       ├── database.py
│       └── migrations/
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ReportViewer.tsx      # Typst live render panel
│   │   │   ├── ChatSidebar.tsx       # Research chat
│   │   │   ├── InlineAnnotation.tsx  # Highlight → follow-up
│   │   │   ├── SourceUpload.tsx      # Upload PDFs/URLs
│   │   │   └── ConflictBox.tsx       # Conflict display
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts       # WS connection to backend
│   │   │   └── useTypst.ts           # typst.ts WASM integration
│   │   └── types/
│   │       └── index.ts
│   └── public/
│
├── typst/
│   ├── templates/
│   │   └── report.typ            # Base report template
│   └── components/
│       ├── conflict-box.typ      # Conflict callout component
│       └── citation.typ          # Citation formatting
│
└── tests/
    ├── backend/
    └── frontend/
```

---

## Gas Town Integration

This project is managed as a Gas Town rig. Suggested agent roles:

- **Crew: backend** — Works on Python/FastAPI backend code
- **Crew: frontend** — Works on React/Vite frontend code
- **Crew: typst** — Works on Typst templates and rendering integration
- **Crew: backends** — Implements and tests individual LLM backend adapters
- **Polecats** — Ephemeral agents for specific tasks (parsing, testing, etc.)

---

## Milestones

### MVP (v0.1)

1. FastAPI backend with WebSocket endpoint
2. Single LLM backend working (Claude) as proof of concept
3. Freeform research brief input → Typst report generation
4. React frontend with live Typst rendering (typst.ts)
5. Chat sidebar for follow-up questions
6. Basic provenance tracking (LLM → source URL)

### v0.2

7. Add Gemini Deep Research + Grok backends
8. Source upload (PDF parsing, URL fetching)
9. Conflict detection and display
10. Inline text annotation for follow-ups

### v0.3

11. Add Kimi K2.5, Codex, NotebookLM backends
12. Full citation graph with provenance chain
13. Report export (PDF download)
14. Report history / versioning

"""Research dispatcher — fans queries out to backends."""

from __future__ import annotations

import asyncio
import logging

from backend.backends.base import ResearchBackend, ResearchResult
from backend.models.brief import ResearchBrief

logger = logging.getLogger(__name__)


class Dispatcher:
    """Dispatches a research brief to one or more LLM backends in parallel."""

    def __init__(self, backends: list[ResearchBackend]) -> None:
        if not backends:
            raise ValueError("At least one backend is required")
        self.backends = backends

    async def dispatch(self, brief: ResearchBrief) -> list[tuple[str, ResearchResult]]:
        """Fan out a research brief to all backends.

        Returns a list of (backend_name, result) tuples.
        Failed backends are logged and skipped.
        """
        tasks = [self._run_backend(b, brief) for b in self.backends]
        outcomes = await asyncio.gather(*tasks, return_exceptions=True)

        results: list[tuple[str, ResearchResult]] = []
        for backend, outcome in zip(self.backends, outcomes):
            if isinstance(outcome, Exception):
                logger.error("Backend %s failed: %s", backend.name, outcome)
            else:
                results.append(outcome)

        if not results:
            raise RuntimeError("All backends failed")

        return results

    async def _run_backend(
        self, backend: ResearchBackend, brief: ResearchBrief
    ) -> tuple[str, ResearchResult]:
        """Run a single backend and return (name, result)."""
        logger.info("Dispatching to %s", backend.name)
        result = await backend.research(brief.query, brief.sources)
        logger.info("Backend %s returned %d claims", backend.name, len(result.claims))
        return (backend.name, result)

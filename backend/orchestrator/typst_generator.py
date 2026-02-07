"""Typst generator — produces Typst source from a synthesized Report."""

from __future__ import annotations

from pathlib import Path

from backend.models.report import Citation, Conflict, Report

TEMPLATE_PATH = Path(__file__).resolve().parent.parent.parent / "typst" / "templates" / "report.typ"
CONTENT_MARKER = "// QUARRY:CONTENT"


class TypstGenerator:
    """Generates Typst source from a Report's citations and conflicts."""

    def __init__(self, template: str | None = None) -> None:
        if template is not None:
            self._template = template
        else:
            self._template = TEMPLATE_PATH.read_text()

    def generate(self, report: Report, query: str = "") -> str:
        """Produce a complete Typst document from a Report."""
        content_lines: list[str] = []

        # Import citation component
        content_lines.append('#import "../components/citation.typ": cite-inline, cite-entry')
        content_lines.append("")

        # Query heading
        if query:
            content_lines.append(f"= {self._escape(query)}")
            content_lines.append("")

        # Summary section with inline citations
        if report.citations:
            content_lines.append("== Findings")
            content_lines.append("")
            for i, citation in enumerate(report.citations, 1):
                content_lines.append(
                    f"{self._escape(citation.claim)}#cite-inline({i})"
                )
                content_lines.append("")

        # Conflicts
        if report.conflicts:
            content_lines.append("== Disputed Claims")
            content_lines.append("")
            for conflict in report.conflicts:
                content_lines.append(self._render_conflict(conflict))
                content_lines.append("")

        # Citation list
        if report.citations:
            content_lines.append("== Sources")
            content_lines.append("")
            for i, citation in enumerate(report.citations, 1):
                content_lines.append(self._render_citation_entry(i, citation))

        content = "\n".join(content_lines)
        return self._template.replace(CONTENT_MARKER, content)

    def _render_citation_entry(self, num: int, citation: Citation) -> str:
        """Render a single citation entry."""
        url_part = f', url: "{citation.underlying_url}"' if citation.underlying_url else ""
        return (
            f'#cite-entry({num}, '
            f'"{self._escape(citation.claim)}", '
            f'"{self._escape(citation.llm_source)}"'
            f"{url_part})"
        )

    def _render_conflict(self, conflict: Conflict) -> str:
        """Render a conflict box."""
        positions = []
        for pos in conflict.positions:
            entry = f'(source: "{self._escape(pos.llm_source)}", claim: "{self._escape(pos.claim)}")'
            positions.append(entry)
        positions_str = ", ".join(positions)

        resolution = "none"
        if conflict.resolution:
            resolution = f'"{self._escape(conflict.resolution)}"'

        return (
            f"#conflict-box(\n"
            f'  topic: "{self._escape(conflict.topic)}",\n'
            f"  positions: ({positions_str},),\n"
            f"  resolution: {resolution},\n"
            f")"
        )

    def _escape(self, text: str) -> str:
        """Escape special Typst characters in text."""
        # Backslash first, then quotes
        return text.replace("\\", "\\\\").replace('"', '\\"')

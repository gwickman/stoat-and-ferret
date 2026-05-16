"""Documentation hygiene tests preventing regression of known bad patterns."""

from __future__ import annotations

import pathlib

_DOCS_ROOT = pathlib.Path(__file__).parent.parent / "docs"
# Operator-facing manual documentation; design docs are excluded as historical artifacts.
_MANUAL_DOCS = _DOCS_ROOT / "manual"

# Maps doc filename → endpoint family for namespace assertion checks.
# "render"  → terminal status is "completed" (RenderStatus)
# "generic" → terminal status is "complete" (JobStatus for scan/proxy/waveform/thumbnail)
# "both"    → file mixes render and generic sections; per-section analysis applied
DOC_FAMILY: dict[str, str] = {
    "operator-guide.md": "render",
    "ai-integration-patterns.md": "both",  # Pattern 4 (Batch) is render; others are generic/mixed
    "ws-event-vocabulary.md": "generic",
    "prompt-recipes.md": "both",
}


def _check_lines(lines: list[tuple[int, str]], pattern: str) -> list[tuple[int, str]]:
    """Return (lineno, stripped_line) pairs where pattern appears."""
    return [(lineno, line.strip()) for lineno, line in lines if pattern in line]


def _split_sections(text: str) -> list[tuple[str, list[tuple[int, str]]]]:
    """Split text into (header, [(lineno, line)]) pairs at '## ' boundaries."""
    sections: list[tuple[str, list[tuple[int, str]]]] = []
    header = "__preamble__"
    current: list[tuple[int, str]] = []
    for i, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            sections.append((header, current))
            header = line
            current = []
        else:
            current.append((i, line))
    sections.append((header, current))
    return sections


def _section_family(header: str) -> str:
    """Classify a section header as 'render', 'generic', or 'mixed'.

    'batch' is treated as render because the codebase only has batch render
    workflows (POST /api/v1/render/batch), never batch scan.
    """
    h = header.lower()
    is_render = any(k in h for k in ("render", "batch"))
    is_generic = any(k in h for k in ("scan", "long-poll", "long poll", "async job"))
    if is_render and not is_generic:
        return "render"
    if is_generic and not is_render:
        return "generic"
    return "mixed"


def test_no_complete_status_literal_in_manual_docs() -> None:
    """Hygiene test: status tokens follow endpoint-family namespace conventions.

    The canonical JobStatus enum value is 'complete' (generic async jobs: scan,
    proxy, waveform, thumbnail). The canonical RenderStatus terminal value is
    'completed' (render jobs). Documentation must use the correct token per
    endpoint family. Unquoted bareword 'status == complete' is always wrong.
    Effect types 'fade' and 'brightness' are not in the live registry.
    """
    errors: list[str] = []

    for md_file in sorted(_MANUAL_DOCS.rglob("*.md")):
        fname = md_file.name
        text = md_file.read_text(encoding="utf-8")
        rel = str(md_file.relative_to(_DOCS_ROOT.parent))
        family = DOC_FAMILY.get(fname)
        lines: list[tuple[int, str]] = list(enumerate(text.splitlines(), 1))

        if family == "render":
            # Render docs must not use the generic 'complete' token in status position.
            for lineno, line in _check_lines(lines, '"status": "complete"'):
                errors.append(f"{rel}:{lineno}: render doc uses generic token 'complete': {line}")

        elif family == "generic":
            # Generic docs must not use the render 'completed' token in status position.
            for lineno, line in _check_lines(lines, '"status": "completed"'):
                errors.append(f"{rel}:{lineno}: generic doc uses render token 'completed': {line}")

        elif family == "both":
            # Per-section analysis for docs with both render and generic content.
            for sec_header, sec_lines in _split_sections(text):
                sf = _section_family(sec_header)
                if sf == "render":
                    for lineno, line in _check_lines(sec_lines, '"status": "complete"'):
                        errors.append(
                            f"{rel}:{lineno}: render section {sec_header!r} uses"
                            f" generic token 'complete': {line}"
                        )
                elif sf == "generic":
                    for lineno, line in _check_lines(sec_lines, '"status": "completed"'):
                        errors.append(
                            f"{rel}:{lineno}: generic section {sec_header!r} uses"
                            f" render token 'completed': {line}"
                        )

        # The following checks apply to all docs regardless of family classification.

        # Unquoted bareword 'status == complete' is always wrong (render uses "completed").
        for lineno, line in _check_lines(lines, "status == complete"):
            errors.append(f"{rel}:{lineno}: unquoted bareword 'status == complete': {line}")

        # Effect types 'fade' and 'brightness' are not in the live registry.
        for bad_effect in ('"effect_type": "fade"', '"effect_type": "brightness"'):
            for lineno, line in _check_lines(lines, bad_effect):
                errors.append(f"{rel}:{lineno}: banned effect type in example: {line}")

    assert not errors, "Documentation hygiene failures:\n" + "\n".join(errors)

"""Documentation hygiene tests preventing regression of known bad patterns."""

from __future__ import annotations

import pathlib

_DOCS_ROOT = pathlib.Path(__file__).parent.parent / "docs"
# Operator-facing manual documentation; design docs are excluded as historical artifacts.
_MANUAL_DOCS = _DOCS_ROOT / "manual"


def _check_lines(lines: list[tuple[int, str]], pattern: str) -> list[tuple[int, str]]:
    """Return (lineno, stripped_line) pairs where pattern appears."""
    return [(lineno, line.strip()) for lineno, line in lines if pattern in line]


def test_no_complete_status_literal_in_manual_docs() -> None:
    """Hygiene test: all job types now use a single terminal-success token "completed".

    Since BL-490, JobStatus.COMPLETED = "completed" unifies all job types (scan,
    proxy, waveform, thumbnail, render). No documentation should contain the stale
    "status": "complete" value. Unquoted bareword 'status == complete' is also wrong.
    Effect types 'fade' and 'brightness' are not in the live registry.
    """
    errors: list[str] = []

    for md_file in sorted(_MANUAL_DOCS.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        rel = str(md_file.relative_to(_DOCS_ROOT.parent))
        lines: list[tuple[int, str]] = list(enumerate(text.splitlines(), 1))

        # Stale terminal-success token: all job types now emit "completed".
        for lineno, line in _check_lines(lines, '"status": "complete"'):
            errors.append(f"{rel}:{lineno}: stale terminal status token 'complete': {line}")

        # Unquoted bareword form is always wrong.
        for lineno, line in _check_lines(lines, "status == complete"):
            errors.append(f"{rel}:{lineno}: unquoted bareword 'status == complete': {line}")

        # Effect types 'fade' and 'brightness' are not in the live registry.
        for bad_effect in ('"effect_type": "fade"', '"effect_type": "brightness"'):
            for lineno, line in _check_lines(lines, bad_effect):
                errors.append(f"{rel}:{lineno}: banned effect type in example: {line}")

    assert not errors, "Documentation hygiene failures:\n" + "\n".join(errors)

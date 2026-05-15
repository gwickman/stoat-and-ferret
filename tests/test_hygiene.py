"""Documentation hygiene tests preventing regression of known bad patterns."""

from __future__ import annotations

import pathlib

_DOCS_ROOT = pathlib.Path(__file__).parent.parent / "docs"
# Operator-facing manual documentation; design docs are excluded as historical artifacts.
_MANUAL_DOCS = _DOCS_ROOT / "manual"


def test_no_complete_status_literal_in_manual_docs() -> None:
    """Hygiene test: no markdown example uses the wrong 'complete' status token.

    The canonical JobStatus enum value is 'completed'. Documentation that uses
    'complete' causes silent integration breaks for operators polling job status.
    Scoped to docs/manual/ (operator-facing); docs/design/ contains historical
    design artifacts that pre-date the canonical enum and are excluded.
    """
    pattern = '"status": "complete"'
    matches: list[str] = []
    for md_file in sorted(_MANUAL_DOCS.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        if pattern in text:
            for i, line in enumerate(text.splitlines(), 1):
                if pattern in line:
                    matches.append(f"{md_file.relative_to(_DOCS_ROOT.parent)}:{i}: {line.strip()}")
    assert not matches, (
        'Found instances of wrong status token \'"status": "complete"\' in docs/manual/:\n'
        + "\n".join(matches)
    )

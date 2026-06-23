# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Documentation hygiene tests preventing regression of known bad patterns."""

from __future__ import annotations

import os
import pathlib

import pytest

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


def _check_clearance_note_structure(audit_doc: pathlib.Path) -> None:
    assert audit_doc.exists(), "docs/legal/relicense-ownership-audit.md must exist"
    content = audit_doc.read_text()
    required_headers = [
        "# Sole-ownership audit",
        "## Audited revision",
        "## Audit scope",
        "## Method",
        "## Conclusion",
        "## Exceptions",
        "## Signer + date",
        "## Authorisation",
    ]
    for header in required_headers:
        assert header in content, f"Required section header missing: {header}"
    lines = content.splitlines()
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped not in required_headers:
            continue
        heading_lvl = len(stripped) - len(stripped.lstrip("#"))
        # Section body extends to the next heading at same or higher level (or EOF)
        next_peer = next(
            (
                j
                for j in range(i + 1, len(lines))
                if lines[j].startswith("#")
                and (len(lines[j]) - len(lines[j].lstrip("#"))) <= heading_lvl
            ),
            len(lines),
        )
        body = "\n".join(lines[i + 1 : next_peer]).strip()
        assert body, f"Section '{stripped}' must not be empty"


# Structure-only validation — does not verify legal/provenance conclusions
def test_ownership_audit_clearance_note_structure() -> None:
    repo_root = pathlib.Path(__file__).parents[1]
    audit_doc = repo_root / "docs" / "legal" / "relicense-ownership-audit.md"
    _check_clearance_note_structure(audit_doc)


def test_ownership_audit_clearance_note_structure_bites(tmp_path: pathlib.Path) -> None:
    repo_root = pathlib.Path(__file__).parents[1]
    audit_doc = repo_root / "docs" / "legal" / "relicense-ownership-audit.md"
    content = audit_doc.read_text()
    malformed = content.replace("## Authorisation", "## REMOVED_SECTION")
    malformed_doc = tmp_path / "relicense-ownership-audit.md"
    malformed_doc.write_text(malformed)
    with pytest.raises(AssertionError, match="Required section header missing"):
        _check_clearance_note_structure(malformed_doc)


_REPO_ROOT = pathlib.Path(__file__).parents[1]

_AUTO_DEV_SENTINEL_NAMES = frozenset(
    {"IMPACT_ASSESSMENT.md", "handoff-template.md", "BACKLOG.md", "backlog.json"}
)


def _auto_dev_artifacts_present(repo_root: pathlib.Path) -> list[str]:
    """Return list of artifact violations; non-empty means auto-dev artefacts found."""
    violations: list[str] = []
    auto_dev_dir = repo_root / "docs" / "auto-dev"
    if auto_dev_dir.exists():
        violations.append(str(auto_dev_dir))
    for name in _AUTO_DEV_SENTINEL_NAMES:
        if (repo_root / name).exists():
            violations.append(str(repo_root / name))
        if (auto_dev_dir / name).exists():
            violations.append(str(auto_dev_dir / name))
    return violations


def test_no_auto_dev_artifacts_in_product_tree() -> None:
    violations = _auto_dev_artifacts_present(_REPO_ROOT)
    assert not violations, "docs/auto-dev/ artifacts found in product tree: " + str(violations)


def test_gitignore_blocks_auto_dev_dir() -> None:
    gitignore = _REPO_ROOT / ".gitignore"
    assert gitignore.exists()
    content = gitignore.read_text()
    assert "docs/auto-dev/" in content, ".gitignore must contain docs/auto-dev/ recurrence guard"


def test_agents_md_has_no_auto_dev_path_references() -> None:
    agents_md = _REPO_ROOT / "AGENTS.md"
    content = agents_md.read_text()
    assert "docs/auto-dev/handoff-template.md" not in content, (
        "AGENTS.md must not reference docs/auto-dev/handoff-template.md"
    )


def test_canonical_impact_assessment_has_license_header_section() -> None:
    artifacts_root = os.environ.get("STOAT_ARTIFACTS_ROOT")
    if not artifacts_root:
        pytest.skip("STOAT_ARTIFACTS_ROOT not set — skipping cross-repo check")
    impact_doc = pathlib.Path(artifacts_root) / "docs" / "auto-dev" / "IMPACT_ASSESSMENT.md"
    if not impact_doc.exists():
        pytest.skip(f"Canonical IMPACT_ASSESSMENT.md not found at {impact_doc}")
    content = impact_doc.read_text()
    assert "License Header Compliance (per-file SPDX)" in content, (
        "Canonical IMPACT_ASSESSMENT.md must contain License Header Compliance section"
    )


def test_no_auto_dev_artifacts_in_product_tree_bites(tmp_path: pathlib.Path) -> None:
    auto_dev_dir = tmp_path / "docs" / "auto-dev"
    auto_dev_dir.mkdir(parents=True)
    (auto_dev_dir / "IMPACT_ASSESSMENT.md").write_text("# test")
    violations = _auto_dev_artifacts_present(tmp_path)
    assert violations, "bite test: expected violations when docs/auto-dev/ recreated in tmp_path"

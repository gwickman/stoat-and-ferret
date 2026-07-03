# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Documentation hygiene tests preventing regression of known bad patterns."""

from __future__ import annotations

import os
import pathlib
import subprocess
from pathlib import Path

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


def test_orchestration_artifacts_not_tracked() -> None:
    """Orchestration runtime files must not be tracked in the git index."""
    result = subprocess.run(
        ["git", "ls-files", ".claude/scheduled_tasks.lock", "merge_result.txt"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, "git ls-files failed"
    assert result.stdout.strip() == "", (
        f"Orchestration artifacts are still tracked: {result.stdout.strip()}"
    )


def _active_gitignore_lines(content: str) -> list[str]:
    result = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            result.append(stripped)
    return result


def test_active_gitignore_lines_helper() -> None:
    assert _active_gitignore_lines("# comment\n\n# another\n") == []
    assert _active_gitignore_lines(".claude/*.lock\n# comment\n") == [".claude/*.lock"]
    assert ".claude/*.lock" not in _active_gitignore_lines("# .claude/*.lock\n# merge_result*.txt")
    assert ".claude/*.lock" in _active_gitignore_lines(".claude/*.lock\nmerge_result*.txt")


def test_orchestration_gitignore_guards_present() -> None:
    gitignore = Path(__file__).parent.parent / ".gitignore"
    content = gitignore.read_text(encoding="utf-8")
    active = _active_gitignore_lines(content)
    assert ".claude/*.lock" in active, ".claude/*.lock missing or commented out in .gitignore"
    assert "merge_result*.txt" in active, "merge_result*.txt missing or commented out in .gitignore"


def test_root_changelog_has_no_version_headings() -> None:
    """Root CHANGELOG.md must not contain ^## v section headings (redirect stub only)."""
    changelog = Path("CHANGELOG.md")
    if not changelog.exists():
        return  # No CHANGELOG.md at root is also acceptable
    content = changelog.read_text()
    version_headings = [line for line in content.splitlines() if line.startswith("## v")]
    assert version_headings == [], (
        f"Root CHANGELOG.md contains stale version headings: {version_headings[:3]}"
    )


def test_uat_baseline_failures_json_schema() -> None:
    """baseline-uat-failures.json must be valid JSON with required fields per entry."""
    import json

    registry_path = Path("tests/fixtures/baseline-uat-failures.json")
    assert registry_path.exists(), "baseline-uat-failures.json not found"
    entries = json.loads(registry_path.read_text())
    assert isinstance(entries, list), "Registry must be a JSON array"
    for entry in entries:
        assert isinstance(entry.get("journey_id"), int), f"journey_id must be int in entry: {entry}"
        assert isinstance(entry.get("reason"), str), f"reason must be str in entry: {entry}"
        assert isinstance(entry.get("tracking_reference"), str), (
            f"tracking_reference must be str in entry: {entry}"
        )


def test_no_http422_unprocessable_entity_in_src() -> None:
    """BL-545: HTTP_422_UNPROCESSABLE_ENTITY is deprecated in starlette 0.50+.

    All router files must use HTTP_422_UNPROCESSABLE_CONTENT instead.
    """
    src_root = _REPO_ROOT / "src"
    violations: list[str] = []
    for py_file in sorted(src_root.rglob("*.py")):
        text = py_file.read_text(encoding="utf-8")
        if "HTTP_422_UNPROCESSABLE_ENTITY" in text:
            rel = str(py_file.relative_to(_REPO_ROOT))
            violations.append(rel)
    assert not violations, (
        "Deprecated HTTP_422_UNPROCESSABLE_ENTITY found in src/ files: " + ", ".join(violations)
    )


def test_uat_baseline_stale_j502_j504_absent() -> None:
    """BL-590: J502/J504 fixed by BL-558; must not reappear in baseline-uat-failures.json."""
    import json

    registry_path = Path("tests/fixtures/baseline-uat-failures.json")
    entries = json.loads(registry_path.read_text())
    journey_ids = {entry["journey_id"] for entry in entries}
    assert 502 not in journey_ids, (
        "J502 is stale (fixed by BL-558) and must not be in baseline-uat-failures.json"
    )
    assert 504 not in journey_ids, (
        "J504 is stale (fixed by BL-558) and must not be in baseline-uat-failures.json"
    )

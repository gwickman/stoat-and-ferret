# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for UAT runner registry loading and annotation logic."""

from __future__ import annotations

import inspect
import json
import subprocess
from pathlib import Path

import pytest

from scripts.uat_runner import get_journey_annotation, load_known_failures, run_journey

# ---------------------------------------------------------------------------
# load_known_failures — unit tests
# ---------------------------------------------------------------------------


def test_load_valid_registry(tmp_path: pytest.TempPathFactory) -> None:
    """Valid bare-array registry file parses without exception and returns correct mapping."""
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(
        json.dumps([{"journey_id": 501, "reason": "test reason", "tracking_reference": "ref-001"}]),
        encoding="utf-8",
    )

    result = load_known_failures(str(registry_file))

    assert 501 in result
    assert result[501]["reason"] == "test reason"
    assert result[501]["tracking_reference"] == "ref-001"


def test_load_missing_registry() -> None:
    """Missing registry file returns empty dict (all failures annotated FAIL)."""
    result = load_known_failures("/nonexistent/path/registry.json")
    assert result == {}


def test_load_malformed_json(tmp_path: pytest.TempPathFactory) -> None:
    """Malformed JSON raises ValueError with descriptive message."""
    registry_file = tmp_path / "bad.json"
    registry_file.write_text("{invalid json}", encoding="utf-8")

    with pytest.raises(ValueError, match="Malformed registry"):
        load_known_failures(str(registry_file))


def test_load_non_list_top_level(tmp_path: pytest.TempPathFactory) -> None:
    """Non-list top-level value raises ValueError naming the canonical bare-array shape."""
    registry_file = tmp_path / "nokey.json"
    registry_file.write_text(json.dumps({"other": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="Expected bare JSON array"):
        load_known_failures(str(registry_file))


def test_load_invalid_journey_id(tmp_path: pytest.TempPathFactory) -> None:
    """Non-integer journey_id raises ValueError."""
    registry_file = tmp_path / "badid.json"
    registry_file.write_text(
        json.dumps([{"journey_id": "not_an_int", "reason": "test", "tracking_reference": "ref"}]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="journey_id must be integer"):
        load_known_failures(str(registry_file))


def test_load_missing_required_field(tmp_path: pytest.TempPathFactory) -> None:
    """Entry missing tracking_reference raises ValueError."""
    registry_file = tmp_path / "incomplete.json"
    registry_file.write_text(
        json.dumps([{"journey_id": 501, "reason": "test"}]),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing 'reason' or 'tracking_reference'"):
        load_known_failures(str(registry_file))


def test_load_empty_failures_list(tmp_path: pytest.TempPathFactory) -> None:
    """Empty bare-array registry returns empty dict."""
    registry_file = tmp_path / "empty.json"
    registry_file.write_text(json.dumps([]), encoding="utf-8")

    result = load_known_failures(str(registry_file))
    assert result == {}


# ---------------------------------------------------------------------------
# get_journey_annotation — unit tests covering all three annotation outcomes
# ---------------------------------------------------------------------------


def test_annotation_known_failure() -> None:
    """Journey in registry that fails → KNOWN_FAILURE."""
    known = {501: {"reason": "known issue", "tracking_reference": "ref"}}
    assert get_journey_annotation(501, "failed", known) == "KNOWN_FAILURE"


def test_annotation_unexpected_pass() -> None:
    """Journey in registry that passes → UNEXPECTED_PASS."""
    known = {501: {"reason": "known issue", "tracking_reference": "ref"}}
    assert get_journey_annotation(501, "passed", known) == "UNEXPECTED_PASS"


def test_annotation_fail_unknown_journey() -> None:
    """Journey not in registry that fails → FAIL (unchanged behavior)."""
    assert get_journey_annotation(201, "failed", {}) == "FAIL"


def test_annotation_pass_unknown_journey() -> None:
    """Journey not in registry that passes → PASS."""
    assert get_journey_annotation(201, "passed", {}) == "PASS"


# ---------------------------------------------------------------------------
# run_journey — timeout handling (BL-398)
# ---------------------------------------------------------------------------


def test_run_journey_timeout_returns_failed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """TimeoutExpired causes run_journey to return JourneyResult(status='failed')."""

    def mock_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(cmd=args[0] if args else [], timeout=900)

    monkeypatch.setattr("subprocess.run", mock_run)

    # Create fake script at the expected location: PROJECT_ROOT / "scripts" / "uat_journey_604.py"
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "uat_journey_604.py").write_text("", encoding="utf-8")

    import scripts.uat_runner as _runner

    original_root = _runner.PROJECT_ROOT
    monkeypatch.setattr(_runner, "PROJECT_ROOT", tmp_path)
    try:
        result = run_journey(journey_id=604, output_dir=tmp_path, headed=False)
    finally:
        monkeypatch.setattr(_runner, "PROJECT_ROOT", original_root)

    assert result.status == "failed"
    assert "timed out" in result.message.lower()


def test_run_journey_subprocess_run_has_timeout() -> None:
    """Static: run_journey() source must contain timeout= (BL-398 regression guard)."""
    source = inspect.getsource(run_journey)
    assert "timeout=" in source, "run_journey() subprocess.run must include timeout="


# ---------------------------------------------------------------------------
# R2 journey dispatch — BL-457
# ---------------------------------------------------------------------------

R2_JOURNEY_IDS = [701, 702, 703, 704, 705, 706, 707, 708, 709, 710]


def test_r2_journey_map_has_all_dispatch_entries() -> None:
    """JOURNEY_MODULE_MAP must contain entries for all R2 journey IDs 701-710 (BL-457-AC-1)."""
    from scripts.uat_runner import JOURNEY_MODULE_MAP

    for journey_id in R2_JOURNEY_IDS:
        assert journey_id in JOURNEY_MODULE_MAP, (
            f"Journey {journey_id} missing from JOURNEY_MODULE_MAP"
        )


def test_r2_journey_modules_resolve_to_actual_files() -> None:
    """Each R2 module in JOURNEY_MODULE_MAP must resolve to an existing file (BL-457-AC-1)."""
    import importlib.util

    from scripts.uat_runner import JOURNEY_MODULE_MAP

    for journey_id in R2_JOURNEY_IDS:
        module_path = JOURNEY_MODULE_MAP[journey_id]
        spec = importlib.util.find_spec(module_path)
        assert spec is not None, f"Module {module_path!r} for journey {journey_id} not importable"


def test_r2_qc_fail_has_playwright_assertions() -> None:
    """j_qc_fail.py must contain real Playwright expect() assertions (BL-457-AC-3).

    Reads the journey source as text rather than importing the module:
    importing j_qc_fail pulls in playwright at module level, which is not
    installed in the smoke-test CI environments.
    """
    journey_path = Path(__file__).parent.parent / "uat" / "journeys" / "j_qc_fail.py"
    source = journey_path.read_text(encoding="utf-8")
    assert "expect(" in source, "j_qc_fail must contain Playwright expect() assertions"
    assert "qc-status-fail" in source, "j_qc_fail must assert qc-status-fail element"
    assert "remaster-btn" in source, "j_qc_fail must assert remaster-btn element"


# ---------------------------------------------------------------------------
# run_journey — absent-journey non-pass behavior (BL-473)
# ---------------------------------------------------------------------------


def test_absent_journey_returns_not_implemented(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """run_journey() with no script and no module mapping returns not_implemented, never passed."""
    import scripts.uat_runner as _runner

    # Empty the module map so journey 999 has no dispatch target
    monkeypatch.setattr(_runner, "JOURNEY_MODULE_MAP", {})
    # Point PROJECT_ROOT at tmp_path so no uat_journey_999.py script exists
    monkeypatch.setattr(_runner, "PROJECT_ROOT", tmp_path)

    result = _runner.run_journey(journey_id=999, output_dir=tmp_path, headed=False)

    assert result.status != "passed", (
        f"Absent journey must not report 'passed', got {result.status!r}"
    )
    assert result.status == "not_implemented"


def test_absent_journey_excluded_from_passed_count(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A not_implemented journey result does not appear in the Passed count."""
    import scripts.uat_runner as _runner

    monkeypatch.setattr(_runner, "JOURNEY_MODULE_MAP", {})
    monkeypatch.setattr(_runner, "PROJECT_ROOT", tmp_path)

    result = _runner.run_journey(journey_id=999, output_dir=tmp_path, headed=False)
    assert result.status == "not_implemented"

    # print_summary must show Passed: 0 and Not Implemented: 1
    _runner.print_summary([result], tmp_path)
    captured = capsys.readouterr()
    assert "Passed: 0" in captured.out
    assert "Not Implemented: 1" in captured.out


# ---------------------------------------------------------------------------
# compute_exit_code — registered known failures do not block; others do
# ---------------------------------------------------------------------------


def _jr(journey_id: int, status: str) -> object:
    from scripts.uat_runner import JourneyResult

    return JourneyResult(journey_id=journey_id, status=status, message="")


def test_exit_code_zero_when_all_pass() -> None:
    from scripts.uat_runner import compute_exit_code

    assert compute_exit_code([_jr(701, "passed"), _jr(702, "passed")], {}) == 0


def test_exit_code_nonzero_on_unregistered_failure() -> None:
    from scripts.uat_runner import compute_exit_code

    assert compute_exit_code([_jr(701, "passed"), _jr(703, "failed")], {}) == 1


def test_exit_code_zero_when_failure_is_registered_known_failure() -> None:
    """A failure registered in the known-failure registry (with tracking ref) does not block."""
    from scripts.uat_runner import compute_exit_code

    known = {703: {"reason": "GUI not built", "tracking_reference": "BL-480"}}
    assert compute_exit_code([_jr(701, "passed"), _jr(703, "failed")], known) == 0


def test_exit_code_nonzero_for_not_implemented_even_when_registered() -> None:
    """A not-run journey is never success (BL-473) — registry does not exempt it."""
    from scripts.uat_runner import compute_exit_code

    known = {705: {"reason": "x", "tracking_reference": "BL-480"}}
    assert compute_exit_code([_jr(705, "not_implemented")], known) == 1


def test_exit_code_nonzero_when_only_some_failures_registered() -> None:
    from scripts.uat_runner import compute_exit_code

    known = {703: {"reason": "x", "tracking_reference": "BL-480"}}
    results = [_jr(703, "failed"), _jr(704, "failed")]
    assert compute_exit_code(results, known) == 1

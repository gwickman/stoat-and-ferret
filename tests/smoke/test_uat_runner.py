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
    """Valid registry file parses without exception and returns correct mapping."""
    registry_file = tmp_path / "registry.json"
    registry_file.write_text(
        json.dumps(
            {
                "failures": [
                    {"journey_id": 501, "reason": "test reason", "tracking_reference": "ref-001"}
                ]
            }
        ),
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


def test_load_missing_failures_key(tmp_path: pytest.TempPathFactory) -> None:
    """Registry without 'failures' key raises ValueError."""
    registry_file = tmp_path / "nokey.json"
    registry_file.write_text(json.dumps({"other": []}), encoding="utf-8")

    with pytest.raises(ValueError, match="must contain 'failures'"):
        load_known_failures(str(registry_file))


def test_load_invalid_journey_id(tmp_path: pytest.TempPathFactory) -> None:
    """Non-integer journey_id raises ValueError."""
    registry_file = tmp_path / "badid.json"
    registry_file.write_text(
        json.dumps(
            {
                "failures": [
                    {"journey_id": "not_an_int", "reason": "test", "tracking_reference": "ref"}
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="journey_id must be integer"):
        load_known_failures(str(registry_file))


def test_load_missing_required_field(tmp_path: pytest.TempPathFactory) -> None:
    """Entry missing tracking_reference raises ValueError."""
    registry_file = tmp_path / "incomplete.json"
    registry_file.write_text(
        json.dumps({"failures": [{"journey_id": 501, "reason": "test"}]}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing 'reason' or 'tracking_reference'"):
        load_known_failures(str(registry_file))


def test_load_empty_failures_list(tmp_path: pytest.TempPathFactory) -> None:
    """Registry with empty failures list returns empty dict."""
    registry_file = tmp_path / "empty.json"
    registry_file.write_text(json.dumps({"failures": []}), encoding="utf-8")

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

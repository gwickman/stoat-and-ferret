# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Regression test: JOURNEY_NAMES values match JOURNEY_NAME constants in journey scripts."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"


def test_journey_names_match_script_constants(monkeypatch: pytest.MonkeyPatch) -> None:
    """Assert every JOURNEY_NAMES entry matches its script's JOURNEY_NAME constant."""
    monkeypatch.syspath_prepend(str(SCRIPTS_DIR.parent))
    from scripts.uat_runner import JOURNEY_NAMES  # type: ignore[import]

    mismatches: list[str] = []
    for journey_id, expected_name in JOURNEY_NAMES.items():
        script_path = SCRIPTS_DIR / f"uat_journey_{journey_id}.py"
        if not script_path.exists():
            continue
        source = script_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        journey_name_value: str | None = None
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Assign)
                and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)
                and node.targets[0].id == "JOURNEY_NAME"
                and isinstance(node.value, ast.Constant)
            ):
                journey_name_value = str(node.value.value)
                break
        if journey_name_value is not None and journey_name_value != expected_name:
            mismatches.append(
                f"Journey {journey_id}: JOURNEY_NAMES={expected_name!r} != "
                f"script JOURNEY_NAME={journey_name_value!r}"
            )
    assert not mismatches, "\n".join(mismatches)


def test_journey_fails_under_pythonoptimize(tmp_path: Path) -> None:
    """Verify that converted if/raise checks survive PYTHONOPTIMIZE=1.

    When -O is used, bare assert is elided; if/raise still executes.
    Forces a step to fail via UAT_SERVER_URL=http://localhost:0 and
    confirms the journey exits non-zero with steps_failed >= 1.
    """
    pytest.importorskip("playwright")

    uat_out = tmp_path / "uat-out"
    env = os.environ.copy()
    env["PYTHONOPTIMIZE"] = "1"
    env["UAT_SERVER_URL"] = "http://localhost:0"
    env["UAT_OUTPUT_DIR"] = str(uat_out)

    result = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "uat_journey_501.py")],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 1, (
        f"Expected exit 1 under PYTHONOPTIMIZE=1, got {result.returncode}.\n"
        f"stdout: {result.stdout[:500]}"
    )

    # Verify steps_failed >= 1 from JSON result file or stdout
    result_file = uat_out / "render-export-journey" / "journey_result.json"
    if result_file.exists():
        data = json.loads(result_file.read_text(encoding="utf-8"))
        assert data.get("steps_failed", 0) >= 1, (
            f"Expected steps_failed >= 1 in result JSON, got: {data}"
        )
    else:
        assert "FAILED" in result.stdout or "FAILED" in result.stderr, (
            f"Expected FAILED step in output. stdout: {result.stdout[:500]}"
        )

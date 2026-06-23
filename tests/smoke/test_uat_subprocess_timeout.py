# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Regression test: every subprocess.run in UAT journeys has a timeout= argument."""

from __future__ import annotations

import ast
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"


def test_all_journey_subprocess_run_have_timeout() -> None:
    """Assert every subprocess.run call in uat_journey_*.py files has a timeout= kwarg."""
    journey_scripts = sorted(SCRIPTS_DIR.glob("uat_journey_*.py"))
    assert journey_scripts, f"No journey scripts found under {SCRIPTS_DIR}"

    violations: list[str] = []
    for script_path in journey_scripts:
        source = script_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr == "run"
                and isinstance(node.func.value, ast.Name)
                and node.func.value.id == "subprocess"
            ):
                continue
            has_timeout = any(
                isinstance(kw, ast.keyword) and kw.arg == "timeout" for kw in node.keywords
            )
            if not has_timeout:
                violations.append(
                    f"{script_path.name}:{node.lineno}: subprocess.run missing timeout="
                )
    assert not violations, "\n".join(violations)

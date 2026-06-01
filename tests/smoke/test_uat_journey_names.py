"""Regression test: JOURNEY_NAMES values match JOURNEY_NAME constants in journey scripts."""

from __future__ import annotations

import ast
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"


def test_journey_names_match_script_constants() -> None:
    """Assert every JOURNEY_NAMES entry matches its script's JOURNEY_NAME constant."""
    import sys

    sys.path.insert(0, str(SCRIPTS_DIR.parent))
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

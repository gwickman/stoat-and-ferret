"""Guard: every effect type in EXPECTED_EFFECT_TYPES must have a STOAT_TEST_FFMPEG-gated test."""

from __future__ import annotations

import ast
from pathlib import Path

# Path to the authoritative effect-type registry
_TEST_EFFECTS = Path(__file__).parents[1] / "test_api" / "test_effects.py"

# Effect types that predate the BL-503 DoD policy and do not yet have a dedicated
# STOAT_TEST_FFMPEG-gated contract test. Each entry here represents a known gap;
# new effect types added after this policy MUST NOT be added to this set — they must
# ship with a gated test in the same PR.
# See: docs/setup/smoke-test-harness-guide/07-dsp-contract-tests.md
_LEGACY_UNCOVERED_TYPES: frozenset[str] = frozenset(
    {
        "audio_mix",  # BL-503: predates policy; discharge test TBD
    }
)


def _load_expected_effect_types() -> set[str]:
    """Parse EXPECTED_EFFECT_TYPES from test_effects.py without importing it."""
    tree = ast.parse(_TEST_EFFECTS.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "EXPECTED_EFFECT_TYPES":
                    return {
                        elt.value
                        for elt in ast.walk(node.value)
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    }
    return set()


def _find_gated_effect_types() -> set[str]:
    """Return set of effect types that appear in a STOAT_TEST_FFMPEG-gated test file."""
    tests_root = Path(__file__).parents[1]
    expected = _load_expected_effect_types()
    covered: set[str] = set()
    for py_file in tests_root.rglob("*.py"):
        content = py_file.read_text(errors="replace")
        if "STOAT_TEST_FFMPEG" not in content:
            continue
        for effect_type in expected:
            if effect_type in content:
                covered.add(effect_type)
    return covered


def test_every_effect_type_has_gated_contract_test() -> None:
    """Every effect type in EXPECTED_EFFECT_TYPES must have a STOAT_TEST_FFMPEG-gated test."""
    expected = _load_expected_effect_types()
    assert expected, "EXPECTED_EFFECT_TYPES must not be empty"

    covered = _find_gated_effect_types()
    # Exclude legacy types that predate the policy from the enforcement check.
    enforceable = expected - _LEGACY_UNCOVERED_TYPES
    missing = sorted(enforceable - covered)

    assert not missing, (
        f"Effect types with no STOAT_TEST_FFMPEG-gated contract test: {missing}\n"
        "Add a gated contract test before registering a new effect builder (BL-503 DoD policy)."
    )

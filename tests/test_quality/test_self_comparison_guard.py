# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Guard: detect attribute self-comparison (A.x == A.x) — the BL-646 pattern missed by PLR0124."""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path


def _is_attr_self_comparison(node: ast.Compare) -> bool:
    """Return True if node is A.x == A.x (same obj.attr on both sides)."""
    if len(node.ops) != 1 or not isinstance(node.ops[0], ast.Eq):
        return False
    left = node.left
    if not (isinstance(left, ast.Attribute) and len(node.comparators) == 1):
        return False
    comp = node.comparators[0]
    if not isinstance(comp, ast.Attribute):
        return False
    # Same attribute name AND same value node type+name
    if left.attr != comp.attr:
        return False
    if not (isinstance(left.value, ast.Name) and isinstance(comp.value, ast.Name)):
        return False
    return left.value.id == comp.value.id


def find_attr_self_comparisons(source: str, filename: str) -> list[tuple[int, str]]:
    """Return list of (line, code_snippet) for attribute self-comparisons found."""
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError as e:
        raise SyntaxError(f"SyntaxError in {filename}: {e}") from e
    results = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and _is_attr_self_comparison(node):
            results.append((node.lineno, ast.unparse(node)))
    return results


def test_flags_attribute_self_comparison() -> None:
    """Positive case: TransitionType.Fade == TransitionType.Fade is flagged."""
    source = textwrap.dedent("""
        class TransitionType:
            Fade = "fade"
        result = TransitionType.Fade == TransitionType.Fade  # BL-646 pattern
    """)
    hits = find_attr_self_comparisons(source, "<test>")
    assert len(hits) == 1, f"Expected 1 hit, got {hits}"


def test_does_not_flag_different_attrs() -> None:
    """Negative case: TransitionType.Fade == TransitionType.Dissolve is NOT flagged."""
    source = textwrap.dedent("""
        class TransitionType:
            Fade = "fade"
            Dissolve = "dissolve"
        result = TransitionType.Fade == TransitionType.Dissolve  # legitimate
    """)
    hits = find_attr_self_comparisons(source, "<test>")
    assert len(hits) == 0, f"Expected 0 hits, got {hits}"


def test_no_attribute_self_comparisons_in_codebase() -> None:
    """No A.x == A.x patterns exist in src/ or tests/."""
    repo_root = Path(__file__).parent.parent.parent
    violations: list[str] = []
    for py_file in repo_root.glob("**/*.py"):
        if any(part.startswith(".") for part in py_file.parts):
            continue
        source = py_file.read_text(encoding="utf-8")
        hits = find_attr_self_comparisons(source, str(py_file))
        for lineno, snippet in hits:
            violations.append(f"{py_file.relative_to(repo_root)}:{lineno}: {snippet}")
    assert not violations, "Attribute self-comparisons found:\n" + "\n".join(violations)

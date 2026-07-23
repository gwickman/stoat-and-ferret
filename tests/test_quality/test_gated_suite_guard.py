# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""BL-691: gated-suite quality guard.

Statically scans tests/ for any def test_* function that directly invokes
subprocess.run(['ffmpeg',...]) or subprocess.run(['ffprobe',...]) without a
STOAT_TEST_FFMPEG skip guard.

Accepted guard forms:
  @pytest.mark.skipif(...STOAT_TEST_FFMPEG...)  -- direct skipif with env var
  @_FFMPEG_TESTS / @_requires_ffmpeg / @_FFMPEG_SKIP / @_FFMPEG_GATE
      (any variable decorator whose name contains 'ffmpeg', case-insensitive)
  pytestmark = pytest.mark.skipif(...STOAT_TEST_FFMPEG...)
      (module-level pytestmark assignment -- guards all tests in that file)
  class-level decorator propagating to methods

This test runs in the standard CI matrix (no STOAT_TEST_FFMPEG required).
"""

from __future__ import annotations

import ast
from pathlib import Path

# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _has_ffmpeg_subprocess_call(func_node: ast.FunctionDef) -> bool:
    """True if the function body directly invokes subprocess.run(['ffmpeg'|'ffprobe',...])."""
    for node in ast.walk(func_node):
        if isinstance(node, ast.Call):
            func = node.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "run"
                and isinstance(func.value, ast.Name)
                and func.value.id == "subprocess"
                and node.args
                and isinstance(node.args[0], ast.List)
            ):
                first = node.args[0]
                if (
                    first.elts
                    and isinstance(first.elts[0], ast.Constant)
                    and first.elts[0].value in ("ffmpeg", "ffprobe")
                ):
                    return True
    return False


def _decorators_have_ffmpeg_guard(decorator_list: list[ast.expr]) -> bool:
    """True if any decorator in the list is an FFmpeg skip guard.

    Accepts both:
    - @pytest.mark.skipif(...STOAT_TEST_FFMPEG...) -- direct skipif
    - Variable decorators whose name contains 'ffmpeg' (case-insensitive), e.g.
      @_FFMPEG_TESTS, @_requires_ffmpeg, @_FFMPEG_SKIP, @_FFMPEG_GATE
    """
    for deco in decorator_list:
        deco_src = ast.unparse(deco)
        if "skipif" in deco_src and "STOAT_TEST_FFMPEG" in deco_src:
            return True
        if "ffmpeg" in deco_src.lower():
            return True
    return False


def _module_pytestmark_has_ffmpeg_guard(tree: ast.Module) -> bool:
    """True if the module assigns pytestmark to a skipif containing STOAT_TEST_FFMPEG.

    Handles both single marks and list-of-marks:
      pytestmark = pytest.mark.skipif(not STOAT_TEST_FFMPEG, ...)
      pytestmark = [pytest.mark.skipif(not STOAT_TEST_FFMPEG, ...), ...]
    """
    for stmt in ast.iter_child_nodes(tree):
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if (
                    isinstance(target, ast.Name)
                    and target.id == "pytestmark"
                    and "STOAT_TEST_FFMPEG" in ast.unparse(stmt.value)
                ):
                    return True
    return False


def _check_file(py_file: Path) -> list[str]:
    """Return violation strings for ungated ffmpeg test functions in py_file."""
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    violations: list[str] = []
    module_guarded = _module_pytestmark_has_ffmpeg_guard(tree)

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_"):
            if (
                _has_ffmpeg_subprocess_call(node)
                and not module_guarded
                and not _decorators_have_ffmpeg_guard(node.decorator_list)
            ):
                violations.append(f"{py_file}::{node.name} (line {node.lineno})")

        elif isinstance(node, ast.ClassDef):
            class_guarded = module_guarded or _decorators_have_ffmpeg_guard(node.decorator_list)
            for child in ast.iter_child_nodes(node):
                if (
                    isinstance(child, ast.FunctionDef)
                    and child.name.startswith("test_")
                    and _has_ffmpeg_subprocess_call(child)
                    and not class_guarded
                    and not _decorators_have_ffmpeg_guard(child.decorator_list)
                ):
                    violations.append(f"{py_file}::{node.name}::{child.name} (line {child.lineno})")

    return violations


def find_ungated_ffmpeg_tests(tests_root: Path) -> list[str]:
    """Scan tests_root recursively and return violations."""
    violations: list[str] = []
    for py_file in sorted(tests_root.rglob("*.py")):
        violations.extend(_check_file(py_file))
    return violations


def _is_bare_pass_body(func_node: ast.FunctionDef) -> bool:
    """Return True if the function body consists only of pass statements and/or docstrings."""
    for stmt in func_node.body:
        if isinstance(stmt, ast.Pass):
            continue
        if (
            isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue  # docstring
        return False
    return True


# ---------------------------------------------------------------------------
# Policy tests
# ---------------------------------------------------------------------------


def test_all_ffmpeg_tests_are_gated() -> None:
    """BL-691-AC-1: every test_ invoking ffmpeg/ffprobe must have a STOAT_TEST_FFMPEG guard."""
    tests_root = Path(__file__).parent.parent  # tests/
    violations = find_ungated_ffmpeg_tests(tests_root)
    assert not violations, (
        "Found FFmpeg-invoking test functions missing STOAT_TEST_FFMPEG skip guard:\n"
        + "\n".join(f"  {v}" for v in violations)
    )


def test_bare_pass_gated_tests_are_flagged() -> None:
    """BL-691-AC-2: any FFmpeg-gated test_ with a bare-pass body is flagged."""
    # Positive case: bare-pass gated test IS detected
    positive_src = """
import pytest
STOAT_TEST_FFMPEG = True
@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="needs ffmpeg")
def test_fake_ffmpeg_bare_pass():
    pass
"""
    tree = ast.parse(positive_src)
    bare_found = any(
        _is_bare_pass_body(n) and _decorators_have_ffmpeg_guard(n.decorator_list)
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    )
    assert bare_found, "Positive case: bare-pass gated test was NOT detected by the guard"

    # Negative case: gated test with a real assertion is NOT flagged
    negative_src = """
import pytest
STOAT_TEST_FFMPEG = True
@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="needs ffmpeg")
def test_fake_ffmpeg_with_assertion():
    assert 1 + 1 == 2
"""
    tree2 = ast.parse(negative_src)
    bare_in_negative = any(
        _is_bare_pass_body(n) and _decorators_have_ffmpeg_guard(n.decorator_list)
        for n in ast.walk(tree2)
        if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
    )
    assert not bare_in_negative, "Negative case: guard falsely flagged a test with a real assertion"

    # Real scan: walk all test files for bare-pass gated tests
    tests_root = Path(__file__).parent.parent  # tests/
    bare_pass_culprits: list[str] = []
    for py_file in sorted(tests_root.rglob("test_*.py")):
        try:
            source = py_file.read_text(encoding="utf-8")
            tree3 = ast.parse(source)
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree3):
            if (
                isinstance(node, ast.FunctionDef)
                and node.name.startswith("test_")
                and _decorators_have_ffmpeg_guard(node.decorator_list)
                and _is_bare_pass_body(node)
            ):
                bare_pass_culprits.append(f"{py_file.relative_to(tests_root.parent)}::{node.name}")
    assert not bare_pass_culprits, "Bare-pass gated tests found (BL-691 guard):\n" + "\n".join(
        f"  {c}" for c in bare_pass_culprits
    )

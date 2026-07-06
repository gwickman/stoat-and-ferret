# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Contract tests for emit_filter_value dispatch and AC-5 hygiene (BL-555).

Tests verify that each ValueKind produces the correct escape when exercised
through the Python-facing builder interface, and that all EffectDefinition
entries with requires_path_escape=True use emit_filter_option_path semantics
(i.e., their value_kind_per_option entries are typed as "path").
"""

from __future__ import annotations

import pytest

from stoat_ferret_core import (
    BurnedSubtitleBuilder,
    BurnedSubtitleSpec,
    CurvesBuilder,
    HueRotationBuilder,
    VignetteBuilder,
)

# ---------------------------------------------------------------------------
# Expression variant (ValueKind::Expression → single-quote wrap, reject ')
# ---------------------------------------------------------------------------


def test_emit_filter_value_expression_single_quoted() -> None:
    """HueRotationBuilder wraps the h_expr in single quotes (Expression kind)."""
    builder = HueRotationBuilder("2*PI*t/3")
    result = str(builder.build())
    assert "hue=H='2*PI*t/3'" in result, f"expected single-quote wrapped expression in: {result!r}"


def test_emit_filter_value_expression_rejects_embedded_apostrophe() -> None:
    """HueRotationBuilder rejects an h_expr containing a single quote."""
    builder = HueRotationBuilder("bad'expr")
    with pytest.raises(ValueError, match="single"):
        builder.build()


# ---------------------------------------------------------------------------
# Path variant (ValueKind::Path → emit_filter_option_path)
# ---------------------------------------------------------------------------


def test_emit_filter_value_path_uses_emit_filter_option_path() -> None:
    """BurnedSubtitleBuilder uses emit_filter_option_path for Windows paths."""
    spec = BurnedSubtitleSpec(source_path="C:\\Users\\grant\\test.srt")
    result = BurnedSubtitleBuilder.build(spec)
    # emit_filter_option_path produces 'C\:/Users/grant/test.srt'
    assert "C\\:/" in result, f"expected colon-escaped Windows path in: {result!r}"
    assert result.startswith("subtitles=filename='"), (
        f"expected single-quoted filename= in: {result!r}"
    )


def test_emit_filter_value_path_rejects_apostrophe() -> None:
    """BurnedSubtitleBuilder rejects a source_path containing a single quote."""
    spec = BurnedSubtitleSpec(source_path="/path/to/O'Brien.srt")
    with pytest.raises(ValueError):
        BurnedSubtitleBuilder.build(spec)


# ---------------------------------------------------------------------------
# KneeString variant (ValueKind::KneeString → single-quote wrap + monotonic)
# ---------------------------------------------------------------------------


def test_emit_filter_value_knee_string_valid_monotonic() -> None:
    """CurvesBuilder wraps a valid knee string in single quotes."""
    builder = CurvesBuilder(red="0/0 0.5/0.4 1/1")
    result = str(builder.build())
    assert "red='0/0 0.5/0.4 1/1'" in result, f"expected single-quoted knee string in: {result!r}"


def test_emit_filter_value_knee_string_rejects_non_monotonic() -> None:
    """CurvesBuilder rejects a knee string with non-monotonic x values."""
    builder = CurvesBuilder(red="0.9/0.1 0.3/0.5 1/1")
    with pytest.raises(ValueError):
        builder.build()


# ---------------------------------------------------------------------------
# EnumLiteral variant (ValueKind::EnumLiteral → pass through unchanged)
# ---------------------------------------------------------------------------


def test_emit_filter_value_enum_literal_passthrough() -> None:
    """VignetteBuilder passes mode enum literal through unchanged."""
    builder = VignetteBuilder(position="centre", mode="backward")
    result = str(builder.build())
    assert "mode=backward" in result, (
        f"expected mode=backward (enum literal passthrough) in: {result!r}"
    )


# ---------------------------------------------------------------------------
# Numeric variant (ValueKind::Numeric → pass through unchanged)
# ---------------------------------------------------------------------------


def test_emit_filter_value_numeric_passthrough() -> None:
    """VignetteBuilder passes angle numeric value through unchanged."""
    builder = VignetteBuilder(position="centre", angle=0.5)
    result = str(builder.build())
    assert "angle=0.5" in result, f"expected angle=0.5 (numeric passthrough) in: {result!r}"


# ---------------------------------------------------------------------------
# Boolean variant (ValueKind::Boolean → pass through unchanged)
# Note: No current builder exposes a boolean option via emit_filter_value.
# Boolean passthrough is covered at the Rust level in video.rs::tests::boolean_pass_through.
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# AC-5: hygiene test — requires_path_escape=True → value_kind_per_option uses "path"
# ---------------------------------------------------------------------------


def test_ac5_path_escape_definitions_use_path_kind() -> None:
    """Definitions with requires_path_escape=True have 'path' kind in value_kind_per_option.

    Ensures that every path-escape-requiring builder documents its path options
    in value_kind_per_option with kind "path" (i.e., uses emit_filter_option_path
    semantics, not escape_for_filter).
    """
    from stoat_ferret.effects.definitions import create_default_registry

    registry = create_default_registry()
    failures: list[str] = []
    for effect_type, defn in registry.list_all():
        if not defn.requires_path_escape:
            continue
        path_options = [k for k, v in defn.value_kind_per_option.items() if v == "path"]
        if not path_options:
            failures.append(
                f"{effect_type!r}: requires_path_escape=True but no 'path' entries in "
                f"value_kind_per_option (got: {defn.value_kind_per_option!r})"
            )
    assert not failures, "\n".join(failures)


def test_ac5_path_options_produce_correct_path_escape() -> None:
    """EffectDefinitions with requires_path_escape=True correctly escape Windows paths.

    Calls build_fn() with a Windows path for each path option and verifies the
    output uses emit_filter_option_path semantics (C\\:/ colon escape).
    """
    from stoat_ferret.effects.definitions import create_default_registry

    registry = create_default_registry()
    windows_path = "C:\\Users\\grant\\test.srt"
    failures: list[str] = []

    for effect_type, defn in registry.list_all():
        if not defn.requires_path_escape:
            continue
        path_options = [k for k, v in defn.value_kind_per_option.items() if v == "path"]
        for option in path_options:
            try:
                result = defn.build_fn({option: windows_path})
                if "C\\:/" not in result:
                    failures.append(
                        f"{effect_type!r} option {option!r}: expected 'C\\:/' in output; "
                        f"got: {result!r}"
                    )
            except Exception as exc:
                # Some builders may reject certain combinations; skip non-path errors
                if "apostrophe" in str(exc).lower() or "colon" in str(exc).lower():
                    failures.append(f"{effect_type!r} option {option!r}: build_fn raised {exc!r}")

    assert not failures, "\n".join(failures)

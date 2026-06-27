# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Hygiene test: cross-checks EffectDefinition.timeline_T_capable against FFmpeg T flag.

For every EffectDefinition that declares timeline_T_capable=True, this test
verifies that the corresponding FFmpeg filter has the T (timeline) flag set.

If FFmpeg is not installed, all checks are skipped (not failed).

Per v088 scope: no existing builder sets timeline_T_capable=True, so all
timeline_T_capable-related assertions pass vacuously in non-FFmpeg environments.
"""

from __future__ import annotations

import shutil
import subprocess

import pytest

from stoat_ferret.effects.definitions import create_default_registry


def _ffmpeg_available() -> bool:
    """Return True if the ffmpeg binary is on PATH."""
    return shutil.which("ffmpeg") is not None


def _get_filter_flags(filter_name: str) -> set[str]:
    """Return the set of single-char flags for a filter from `ffmpeg -filters`.

    Output line format:
      [flags] <name>               <description>
    where flags is e.g. "VSC" (V=video, S=slice, C=command-capable).
    The T flag means timeline (enable expression) support.

    Returns an empty set if the filter is not found.
    """
    result = subprocess.run(
        ["ffmpeg", "-filters", "-hide_banner"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    for line in result.stdout.splitlines():
        parts = line.strip().split(None, 2)
        if len(parts) >= 2 and parts[1] == filter_name:
            return set(parts[0])
    return set()


@pytest.mark.skipif(not _ffmpeg_available(), reason="ffmpeg not installed")
def test_timeline_T_capable_agrees_with_ffmpeg_T_flag() -> None:
    """Builders declaring timeline_T_capable=True must have the FFmpeg T flag."""
    registry = create_default_registry()
    all_effects = registry.list_all()
    assert all_effects, "Expected at least one effect in registry"

    failures: list[str] = []
    for effect_type, definition in all_effects:
        if not definition.timeline_T_capable:
            continue
        # Extract the filter name from the preview string.
        preview = definition.preview_fn()
        filter_name = preview.split("=")[0].split(",")[-1].strip()
        flags = _get_filter_flags(filter_name)
        if "T" not in flags:
            failures.append(
                f"{effect_type}: timeline_T_capable=True but filter '{filter_name}' "
                f"lacks the T flag (flags: {sorted(flags)})"
            )

    assert not failures, (
        "EffectDefinition.timeline_T_capable mismatch with FFmpeg T flag:\n"
        + "\n".join(f"  - {f}" for f in failures)
    )


def test_wave3a_t_capable_builders_curves_hue_rotation_vignette() -> None:
    """Feature 004: final T-capable Wave 3a builders; assert exactly curves, hue_rotation, vignette.

    Finalizes the Wave 3a T-capable assertion (BL-510).
    """
    registry = create_default_registry()
    t_capable = [etype for etype, defn in registry.list_all() if defn.timeline_T_capable]
    assert sorted(t_capable) == ["curves", "hue_rotation", "vignette"]

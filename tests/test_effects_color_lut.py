# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for ColorLutBuilder and color_lut effect definition (BL-450)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from stoat_ferret.effects.definitions import COLOR_LUT, _build_color_lut, create_default_registry
from stoat_ferret_core import ColorLutBuilder

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")


# ---------------------------------------------------------------------------
# ColorLutBuilder unit tests (BL-450-AC-1)
# ---------------------------------------------------------------------------


def test_color_lut_valid_preset_calming_teal() -> None:
    """ColorLutBuilder accepts 'calming_teal' preset."""
    builder = ColorLutBuilder("calming_teal")
    assert builder.preset_name() == "calming_teal"


def test_color_lut_valid_preset_warm_fade() -> None:
    """ColorLutBuilder accepts 'warm_fade' preset."""
    builder = ColorLutBuilder("warm_fade")
    assert builder.preset_name() == "warm_fade"


def test_color_lut_valid_preset_identity() -> None:
    """ColorLutBuilder accepts 'identity' preset."""
    builder = ColorLutBuilder("identity")
    assert builder.preset_name() == "identity"


def test_color_lut_invalid_preset_raises() -> None:
    """ColorLutBuilder raises ValueError for unrecognised preset."""
    with pytest.raises((ValueError, Exception)):
        ColorLutBuilder("unknown")
    with pytest.raises((ValueError, Exception)):
        ColorLutBuilder("")


def test_color_lut_build_produces_lut3d_filter() -> None:
    """ColorLutBuilder.build() produces lut3d=file=<preset>.cube."""
    f = ColorLutBuilder("identity").build()
    s = str(f)
    assert s.startswith("lut3d="), f"Expected lut3d filter, got: {s}"
    assert "identity.cube" in s, f"Expected identity.cube in: {s}"


def test_color_lut_build_preset_name_in_filter() -> None:
    """build() includes the preset name as the file parameter."""
    for preset in ("calming_teal", "warm_fade", "identity"):
        f = ColorLutBuilder(preset).build()
        s = str(f)
        assert f"{preset}.cube" in s, f"Expected {preset}.cube in: {s}"


def test_color_lut_build_deterministic() -> None:
    """Two calls with the same preset produce identical filter strings."""
    b1 = ColorLutBuilder("identity")
    b2 = ColorLutBuilder("identity")
    assert str(b1.build()) == str(b2.build())


def test_color_lut_preset_name_getter() -> None:
    """preset_name() returns the validated preset name."""
    assert ColorLutBuilder("calming_teal").preset_name() == "calming_teal"
    assert ColorLutBuilder("warm_fade").preset_name() == "warm_fade"
    assert ColorLutBuilder("identity").preset_name() == "identity"


# ---------------------------------------------------------------------------
# Effect definition structure (BL-450-AC-2)
# ---------------------------------------------------------------------------


def test_color_lut_effect_registered_in_default_registry() -> None:
    """color_lut effect is registered in create_default_registry()."""
    registry = create_default_registry()
    definition = registry.get("color_lut")
    assert definition is not None


def test_color_lut_effect_definition_is_color_lut() -> None:
    """The registered definition is the COLOR_LUT EffectDefinition."""
    registry = create_default_registry()
    definition = registry.get("color_lut")
    assert definition is COLOR_LUT


def test_color_lut_effect_has_preset_schema() -> None:
    """color_lut schema has a 'preset' property with enum of known names."""
    schema = COLOR_LUT.parameter_schema
    assert schema["type"] == "object"
    props = schema["properties"]  # type: ignore[index]
    assert "preset" in props
    preset_prop = props["preset"]
    assert preset_prop["type"] == "string"
    assert set(preset_prop["enum"]) == {"calming_teal", "warm_fade", "identity"}


def test_color_lut_effect_schema_requires_preset() -> None:
    """color_lut schema lists 'preset' as required."""
    schema = COLOR_LUT.parameter_schema
    assert "preset" in schema.get("required", [])


def test_color_lut_effect_not_automatable() -> None:
    """color_lut has empty automatable set (no automation support)."""
    assert len(COLOR_LUT.automatable) == 0


def test_color_lut_effect_automation_filter_template_is_none() -> None:
    """color_lut has no automation_filter_template (not automatable)."""
    assert COLOR_LUT.automation_filter_template is None


def test_color_lut_preview_fn_produces_lut3d_string() -> None:
    """preview_fn() returns a string containing 'lut3d'."""
    s = COLOR_LUT.preview_fn()
    assert "lut3d" in s, f"Expected lut3d in preview: {s}"


def test_color_lut_build_fn_produces_lut3d_string() -> None:
    """build_fn({'preset': 'identity'}) returns a string containing 'lut3d'."""
    s = COLOR_LUT.build_fn({"preset": "identity"})
    assert "lut3d" in s, f"Expected lut3d in build output: {s}"
    assert "identity" in s, f"Expected 'identity' in build output: {s}"


def test_color_lut_build_fn_path_points_to_existing_file() -> None:
    """build_fn returns a path that resolves to an existing .cube file."""
    s = COLOR_LUT.build_fn({"preset": "identity"})
    # Extract path after 'file='
    assert "file=" in s, f"Expected file= in: {s}"
    path_part = s.split("file=", 1)[1]
    path = Path(path_part)
    assert path.exists(), f"Resolved LUT path does not exist: {path}"
    assert path.suffix == ".cube", f"Expected .cube extension: {path}"


def test_color_lut_build_fn_path_uses_forward_slashes() -> None:
    """Verify _build_color_lut returns a filter string with no backslashes (BL-499)."""
    result = _build_color_lut({"preset": "identity"})
    assert "\\" not in result, f"Expected forward slashes only, got: {result}"
    assert "lut3d=file=" in result


def test_color_lut_bundled_assets_exist() -> None:
    """All three bundled .cube files are accessible via importlib.resources."""
    import importlib.resources

    for preset in ("calming_teal", "warm_fade", "identity"):
        ref = importlib.resources.files("stoat_ferret") / "assets" / "luts" / f"{preset}.cube"
        path = Path(str(ref))
        assert path.exists(), f"Bundled LUT asset missing: {path}"


# ---------------------------------------------------------------------------
# Contract tests — require real FFmpeg (BL-450-AC-3)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="STOAT_TEST_FFMPEG not set")
@pytest.mark.contract
def test_color_lut_renders_contract(tmp_path: Path) -> None:
    """color_lut effect applies without FFmpeg error (integration, BL-450-AC-3)."""
    import subprocess

    filter_str = COLOR_LUT.build_fn({"preset": "identity"})
    output = tmp_path / "out.mp4"
    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "color=blue:size=64x64:duration=1:rate=24",
            "-vf",
            filter_str,
            "-frames:v",
            "1",
            "-y",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"FFmpeg failed:\n{result.stderr}"
    assert output.exists(), "Output file was not created"

"""Tests for BlurBuilder and SharpenBuilder (BL-451)."""

from __future__ import annotations

import os

import pytest

from stoat_ferret.effects.definitions import BLUR, SHARPEN, create_default_registry
from stoat_ferret_core import Automation, BlurBuilder, Keyframe, SharpenBuilder

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")


# ---------------------------------------------------------------------------
# BlurBuilder unit tests (FR-001-AC-1)
# ---------------------------------------------------------------------------


def test_blur_gaussian_build_produces_gblur() -> None:
    """BlurBuilder(sigma, 'gaussian').build() produces gblur=sigma=<sigma>."""
    f = BlurBuilder(2.5, "gaussian").build()
    s = str(f)
    assert s.startswith("gblur="), f"Expected gblur filter, got: {s}"
    assert "sigma=2.5" in s, f"Expected sigma=2.5 in: {s}"


def test_blur_directional_build_produces_dblur() -> None:
    """BlurBuilder(sigma, 'directional').build() produces dblur=radius=<sigma>."""
    f = BlurBuilder(3.0, "directional").build()
    s = str(f)
    assert s.startswith("dblur="), f"Expected dblur filter, got: {s}"
    assert "radius=3" in s, f"Expected radius=3 in: {s}"


def test_blur_invalid_sigma_raises() -> None:
    """BlurBuilder raises ValueError if sigma <= 0."""
    with pytest.raises((ValueError, Exception)):
        BlurBuilder(0.0, "gaussian")
    with pytest.raises((ValueError, Exception)):
        BlurBuilder(-1.0, "gaussian")


def test_blur_invalid_type_raises() -> None:
    """BlurBuilder raises ValueError for unrecognised blur_type."""
    with pytest.raises((ValueError, Exception)):
        BlurBuilder(1.0, "box")
    with pytest.raises((ValueError, Exception)):
        BlurBuilder(1.0, "")


# ---------------------------------------------------------------------------
# BlurBuilder automation (FR-001-AC-2)
# ---------------------------------------------------------------------------


def test_blur_with_automation_build_contains_eval_frame() -> None:
    """BlurBuilder.with_automation().build() produces gblur=sigma='...':eval=frame."""
    auto = Automation(
        default=1.0,
        keyframes=[
            Keyframe(t=0.0, value=1.0, curve="Linear"),
            Keyframe(t=5.0, value=5.0, curve="Linear"),
        ],
    )
    f = BlurBuilder(2.0, "gaussian").with_automation(auto).build()
    s = str(f)
    assert "eval=frame" in s, f"Expected eval=frame in automated blur filter: {s}"
    assert "gblur=" in s, f"Expected gblur in automated blur filter: {s}"


def test_blur_without_automation_has_no_eval_frame() -> None:
    """BlurBuilder without automation does NOT include eval=frame."""
    f = BlurBuilder(2.0, "gaussian").build()
    s = str(f)
    assert "eval=frame" not in s, f"eval=frame should not appear in static filter: {s}"


def test_blur_with_automation_returns_new_instance() -> None:
    """with_automation returns a new BlurBuilder (immutable chaining)."""
    original = BlurBuilder(2.0, "gaussian")
    auto = Automation(
        default=1.0,
        keyframes=[Keyframe(t=0.0, value=1.0, curve="Linear")],
    )
    modified = original.with_automation(auto)
    # original still builds without eval=frame
    assert "eval=frame" not in str(original.build())
    # modified builds with eval=frame
    assert "eval=frame" in str(modified.build())


# ---------------------------------------------------------------------------
# SharpenBuilder unit tests (FR-002-AC-1)
# ---------------------------------------------------------------------------


def test_sharpen_build_produces_unsharp() -> None:
    """SharpenBuilder.build() produces unsharp filter with correct params."""
    f = SharpenBuilder(1.5).build()
    s = str(f)
    assert "unsharp" in s, f"Expected unsharp filter: {s}"
    assert "luma_msize_x=5" in s, f"Expected luma_msize_x=5: {s}"
    assert "luma_msize_y=5" in s, f"Expected luma_msize_y=5: {s}"
    assert "luma_amount=1.5" in s, f"Expected luma_amount=1.5: {s}"


def test_sharpen_invalid_amount_raises() -> None:
    """SharpenBuilder raises ValueError if amount <= 0."""
    with pytest.raises((ValueError, Exception)):
        SharpenBuilder(0.0)
    with pytest.raises((ValueError, Exception)):
        SharpenBuilder(-0.1)


def test_sharpen_no_automation() -> None:
    """SharpenBuilder has no with_automation method (FR-002-AC-2)."""
    assert not hasattr(SharpenBuilder(1.0), "with_automation"), (
        "SharpenBuilder must not expose with_automation"
    )


# ---------------------------------------------------------------------------
# EffectDefinition / registry tests (FR-003-AC-1)
# ---------------------------------------------------------------------------


def test_blur_effect_definition_automatable() -> None:
    """BLUR EffectDefinition has automatable={'sigma'} (FR-001-AC-3)."""
    assert "sigma" in BLUR.automatable


def test_blur_effect_definition_automation_template() -> None:
    """BLUR.automation_filter_template matches gblur=sigma='{expr}':eval=frame."""
    assert BLUR.automation_filter_template == "gblur=sigma='{expr}':eval=frame"


def test_sharpen_effect_definition_not_automatable() -> None:
    """SHARPEN EffectDefinition is not automatable (FR-002-AC-2)."""
    assert len(SHARPEN.automatable) == 0
    assert SHARPEN.automation_filter_template is None


def test_blur_registered_in_registry() -> None:
    """blur is registered in create_default_registry()."""
    registry = create_default_registry()
    defn = registry.get("blur")
    assert defn is not None, "blur must be in the registry"
    assert defn.automatable == frozenset({"sigma"})


def test_sharpen_registered_in_registry() -> None:
    """sharpen is registered in create_default_registry()."""
    registry = create_default_registry()
    defn = registry.get("sharpen")
    assert defn is not None, "sharpen must be in the registry"


def test_blur_build_fn_gaussian() -> None:
    """BLUR.build_fn produces gblur filter string."""
    result = BLUR.build_fn({"sigma": 3.0, "blur_type": "gaussian"})
    assert "gblur" in result
    assert "sigma=3" in result


def test_blur_build_fn_directional() -> None:
    """BLUR.build_fn with blur_type=directional produces dblur filter string."""
    result = BLUR.build_fn({"sigma": 2.0, "blur_type": "directional"})
    assert "dblur" in result
    assert "radius=2" in result


def test_sharpen_build_fn() -> None:
    """SHARPEN.build_fn produces unsharp filter string."""
    result = SHARPEN.build_fn({"amount": 2.0})
    assert "unsharp" in result
    assert "luma_amount=2" in result


def test_blur_automation_dispatch_via_registry() -> None:
    """Registry.build_automation_filter_string works for blur (Feature 001 dispatch)."""
    registry = create_default_registry()
    result = registry.build_automation_filter_string("blur", "1+0.5*t")
    assert "eval=frame" in result
    assert "gblur" in result
    assert "1+0.5*t" in result


# ---------------------------------------------------------------------------
# Contract tests (deferred_post_merge — FR-004-AC-1)
# These require STOAT_TEST_FFMPEG=1 and a real FFmpeg installation.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="requires STOAT_TEST_FFMPEG=1 and real ffmpeg")
def test_blur_gaussian_renders_contract() -> None:
    """BlurBuilder gaussian render contract test against real FFmpeg."""
    import subprocess

    f = BlurBuilder(2.0, "gaussian").build()
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=64x64:duration=0.1",
        "-vf",
        str(f),
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    assert result.returncode == 0, f"FFmpeg gblur failed: {result.stderr.decode()}"


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="requires STOAT_TEST_FFMPEG=1 and real ffmpeg")
def test_blur_directional_renders_contract() -> None:
    """BlurBuilder directional render contract test against real FFmpeg."""
    import subprocess

    f = BlurBuilder(2.0, "directional").build()
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=64x64:duration=0.1",
        "-vf",
        str(f),
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    assert result.returncode == 0, f"FFmpeg dblur failed: {result.stderr.decode()}"


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="requires STOAT_TEST_FFMPEG=1 and real ffmpeg")
def test_sharpen_renders_contract() -> None:
    """SharpenBuilder render contract test against real FFmpeg."""
    import subprocess

    f = SharpenBuilder(1.5).build()
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=64x64:duration=0.1",
        "-vf",
        str(f),
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    assert result.returncode == 0, f"FFmpeg unsharp failed: {result.stderr.decode()}"

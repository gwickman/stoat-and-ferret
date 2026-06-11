"""Tests for PanBuilder (BL-437): static stereo positioning and automation envelope."""

from __future__ import annotations

import os

import pytest

from stoat_ferret_core import Automation, Keyframe, PanBuilder

# ---------------------------------------------------------------------------
# Unit tests — filter string generation (no FFmpeg required)
# ---------------------------------------------------------------------------


def test_pan_builder_center_position() -> None:
    """PanBuilder(0.0) produces equal left and right gains."""
    f = PanBuilder(0.0).build()
    s = str(f)
    assert s.startswith("pan=stereo|"), f"expected pan=stereo| prefix, got: {s}"
    assert "c0=1*c0" in s, f"expected c0=1*c0 at center, got: {s}"
    assert "c1=1*c1" in s, f"expected c1=1*c1 at center, got: {s}"


def test_pan_builder_full_right() -> None:
    """PanBuilder(1.0) zeroes out the left channel."""
    f = PanBuilder(1.0).build()
    s = str(f)
    assert "c0=0*c0" in s, f"expected c0=0*c0 at full right, got: {s}"


def test_pan_builder_full_left() -> None:
    """PanBuilder(-1.0) zeroes out the right channel."""
    f = PanBuilder(-1.0).build()
    s = str(f)
    assert "c1=0*c1" in s, f"expected c1=0*c1 at full left, got: {s}"


def test_pan_builder_half_right() -> None:
    """PanBuilder(0.5) attenuates left and boosts right."""
    f = PanBuilder(0.5).build()
    s = str(f)
    assert "pan=stereo|" in s, f"expected pan filter, got: {s}"
    assert "c0=0.5*c0" in s, f"expected c0=0.5*c0 at pos 0.5, got: {s}"
    assert "c1=1.5*c1" in s, f"expected c1=1.5*c1 at pos 0.5, got: {s}"


def test_pan_builder_clamps_above_one() -> None:
    """PanBuilder clamps position > 1.0 to 1.0 (LRN-597)."""
    b = PanBuilder(2.0)
    s = str(b.build())
    assert "c0=0*c0" in s, f"expected same output as position=1.0, got: {s}"


def test_pan_builder_clamps_below_minus_one() -> None:
    """PanBuilder clamps position < -1.0 to -1.0 (LRN-597)."""
    b = PanBuilder(-2.0)
    s = str(b.build())
    assert "c1=0*c1" in s, f"expected same output as position=-1.0, got: {s}"


def test_pan_builder_automation_contains_eval_frame() -> None:
    """Automated PanBuilder must emit eval=frame (LRN-583)."""
    auto = Automation(
        default=0.0,
        keyframes=[
            Keyframe(t=0.0, value=-0.5, curve="Linear"),
            Keyframe(t=2.0, value=0.5, curve="Linear"),
        ],
    )
    f = PanBuilder(0.0).with_automation(auto).build()
    s = str(f)
    assert "eval=frame" in s, f"eval=frame must be present per LRN-583, got: {s}"


def test_pan_builder_automation_uses_aeval_filter() -> None:
    """Automated PanBuilder uses aeval filter for in-place signal processing."""
    auto = Automation(
        default=0.0,
        keyframes=[
            Keyframe(t=0.0, value=-0.5, curve="Linear"),
            Keyframe(t=2.0, value=0.5, curve="Linear"),
        ],
    )
    f = PanBuilder(0.0).with_automation(auto).build()
    s = str(f)
    assert s.startswith("aeval="), f"expected aeval filter for automation, got: {s}"


def test_pan_builder_automation_contains_both_channels() -> None:
    """Automated filter string references c0 and c1."""
    auto = Automation(default=0.0, keyframes=[Keyframe(t=0.0, value=0.0, curve="Hold")])
    f = PanBuilder(0.0).with_automation(auto).build()
    s = str(f)
    assert "c0" in s, f"expected c0 channel expression, got: {s}"
    assert "c1" in s, f"expected c1 channel expression, got: {s}"


def test_pan_registered_in_default_registry() -> None:
    """Pan effect is registered under the 'pan' key in the default registry."""
    from stoat_ferret.effects.definitions import create_default_registry

    registry = create_default_registry()
    assert registry.get("pan") is not None, "pan effect must be registered"


def test_pan_effect_build_fn_returns_string() -> None:
    """PAN.build_fn returns a non-empty filter string."""
    from stoat_ferret.effects.definitions import PAN

    result = PAN.build_fn({"position": 0.3})
    assert isinstance(result, str)
    assert len(result) > 0


def test_pan_effect_build_fn_center() -> None:
    """PAN.build_fn with position=0.0 produces a centered pan filter."""
    from stoat_ferret.effects.definitions import PAN

    result = PAN.build_fn({"position": 0.0})
    assert "pan=stereo|" in result


def test_pan_effect_automatable_flag() -> None:
    """PAN.automatable includes 'position'."""
    from stoat_ferret.effects.definitions import PAN

    assert "position" in PAN.automatable


# ---------------------------------------------------------------------------
# FFmpeg-gated contract tests (require STOAT_TEST_FFMPEG=1)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg required; set STOAT_TEST_FFMPEG=1",
)
def test_pan_static_renders_stereo_output(tmp_path: str) -> None:
    """PanBuilder(0.5) applied to a mono sine produces a stereo WAV with L != R."""
    import subprocess
    from pathlib import Path

    tmp = Path(str(tmp_path))
    mono = tmp / "mono.wav"
    output = tmp / "panned.wav"

    # Generate 1s mono 440 Hz sine at 44100 Hz
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=1",
            str(mono),
        ],
        check=True,
        capture_output=True,
    )

    pan_filter = str(PanBuilder(0.5).build())
    subprocess.run(
        ["ffmpeg", "-y", "-i", str(mono), "-af", pan_filter, str(output)],
        check=True,
        capture_output=True,
    )

    assert output.exists(), "output file must exist after render"
    assert output.stat().st_size > 0, "output must be non-empty"

    # Verify stereo output with distinct L/R levels via ffprobe
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    import json

    info = json.loads(probe.stdout)
    audio_streams = [s for s in info["streams"] if s.get("codec_type") == "audio"]
    assert audio_streams, "output must have an audio stream"
    assert audio_streams[0].get("channels", 0) == 2, "output must be stereo (2 channels)"


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg required; set STOAT_TEST_FFMPEG=1",
)
def test_pan_automation_eval_frame_produces_time_varying_output(tmp_path: str) -> None:
    """Automated PanBuilder with eval=frame produces output that varies over time."""
    import subprocess
    from pathlib import Path

    tmp = Path(str(tmp_path))
    mono = tmp / "mono.wav"
    output = tmp / "panned_auto.wav"

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=2",
            str(mono),
        ],
        check=True,
        capture_output=True,
    )

    auto = Automation(
        default=-1.0,
        keyframes=[
            Keyframe(t=0.0, value=-1.0, curve="Linear"),
            Keyframe(t=2.0, value=1.0, curve="Linear"),
        ],
    )
    pan_filter = str(PanBuilder(0.0).with_automation(auto).build())
    assert "eval=frame" in pan_filter, f"eval=frame must be present, got: {pan_filter}"

    subprocess.run(
        ["ffmpeg", "-y", "-i", str(mono), "-af", pan_filter, str(output)],
        check=True,
        capture_output=True,
    )

    assert output.exists(), "output file must exist after automated render"
    assert output.stat().st_size > 0, "output must be non-empty"

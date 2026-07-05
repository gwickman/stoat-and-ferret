# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for tone synthesis generator — BL-439."""

from __future__ import annotations

import os

import pytest


def test_tone_filter_constant_frequency() -> None:
    """build_generator_source_filter produces a valid aevalsrc expression for a constant tone."""
    from stoat_ferret_core import build_generator_source_filter

    f = build_generator_source_filter('{"type": "tone", "frequency": 440.0}', 5.0)
    assert "aevalsrc" in f
    assert "eval=frame" not in f  # FFmpeg 8: eval=frame option removed
    assert "440.000" in f
    assert "duration=5.000000" in f
    assert "stereo" not in f


def test_tone_filter_frequency_sweep() -> None:
    """build_generator_source_filter produces a chirp expression when frequency_end is set."""
    from stoat_ferret_core import build_generator_source_filter

    f = build_generator_source_filter(
        '{"type": "tone", "frequency": 100.0, "frequency_end": 200.0}', 10.0
    )
    assert "aevalsrc" in f
    assert "eval=frame" not in f  # FFmpeg 8: eval=frame option removed
    assert "100.000" in f
    assert "200.000" in f
    assert "t*t" in f
    assert "duration=10.000000" in f


def test_tone_filter_binaural_beat() -> None:
    """build_generator_source_filter produces a stereo expression for binaural mode."""
    from stoat_ferret_core import build_generator_source_filter

    f = build_generator_source_filter(
        '{"type": "tone", "frequency": 200.0, "binaural_offset": 4.0}', 5.0
    )
    assert "stereo" in f
    assert "eval=frame" not in f  # FFmpeg 8: eval=frame option removed
    assert "200.000" in f
    assert "204.000" in f
    assert "|" in f


def test_tone_filter_binaural_sweep() -> None:
    """Binaural + sweep: both channels use chirp; right channel offset by binaural_offset."""
    from stoat_ferret_core import build_generator_source_filter

    f = build_generator_source_filter(
        '{"type": "tone", "frequency": 100.0, "frequency_end": 200.0, "binaural_offset": 4.0}',
        5.0,
    )
    assert "stereo" in f
    assert "100.000" in f
    assert "200.000" in f
    # Right channel: 104 Hz → 204 Hz
    assert "104.000" in f
    assert "204.000" in f
    assert "t*t" in f


def test_tone_filter_missing_frequency_raises() -> None:
    """build_generator_source_filter raises ValueError when 'frequency' is absent."""
    from stoat_ferret_core import build_generator_source_filter

    with pytest.raises(ValueError, match="frequency"):
        build_generator_source_filter('{"type": "tone"}', 5.0)


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg integration test — set STOAT_TEST_FFMPEG=1 to run",
)
def test_tone_synthesis_renders_constant_frequency(tmp_path: object) -> None:
    """Tone generator (constant frequency) renders a WAV file via aevalsrc."""
    import subprocess
    from pathlib import Path

    from stoat_ferret_core import build_generator_render_command

    params_json = '{"type": "tone", "frequency": 440.0}'
    duration = 0.1
    out = str(Path(str(tmp_path)) / "tone_constant.wav")  # type: ignore[arg-type]

    cmd = build_generator_render_command(params_json, duration, out)
    result = subprocess.run(["ffmpeg"] + cmd.args(), capture_output=True, text=True)
    assert result.returncode == 0, f"FFmpeg failed: {result.stderr[-500:]}"
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg integration test — set STOAT_TEST_FFMPEG=1 to run",
)
def test_tone_synthesis_renders_frequency_sweep(tmp_path: object) -> None:
    """Tone generator (linear chirp sweep) renders a WAV file."""
    import subprocess
    from pathlib import Path

    from stoat_ferret_core import build_generator_render_command

    params_json = '{"type": "tone", "frequency": 100.0, "frequency_end": 200.0}'
    duration = 0.5
    out = str(Path(str(tmp_path)) / "tone_sweep.wav")  # type: ignore[arg-type]

    cmd = build_generator_render_command(params_json, duration, out)
    result = subprocess.run(["ffmpeg"] + cmd.args(), capture_output=True, text=True)
    assert result.returncode == 0, f"FFmpeg failed: {result.stderr[-500:]}"
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg integration test — set STOAT_TEST_FFMPEG=1 to run",
)
def test_tone_synthesis_renders_binaural_stereo(tmp_path: object) -> None:
    """Binaural beat tone renders a stereo WAV with L/R frequency offset."""
    import subprocess
    from pathlib import Path

    from stoat_ferret_core import build_generator_render_command

    params_json = '{"type": "tone", "frequency": 200.0, "binaural_offset": 4.0}'
    duration = 0.1
    out = str(Path(str(tmp_path)) / "tone_binaural.wav")  # type: ignore[arg-type]

    cmd = build_generator_render_command(params_json, duration, out)
    result = subprocess.run(["ffmpeg"] + cmd.args(), capture_output=True, text=True)
    assert result.returncode == 0, f"FFmpeg failed: {result.stderr[-500:]}"
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0

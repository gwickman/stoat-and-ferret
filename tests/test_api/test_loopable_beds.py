"""Tests for build_loop_render_command (BL-440: loopable ambience beds)."""

from __future__ import annotations

import os

import pytest

from stoat_ferret_core import build_loop_render_command

# ---------------------------------------------------------------------------
# Unit tests (no FFmpeg required)
# ---------------------------------------------------------------------------


def test_loop_command_basic_structure() -> None:
    """Command contains -stream_loop -1 and trims to target duration."""
    cmd = build_loop_render_command("/bed.wav", 60.0, "/out.wav")
    args = cmd.args()
    assert "-stream_loop" in args
    assert args[args.index("-stream_loop") + 1] == "-1"
    assert "-i" in args
    assert "/bed.wav" in args
    assert "-t" in args
    assert "60.000000" in args
    assert args[-1] == "/out.wav"


def test_loop_command_no_crossfade_omits_af() -> None:
    """Zero crossfade_duration must not add an -af filter argument."""
    cmd = build_loop_render_command("/bed.wav", 60.0, "/out.wav", crossfade_duration=0.0)
    assert "-af" not in cmd.args()


def test_loop_command_no_loop_start_omits_ss() -> None:
    """Zero loop_start must not add an -ss seek argument."""
    cmd = build_loop_render_command("/bed.wav", 60.0, "/out.wav", loop_start=0.0)
    assert "-ss" not in cmd.args()


def test_loop_command_crossfade_adds_af() -> None:
    """Positive crossfade_duration adds an -af filter with afade in+out."""
    cmd = build_loop_render_command("/bed.wav", 60.0, "/out.wav", crossfade_duration=0.05)
    args = cmd.args()
    assert "-af" in args
    af_idx = args.index("-af")
    filt = args[af_idx + 1]
    assert "afade=t=in" in filt
    assert "afade=t=out" in filt


def test_loop_command_crossfade_fade_out_start() -> None:
    """fade-out start time equals target_duration minus crossfade_duration."""
    cmd = build_loop_render_command("/bed.wav", 10.0, "/out.wav", crossfade_duration=0.5)
    args = cmd.args()
    af_idx = args.index("-af")
    filt = args[af_idx + 1]
    # fade-out should start at 9.5s
    assert "st=9.500000" in filt


def test_loop_command_loop_start_adds_ss() -> None:
    """Positive loop_start adds -ss with the correct offset string."""
    cmd = build_loop_render_command("/bed.wav", 60.0, "/out.wav", loop_start=2.5)
    args = cmd.args()
    assert "-ss" in args
    ss_idx = args.index("-ss")
    assert args[ss_idx + 1] == "2.500000"


def test_loop_command_output_path_last() -> None:
    """Output path is always the final argument and matches output_path attr."""
    cmd = build_loop_render_command("/input.wav", 120.0, "/output.wav", 0.1, 1.0)
    assert cmd.args()[-1] == "/output.wav"
    assert cmd.output_path == "/output.wav"
    assert cmd.segment_index == 0


def test_loop_command_stream_loop_precedes_input() -> None:
    """-stream_loop -1 must appear before -i (FFmpeg flag ordering requirement)."""
    cmd = build_loop_render_command("/bed.wav", 60.0, "/out.wav")
    args = cmd.args()
    sl_idx = args.index("-stream_loop")
    i_idx = args.index("-i")
    assert sl_idx < i_idx


# ---------------------------------------------------------------------------
# FFmpeg contract tests (require real FFmpeg binary)
# ---------------------------------------------------------------------------

_FFMPEG_TESTS = pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg integration test — set STOAT_TEST_FFMPEG=1 to run",
)


@_FFMPEG_TESTS
def test_loop_command_renders_to_wav(tmp_path: object) -> None:
    """Loop command produces a non-empty WAV file at target duration."""
    import subprocess
    from pathlib import Path

    # Build a short sine source first, then loop it
    from stoat_ferret_core import build_generator_render_command

    bed = str(Path(str(tmp_path)) / "bed.wav")
    out = str(Path(str(tmp_path)) / "out.wav")

    src_cmd = build_generator_render_command('{"type": "sine", "frequency": 220.0}', 2.0, bed)
    result = subprocess.run(["ffmpeg"] + src_cmd.args(), capture_output=True, text=True)
    assert result.returncode == 0, f"source render failed: {result.stderr[-300:]}"

    loop_cmd = build_loop_render_command(bed, 10.0, out)
    result = subprocess.run(["ffmpeg"] + loop_cmd.args(), capture_output=True, text=True)
    assert result.returncode == 0, f"loop render failed: {result.stderr[-500:]}"
    assert Path(out).exists()
    assert Path(out).stat().st_size > 0


@_FFMPEG_TESTS
def test_loop_command_crossfade_renders(tmp_path: object) -> None:
    """Loop command with crossfade renders without FFmpeg errors."""
    import subprocess
    from pathlib import Path

    from stoat_ferret_core import build_generator_render_command

    bed = str(Path(str(tmp_path)) / "bed.wav")
    out = str(Path(str(tmp_path)) / "out.wav")

    src_cmd = build_generator_render_command('{"type": "sine", "frequency": 220.0}', 2.0, bed)
    subprocess.run(["ffmpeg"] + src_cmd.args(), capture_output=True, check=True)

    loop_cmd = build_loop_render_command(bed, 10.0, out, crossfade_duration=0.1)
    result = subprocess.run(["ffmpeg"] + loop_cmd.args(), capture_output=True, text=True)
    assert result.returncode == 0, f"loop+crossfade render failed: {result.stderr[-500:]}"
    assert Path(out).stat().st_size > 0

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""FFmpeg-gated tests for the 5 Rust QC parser families.

Requires STOAT_TEST_FFMPEG=1 to run. Discharges BL-423-AC-1 through BL-423-AC-4.
Each test runs FFmpeg against a lavfi fixture and verifies the corresponding
Rust parser returns correct typed measurements without panicking.
"""

from __future__ import annotations

import math
import os
import subprocess

import pytest

_STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")

_skip_no_ffmpeg = pytest.mark.skipif(
    not _STOAT_TEST_FFMPEG,
    reason="requires STOAT_TEST_FFMPEG=1",
)


def _ffmpeg_stderr(*args: str) -> str:
    """Run ffmpeg with given args and return stderr as a string."""
    result = subprocess.run(
        ["ffmpeg", *args],
        capture_output=True,
        text=True,
        timeout=60,
    )
    return result.stderr


@_skip_no_ffmpeg
def test_parse_loudnorm_real_output() -> None:
    """BL-423-AC-1: parse_loudness_report returns non-null measurements from loudnorm JSON."""
    from stoat_ferret_core import parse_loudness_report

    stderr = _ffmpeg_stderr(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:duration=5",
        "-af",
        "loudnorm=I=-23:TP=-1:LRA=11:print_format=json",
        "-f",
        "null",
        "/dev/null",
    )

    report = parse_loudness_report(stderr)

    assert math.isfinite(report.integrated_lufs), (
        f"integrated_lufs not finite: {report.integrated_lufs}"
    )
    assert math.isfinite(report.lra), f"lra not finite: {report.lra}"
    assert math.isfinite(report.true_peak_dbtp), (
        f"true_peak_dbtp not finite: {report.true_peak_dbtp}"
    )


@_skip_no_ffmpeg
def test_parse_peak_real_output() -> None:
    """BL-423-AC-2: parse_peak_report returns non-null peak_level and clipped_samples."""
    from stoat_ferret_core import parse_peak_report

    stderr = _ffmpeg_stderr(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:duration=5",
        "-af",
        "astats=metadata=1",
        "-f",
        "null",
        "/dev/null",
    )

    report = parse_peak_report(stderr)

    assert math.isfinite(report.peak_level), f"peak_level not finite: {report.peak_level}"
    assert report.clipped_samples >= 0, f"clipped_samples negative: {report.clipped_samples}"


@_skip_no_ffmpeg
def test_parse_silence_real_output() -> None:
    """BL-423-AC-3: parse_silence_report returns populated regions for a silent fixture.

    Uses anullsrc (pure silence) as input. The entire 3-second clip is below the
    -30 dB noise threshold, so at least one silence region is expected.
    Trailing silence_start without silence_end produces end==float('inf') (f64::MAX).
    """
    from stoat_ferret_core import parse_silence_report

    stderr = _ffmpeg_stderr(
        "-f",
        "lavfi",
        "-i",
        "anullsrc=r=44100:cl=mono",
        "-t",
        "3",
        "-af",
        "silencedetect=noise=-30dB:duration=0.1",
        "-f",
        "null",
        "/dev/null",
    )

    report = parse_silence_report(stderr)

    assert len(report.regions) > 0, (
        f"expected at least one silence region; got 0. stderr snippet:\n{stderr[:500]}"
    )
    for region in report.regions:
        assert math.isfinite(region.start), f"region.start not finite: {region.start}"
        # end may be f64::MAX for a trailing silence_start without silence_end
        assert region.end >= region.start, (
            f"region.end ({region.end}) < region.start ({region.start})"
        )


@_skip_no_ffmpeg
def test_parse_spectral_real_output() -> None:
    """BL-423-AC-4 (spectral): parse_spectral_report returns populated channel_means.

    aspectralstats stores data as frame metadata. ametadata=mode=print without file=
    routes through av_log at INFO level, which is hidden at FFmpeg's default log level
    and prefixes every line with [filter @ addr]. Using file=/dev/stderr writes directly
    to stderr without the av_log prefix, so the parser's strip_prefix can match.
    """
    from stoat_ferret_core import parse_spectral_report

    stderr = _ffmpeg_stderr(
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:duration=5",
        "-af",
        "aspectralstats,ametadata=mode=print:file=/dev/stderr",
        "-f",
        "null",
        "/dev/null",
    )

    report = parse_spectral_report(stderr)

    assert len(report.channel_means) > 0, (
        f"expected channel_means, got empty list. stderr snippet:\n{stderr[:500]}"
    )
    assert report.channel_count == len(report.channel_means)
    for mean in report.channel_means:
        assert math.isfinite(mean), f"channel mean not finite: {mean}"


@_skip_no_ffmpeg
def test_parse_video_defect_real_output() -> None:
    """BL-423-AC-4 (video defects): parse_video_defect_report returns non-empty black_regions.

    color=black produces a solid black video fixture. blackdetect with d=0.1 minimum
    duration reports the entire clip as a single black region.
    """
    from stoat_ferret_core import parse_video_defect_report

    stderr = _ffmpeg_stderr(
        "-f",
        "lavfi",
        "-i",
        "color=black:duration=2:size=320x240:rate=5",
        "-vf",
        "blackdetect=d=0.1",
        "-f",
        "null",
        "/dev/null",
    )

    report = parse_video_defect_report(stderr)

    assert len(report.black_regions) > 0, (
        f"expected black_regions, got 0. stderr snippet:\n{stderr[:500]}"
    )
    for region in report.black_regions:
        assert math.isfinite(region.start)
        assert math.isfinite(region.end)
        assert region.end > region.start

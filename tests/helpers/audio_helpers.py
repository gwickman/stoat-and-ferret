# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Shared audio measurement helpers for FFmpeg-gated tests."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _measure_band_db_windowed(path: Path, freq_hz: int, start: float, end: float) -> float:
    """Return mean_volume (dBFS) of a narrow frequency band within a time window."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(path),
            "-af",
            f"atrim=start={start}:end={end},bandpass=f={freq_hz}:width_type=o:width=1,volumedetect",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    for line in r.stderr.splitlines():
        if "mean_volume" in line:
            return float(line.split("mean_volume:")[-1].strip().split(" ")[0])
    raise RuntimeError(
        f"volumedetect gave no mean_volume at {freq_hz} Hz for {path} [{start},{end}]"
    )

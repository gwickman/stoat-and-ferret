# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Integration tests for lut3d with Windows absolute paths (BL-499).

Validates that the variant-4 single-quoted colon-escape policy used by
emit_filter_option_path() produces FFmpeg-accepted filter strings on Windows.

Gated on STOAT_TEST_FFMPEG=1 and sys.platform == 'win32'.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG", "")

_IDENTITY_LUT_CONTENT = """\
LUT_3D_SIZE 2
0.0 0.0 0.0
1.0 0.0 0.0
0.0 1.0 0.0
1.0 1.0 0.0
0.0 0.0 1.0
1.0 0.0 1.0
0.0 1.0 1.0
1.0 1.0 1.0
"""


def _variant4_escape(path: str) -> str:
    """Apply variant-4 single-quoted colon-escape policy.

    Mirrors emit_filter_option_path() in Rust. Raises ValueError for apostrophes.
    Windows absolute paths get single-quoted with escaped colon; others pass through.
    """
    if "'" in path:
        raise ValueError(
            f"Path '{path}' contains an apostrophe which cannot be safely escaped "
            "for use in FFmpeg filter option values. Rename the file to remove "
            "the apostrophe character."
        )
    if len(path) >= 2 and path[1] == ":" and path[0].isalpha():
        drive = path[0]
        rest = path[2:].replace("\\", "/")
        return f"'{drive}\\:{rest}'"
    return path


@pytest.mark.skipif(
    sys.platform != "win32" or not STOAT_TEST_FFMPEG,
    reason="Windows FFmpeg integration test; set STOAT_TEST_FFMPEG=1 on Windows to enable",
)
def test_lut3d_windows_absolute_path(tmp_path: Path) -> None:
    """lut3d filter accepts a variant-4 escaped Windows absolute path (BL-499).

    Creates a temporary identity LUT at a Windows absolute path, escapes it
    using the variant-4 policy, and verifies FFmpeg 8.0.1 accepts the filter.
    """
    lut_file = tmp_path / "identity.cube"
    lut_file.write_text(_IDENTITY_LUT_CONTENT)

    escaped = _variant4_escape(str(lut_file))
    filter_str = f"lut3d=file={escaped}"

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
    assert result.returncode == 0, (
        f"FFmpeg rejected variant-4 escaped Windows path:\n{result.stderr}"
    )
    assert output.exists(), "Output file was not created"
    assert output.stat().st_size > 0, "Output file is empty"


def test_variant4_escape_windows_path() -> None:
    """_variant4_escape() applies colon-escape to Windows absolute paths."""
    result = _variant4_escape("C:\\Users\\foo\\bar.cube")
    assert result == "'C\\:/Users/foo/bar.cube'"


def test_variant4_escape_unix_path() -> None:
    """_variant4_escape() passes Unix paths through unchanged."""
    result = _variant4_escape("/home/user/file.cube")
    assert result == "/home/user/file.cube"


def test_variant4_escape_apostrophe_raises() -> None:
    """_variant4_escape() raises ValueError for paths containing apostrophe."""
    with pytest.raises(ValueError, match="apostrophe"):
        _variant4_escape("C:\\Users\\O'Brien\\file.cube")

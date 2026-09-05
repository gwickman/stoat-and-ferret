# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Preview media oracle: materialize HLS + decode frames + SSIM compare.

Provides three primitives for acceptance tests that verify preview content
at the media level (not just routing level):

- materialize_preview_session: wait for HLS manifest + >=1 segment
- decode_preview_frame: decode a frame at a timeline position
- compare_preview_render: assert SSIM agreement between preview and render
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess
from pathlib import Path

STOAT_TEST_FFMPEG = os.getenv("STOAT_TEST_FFMPEG")


async def materialize_preview_session(
    session_id: str,
    output_dir: Path | str,
    timeout: float = 30.0,
) -> dict:
    """Wait for HLS manifest + >=1 segment in output_dir; return session info.

    Args:
        session_id: Preview session identifier for tracking.
        output_dir: Directory containing HLS output (manifest.m3u8 + .ts files).
        timeout: Maximum seconds to wait for readiness.

    Returns:
        Dict with keys 'session_id', 'manifest_path', 'output_dir'.

    Raises:
        TimeoutError: If manifest or segments are not present within timeout.
    """
    output_path = Path(output_dir)
    manifest = output_path / "manifest.m3u8"
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        if manifest.exists() and any(
            f.suffix == ".ts" for f in output_path.iterdir() if f.is_file()
        ):
            return {
                "session_id": session_id,
                "manifest_path": str(manifest),
                "output_dir": str(output_path),
            }
        await asyncio.sleep(0.25)
    raise TimeoutError(f"Preview session '{session_id}' not ready within {timeout}s: {output_path}")


async def decode_preview_frame(session: dict, t: float) -> bytes:
    """Return PNG-encoded frame bytes from the preview HLS at timeline position t.

    Args:
        session: Session info dict returned by materialize_preview_session.
        t: Timeline position in seconds.

    Returns:
        Raw PNG frame bytes.

    Raises:
        RuntimeError: If FFmpeg fails to decode the frame or produces no output.
    """
    manifest_path = session["manifest_path"]
    result = await asyncio.to_thread(
        subprocess.run,
        [
            "ffmpeg",
            "-ss",
            str(t),
            "-i",
            manifest_path,
            "-frames:v",
            "1",
            "-f",
            "image2pipe",
            "-vcodec",
            "png",
            "-",
        ],
        capture_output=True,
        timeout=30,
    )
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError(
            f"Failed to decode preview frame at t={t}: "
            f"{result.stderr.decode(errors='replace')[-400:]}"
        )
    return result.stdout


def _compute_ssim_hls_vs_file(
    manifest_path: str,
    t_preview: float,
    render_path: Path,
    t_render: float,
    duration: float = 0.3,
) -> float:
    """Return SSIM between a preview HLS at t_preview and render file at t_render."""
    r = subprocess.run(
        [
            "ffmpeg",
            "-ss",
            str(t_preview),
            "-t",
            str(duration),
            "-i",
            manifest_path,
            "-ss",
            str(t_render),
            "-t",
            str(duration),
            "-i",
            str(render_path),
            "-filter_complex",
            "[0:v][1:v]ssim=f=-",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    m = re.search(r"All:(\d+\.\d+)", r.stderr)
    if not m:
        raise RuntimeError(f"Could not parse SSIM from ffmpeg output:\n{r.stderr[-600:]}")
    return float(m.group(1))


async def compare_preview_render(
    session: dict,
    render_path: Path,
    t_values: list[float],
    ssim_threshold: float,
) -> bool:
    """Assert SSIM >= ssim_threshold between preview HLS and render at all sampled times.

    Args:
        session: Session info dict returned by materialize_preview_session.
        render_path: Path to the render output file.
        t_values: Timeline positions (seconds) at which to sample and compare.
        ssim_threshold: Minimum acceptable SSIM value (e.g. 0.90).

    Returns:
        True when all comparisons pass.

    Raises:
        AssertionError: If SSIM < ssim_threshold at any t_value.
        RuntimeError: If FFmpeg fails to compute SSIM.
    """
    manifest_path = session["manifest_path"]
    for t in t_values:
        ssim = await asyncio.to_thread(_compute_ssim_hls_vs_file, manifest_path, t, render_path, t)
        if ssim < ssim_threshold:
            raise AssertionError(
                f"Preview/render SSIM {ssim:.4f} < threshold {ssim_threshold} at t={t}s"
            )
    return True

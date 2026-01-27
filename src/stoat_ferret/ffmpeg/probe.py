"""FFprobe wrapper for extracting video metadata."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class FFprobeError(Exception):
    """Error running ffprobe."""


@dataclass
class VideoMetadata:
    """Video metadata extracted from ffprobe.

    Contains essential video file information including dimensions,
    duration, codecs, and frame rate.
    """

    duration_seconds: float
    width: int
    height: int
    frame_rate_numerator: int
    frame_rate_denominator: int
    video_codec: str
    audio_codec: str | None
    file_size: int

    @property
    def frame_rate(self) -> tuple[int, int]:
        """Return frame rate as (numerator, denominator) tuple."""
        return (self.frame_rate_numerator, self.frame_rate_denominator)

    @property
    def duration_frames(self) -> int:
        """Compute duration in frames from seconds and frame rate."""
        fps = self.frame_rate_numerator / self.frame_rate_denominator
        return int(self.duration_seconds * fps)


def ffprobe_video(path: str, ffprobe_path: str = "ffprobe") -> VideoMetadata:
    """Run ffprobe on a video file and return structured metadata.

    Args:
        path: Path to the video file.
        ffprobe_path: Path to the ffprobe executable.

    Returns:
        VideoMetadata with extracted information.

    Raises:
        FileNotFoundError: If the video file does not exist.
        FFprobeError: If ffprobe is not installed, times out, or fails.
        ValueError: If the file is not a valid video (no video stream).
    """
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Video file not found: {path}")

    try:
        result = subprocess.run(
            [
                ffprobe_path,
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_format",
                "-show_streams",
                path,
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
    except FileNotFoundError:
        raise FFprobeError(f"ffprobe not found at: {ffprobe_path}. Is FFmpeg installed?") from None
    except subprocess.TimeoutExpired as e:
        raise FFprobeError(f"ffprobe timed out reading: {path}") from e

    if result.returncode != 0:
        stderr = result.stderr.decode(errors="replace")
        raise FFprobeError(f"ffprobe failed for {path}: {stderr}")

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise FFprobeError(f"Failed to parse ffprobe output: {e}") from e

    return _parse_ffprobe_output(data, file_path)


def _parse_ffprobe_output(data: dict[str, Any], file_path: Path) -> VideoMetadata:
    """Parse ffprobe JSON output into VideoMetadata.

    Args:
        data: Parsed JSON from ffprobe.
        file_path: Original file path for error messages.

    Returns:
        VideoMetadata extracted from the ffprobe output.

    Raises:
        ValueError: If no video stream is found in the data.
    """
    video_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "video"),
        None,
    )
    if not video_stream:
        raise ValueError(f"No video stream found in: {file_path}")

    audio_stream = next(
        (s for s in data.get("streams", []) if s.get("codec_type") == "audio"),
        None,
    )

    # Parse frame rate (e.g., "24/1" or "30000/1001")
    r_frame_rate = video_stream.get("r_frame_rate", "24/1")
    num, den = map(int, r_frame_rate.split("/"))

    format_info = data.get("format", {})

    return VideoMetadata(
        duration_seconds=float(format_info.get("duration", 0)),
        width=int(video_stream["width"]),
        height=int(video_stream["height"]),
        frame_rate_numerator=num,
        frame_rate_denominator=den,
        video_codec=video_stream["codec_name"],
        audio_codec=audio_stream["codec_name"] if audio_stream else None,
        file_size=int(format_info.get("size", 0)),
    )

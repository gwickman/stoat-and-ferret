"""FFmpeg integration module for video probing and processing."""

from stoat_ferret.ffmpeg.executor import (
    ExecutionResult,
    FakeFFmpegExecutor,
    FFmpegExecutor,
    RealFFmpegExecutor,
    RecordingFFmpegExecutor,
)
from stoat_ferret.ffmpeg.probe import FFprobeError, VideoMetadata, ffprobe_video

__all__ = [
    "ExecutionResult",
    "FakeFFmpegExecutor",
    "FFmpegExecutor",
    "FFprobeError",
    "RealFFmpegExecutor",
    "RecordingFFmpegExecutor",
    "VideoMetadata",
    "ffprobe_video",
]

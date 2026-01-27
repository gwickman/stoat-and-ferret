"""FFmpeg integration module for video probing and processing."""

from stoat_ferret.ffmpeg.executor import (
    ExecutionResult,
    FakeFFmpegExecutor,
    FFmpegExecutor,
    RealFFmpegExecutor,
    RecordingFFmpegExecutor,
)
from stoat_ferret.ffmpeg.integration import CommandExecutionError, execute_command
from stoat_ferret.ffmpeg.probe import FFprobeError, VideoMetadata, ffprobe_video

__all__ = [
    "CommandExecutionError",
    "ExecutionResult",
    "FakeFFmpegExecutor",
    "FFmpegExecutor",
    "FFprobeError",
    "RealFFmpegExecutor",
    "RecordingFFmpegExecutor",
    "VideoMetadata",
    "execute_command",
    "ffprobe_video",
]

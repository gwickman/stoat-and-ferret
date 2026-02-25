"""FFmpeg integration module for video probing and processing."""

from stoat_ferret.ffmpeg.executor import (
    ExecutionResult,
    FakeFFmpegExecutor,
    FFmpegExecutor,
    RealFFmpegExecutor,
    RecordingFFmpegExecutor,
)
from stoat_ferret.ffmpeg.metrics import (
    ffmpeg_active_processes,
    ffmpeg_execution_duration_seconds,
    ffmpeg_executions_total,
)
from stoat_ferret.ffmpeg.observable import ObservableFFmpegExecutor
from stoat_ferret.ffmpeg.probe import FFprobeError, VideoMetadata, ffprobe_video

__all__ = [
    "ExecutionResult",
    "FakeFFmpegExecutor",
    "FFmpegExecutor",
    "FFprobeError",
    "ObservableFFmpegExecutor",
    "RealFFmpegExecutor",
    "RecordingFFmpegExecutor",
    "VideoMetadata",
    "ffmpeg_active_processes",
    "ffmpeg_execution_duration_seconds",
    "ffmpeg_executions_total",
    "ffprobe_video",
]

"""FFmpeg integration module for video probing and processing."""

from stoat_ferret.ffmpeg.probe import FFprobeError, VideoMetadata, ffprobe_video

__all__ = [
    "FFprobeError",
    "VideoMetadata",
    "ffprobe_video",
]

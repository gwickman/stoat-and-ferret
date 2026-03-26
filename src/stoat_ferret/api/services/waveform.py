"""Waveform generation service using FFmpeg showwavespic and astats filters."""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.db.models import Waveform, WaveformFormat, WaveformStatus
from stoat_ferret.ffmpeg.async_executor import ProgressInfo

if TYPE_CHECKING:
    from stoat_ferret.api.websocket.manager import ConnectionManager
    from stoat_ferret.ffmpeg.async_executor import AsyncFFmpegExecutor

logger = structlog.get_logger(__name__)

# Progress throttle constants
_PROGRESS_MIN_INTERVAL_S = 0.5
_PROGRESS_MIN_DELTA = 0.05

# Samples per second for astats JSON output (44100 Hz / 4410 = 10 samples/s)
_ASTATS_SAMPLES_PER_SECOND = 4410


def escape_path_for_amovie(path: str) -> str:
    """Escape a file path for use in FFmpeg amovie= filter parameter.

    On Windows, backslashes must be replaced with forward slashes
    to avoid escaping issues in FFmpeg filter expressions.

    Args:
        path: The file path to escape.

    Returns:
        The escaped path safe for use in amovie= filter.
    """
    return path.replace("\\", "/")


def build_png_ffmpeg_args(
    video_path: str,
    output_path: str,
    *,
    width: int = 1800,
    height: int = 140,
    channels: int = 1,
) -> list[str]:
    """Build FFmpeg arguments for PNG waveform generation via showwavespic.

    Args:
        video_path: Path to the source video/audio file.
        output_path: Path for the output PNG file.
        width: Output image width in pixels.
        height: Output image height in pixels.
        channels: Number of audio channels (1=mono, 2=stereo).

    Returns:
        List of FFmpeg arguments.
    """
    layout = "stereo" if channels >= 2 else "mono"
    colors = "blue|red" if channels >= 2 else "blue"
    af = f"aformat=channel_layouts={layout},showwavespic=s={width}x{height}:colors={colors}"
    return [
        "-i",
        video_path,
        "-filter_complex",
        af,
        "-frames:v",
        "1",
        "-y",
        output_path,
    ]


def build_json_ffmpeg_args(
    video_path: str,
) -> list[str]:
    """Build ffprobe arguments for JSON waveform data via astats.

    Uses amovie to load the file, asetnsamples for 10 samples/second,
    and astats to extract Peak_level and RMS_level metadata.

    Args:
        video_path: Path to the source video/audio file.

    Returns:
        List of ffprobe arguments.
    """
    escaped_path = escape_path_for_amovie(video_path)
    samples = _ASTATS_SAMPLES_PER_SECOND
    af = f"amovie={escaped_path},asetnsamples={samples},astats=metadata=1:reset=1"
    return [
        "-f",
        "lavfi",
        "-i",
        af,
        "-show_entries",
        "frame_tags=lavfi.astats.Overall.Peak_level,lavfi.astats.Overall.RMS_level,"
        "lavfi.astats.1.Peak_level,lavfi.astats.1.RMS_level,"
        "lavfi.astats.2.Peak_level,lavfi.astats.2.RMS_level",
        "-of",
        "json",
        "-v",
        "quiet",
    ]


def parse_astats_output(raw_output: str) -> list[dict[str, str]]:
    """Parse ffprobe astats JSON output into amplitude samples.

    Each frame in the ffprobe output contains tags with Peak_level and
    RMS_level values as strings (decimal dB values).

    Args:
        raw_output: Raw JSON string from ffprobe output.

    Returns:
        List of dicts with Peak_level and RMS_level string values.
    """
    try:
        data = json.loads(raw_output)
    except json.JSONDecodeError:
        logger.warning("astats_parse_error", raw_length=len(raw_output))
        return []

    frames = data.get("frames", [])
    samples: list[dict[str, str]] = []

    for frame in frames:
        tags = frame.get("tags", {})
        sample: dict[str, str] = {}

        # Overall levels
        peak = tags.get("lavfi.astats.Overall.Peak_level")
        rms = tags.get("lavfi.astats.Overall.RMS_level")
        if peak is not None:
            sample["Peak_level"] = str(peak)
        if rms is not None:
            sample["RMS_level"] = str(rms)

        # Per-channel levels (channel 1)
        peak_1 = tags.get("lavfi.astats.1.Peak_level")
        rms_1 = tags.get("lavfi.astats.1.RMS_level")
        if peak_1 is not None:
            sample["ch1_Peak_level"] = str(peak_1)
        if rms_1 is not None:
            sample["ch1_RMS_level"] = str(rms_1)

        # Per-channel levels (channel 2)
        peak_2 = tags.get("lavfi.astats.2.Peak_level")
        rms_2 = tags.get("lavfi.astats.2.RMS_level")
        if peak_2 is not None:
            sample["ch2_Peak_level"] = str(peak_2)
        if rms_2 is not None:
            sample["ch2_RMS_level"] = str(rms_2)

        if sample:
            samples.append(sample)

    return samples


class WaveformService:
    """Generate audio waveform visualizations using FFmpeg.

    Produces PNG images via showwavespic filter and JSON amplitude
    data via astats filter for audio visualization in the timeline.

    Args:
        async_executor: Async FFmpeg executor for waveform generation.
        ffprobe_executor: Async executor for ffprobe JSON extraction.
        waveform_dir: Directory to store generated waveform files.
        ws_manager: Optional WebSocket manager for progress broadcasting.
    """

    def __init__(
        self,
        async_executor: AsyncFFmpegExecutor,
        waveform_dir: str | Path,
        *,
        ffprobe_executor: AsyncFFmpegExecutor | None = None,
        ws_manager: ConnectionManager | None = None,
    ) -> None:
        self._async_executor = async_executor
        self._ffprobe_executor = ffprobe_executor
        self._waveform_dir = Path(waveform_dir)
        self._ws_manager = ws_manager
        self._waveforms: dict[str, Waveform] = {}  # keyed by "{video_id}:{format}"

    def get_waveform(self, video_id: str, fmt: WaveformFormat) -> Waveform | None:
        """Get waveform metadata for a video and format.

        Args:
            video_id: Source video ID.
            fmt: Waveform format (png or json).

        Returns:
            Waveform if one has been generated, or None.
        """
        return self._waveforms.get(f"{video_id}:{fmt.value}")

    async def generate_png(
        self,
        *,
        video_id: str,
        video_path: str,
        duration_seconds: float,
        channels: int = 1,
        width: int = 1800,
        height: int = 140,
        waveform_id: str | None = None,
    ) -> Waveform:
        """Generate a PNG waveform image using FFmpeg showwavespic.

        Args:
            video_id: Source video ID.
            video_path: Path to the source video file.
            duration_seconds: Audio duration in seconds.
            channels: Number of audio channels (1=mono, 2=stereo).
            width: Output image width in pixels.
            height: Output image height in pixels.
            waveform_id: Optional pre-generated waveform ID.

        Returns:
            The completed Waveform metadata.

        Raises:
            RuntimeError: If FFmpeg fails.
        """
        wid = waveform_id or Waveform.new_id()
        waveform = Waveform(
            id=wid,
            video_id=video_id,
            format=WaveformFormat.PNG,
            status=WaveformStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            duration=duration_seconds,
            channels=channels,
        )

        key = f"{video_id}:{WaveformFormat.PNG.value}"
        self._waveforms[key] = waveform
        waveform.status = WaveformStatus.GENERATING

        # Prepare output directory
        self._waveform_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(self._waveform_dir / f"{wid}.png")

        args = build_png_ffmpeg_args(
            video_path,
            output_path,
            width=width,
            height=height,
            channels=channels,
        )

        # Build progress callback
        duration_us = int(duration_seconds * 1_000_000)
        progress_cb = self._make_progress_callback(
            waveform_id=wid,
            video_id=video_id,
            duration_us=duration_us,
        )

        start_time = time.monotonic()
        try:
            result = await self._async_executor.run(
                args,
                progress_callback=progress_cb,
            )
        except Exception:
            waveform.status = WaveformStatus.ERROR
            logger.error(
                "waveform_generation_error",
                waveform_id=wid,
                video_id=video_id,
                format="png",
                exc_info=True,
            )
            raise RuntimeError("Waveform PNG generation failed") from None

        generation_time = time.monotonic() - start_time

        if result.returncode != 0:
            waveform.status = WaveformStatus.ERROR
            error_msg = result.stderr.decode("utf-8", errors="replace")[:500]
            logger.error(
                "waveform_generation_failed",
                waveform_id=wid,
                video_id=video_id,
                format="png",
                returncode=result.returncode,
                error=error_msg,
            )
            raise RuntimeError(f"FFmpeg failed with code {result.returncode}: {error_msg}")

        # Update waveform metadata on success
        waveform.status = WaveformStatus.READY
        waveform.file_path = output_path

        logger.info(
            "waveform_generated",
            waveform_id=wid,
            video_id=video_id,
            format="png",
            duration=duration_seconds,
            channels=channels,
            duration_ms=round(generation_time * 1000, 1),
        )

        # Send completion progress event
        await self._send_progress(
            waveform_id=wid,
            video_id=video_id,
            progress=1.0,
            status="complete",
        )

        return waveform

    async def generate_json(
        self,
        *,
        video_id: str,
        video_path: str,
        duration_seconds: float,
        channels: int = 1,
        waveform_id: str | None = None,
    ) -> Waveform:
        """Generate JSON waveform amplitude data using ffprobe astats.

        Args:
            video_id: Source video ID.
            video_path: Path to the source video file.
            duration_seconds: Audio duration in seconds.
            channels: Number of audio channels (1=mono, 2=stereo).
            waveform_id: Optional pre-generated waveform ID.

        Returns:
            The completed Waveform metadata.

        Raises:
            RuntimeError: If no ffprobe executor is configured or ffprobe fails.
        """
        if self._ffprobe_executor is None:
            raise RuntimeError("ffprobe executor required for JSON waveform generation")

        wid = waveform_id or Waveform.new_id()
        waveform = Waveform(
            id=wid,
            video_id=video_id,
            format=WaveformFormat.JSON,
            status=WaveformStatus.PENDING,
            created_at=datetime.now(timezone.utc),
            duration=duration_seconds,
            channels=channels,
        )

        key = f"{video_id}:{WaveformFormat.JSON.value}"
        self._waveforms[key] = waveform
        waveform.status = WaveformStatus.GENERATING

        # Prepare output directory
        self._waveform_dir.mkdir(parents=True, exist_ok=True)
        output_path = str(self._waveform_dir / f"{wid}.json")

        args = build_json_ffmpeg_args(video_path)

        # Build progress callback
        duration_us = int(duration_seconds * 1_000_000)
        progress_cb = self._make_progress_callback(
            waveform_id=wid,
            video_id=video_id,
            duration_us=duration_us,
        )

        start_time = time.monotonic()
        try:
            result = await self._ffprobe_executor.run(
                args,
                progress_callback=progress_cb,
            )
        except Exception:
            waveform.status = WaveformStatus.ERROR
            logger.error(
                "waveform_generation_error",
                waveform_id=wid,
                video_id=video_id,
                format="json",
                exc_info=True,
            )
            raise RuntimeError("Waveform JSON generation failed") from None

        generation_time = time.monotonic() - start_time

        if result.returncode != 0:
            waveform.status = WaveformStatus.ERROR
            error_msg = result.stderr.decode("utf-8", errors="replace")[:500]
            logger.error(
                "waveform_generation_failed",
                waveform_id=wid,
                video_id=video_id,
                format="json",
                returncode=result.returncode,
                error=error_msg,
            )
            raise RuntimeError(f"ffprobe failed with code {result.returncode}: {error_msg}")

        # Parse astats output and write JSON file
        raw_output = result.stdout.decode("utf-8", errors="replace")
        samples = parse_astats_output(raw_output)

        output_data = {
            "video_id": video_id,
            "channels": channels,
            "samples_per_second": 10,
            "frames": samples,
        }

        Path(output_path).write_text(json.dumps(output_data, indent=2))

        # Update waveform metadata on success
        waveform.status = WaveformStatus.READY
        waveform.file_path = output_path

        logger.info(
            "waveform_generated",
            waveform_id=wid,
            video_id=video_id,
            format="json",
            duration=duration_seconds,
            channels=channels,
            duration_ms=round(generation_time * 1000, 1),
        )

        # Send completion progress event
        await self._send_progress(
            waveform_id=wid,
            video_id=video_id,
            progress=1.0,
            status="complete",
        )

        return waveform

    def _make_progress_callback(
        self,
        *,
        waveform_id: str,
        video_id: str,
        duration_us: int,
    ) -> Any:
        """Create a throttled progress callback for waveform generation.

        Args:
            waveform_id: Waveform ID.
            video_id: Source video ID.
            duration_us: Audio duration in microseconds.

        Returns:
            Async callback function for ProgressInfo updates.
        """
        last_progress = 0.0
        last_time = 0.0

        async def on_progress(info: ProgressInfo) -> None:
            nonlocal last_progress, last_time

            if duration_us <= 0:
                return

            progress = min(info.out_time_us / duration_us, 1.0)
            now = time.monotonic()

            time_delta = now - last_time
            progress_delta = progress - last_progress
            if time_delta < _PROGRESS_MIN_INTERVAL_S and progress_delta < _PROGRESS_MIN_DELTA:
                return

            last_progress = progress
            last_time = now

            await self._send_progress(
                waveform_id=waveform_id,
                video_id=video_id,
                progress=progress,
                status="generating",
            )

        return on_progress

    async def _send_progress(
        self,
        *,
        waveform_id: str,
        video_id: str,
        progress: float,
        status: str,
    ) -> None:
        """Send a waveform generation progress event via WebSocket.

        Args:
            waveform_id: Waveform ID.
            video_id: Source video ID.
            progress: Progress value 0.0-1.0.
            status: Generation status string.
        """
        if self._ws_manager is not None:
            await self._ws_manager.broadcast(
                build_event(
                    EventType.JOB_PROGRESS,
                    {
                        "job_type": "waveform",
                        "waveform_id": waveform_id,
                        "video_id": video_id,
                        "progress": progress,
                        "status": status,
                    },
                )
            )

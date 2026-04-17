"""Contract tests for render output format and encoder detection.

Validates that render commands produce valid output files in all 4 supported
formats (mp4, webm, mov, mkv) using real FFmpeg execution with lavfi virtual
inputs (LRN-100), and that the encoder detection parser correctly identifies
software encoders from real FFmpeg output.

Also verifies the RENDER_PROGRESS WebSocket event schema includes the enriched
fields: frame_count, fps, encoder_name, encoder_type (BL-254).

Also verifies the frame streaming endpoint and render.frame_available
throttling behaviour for Theater Mode (BL-255).
"""

from __future__ import annotations

import io
import json
import shutil
import subprocess
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from PIL import Image

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.ffmpeg.executor import RealFFmpegExecutor
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService
from stoat_ferret_core import detect_hardware_encoders
from tests.conftest import requires_ffmpeg


@pytest.fixture(scope="session")
def ffmpeg_encoder_output() -> str:
    """Capture real ``ffmpeg -encoders`` output once per test session.

    Used by encoder detection contract tests to avoid re-running FFmpeg for
    each test method and to provide a stable snapshot for regression comparison.

    Returns:
        The raw stdout from ``ffmpeg -encoders``.
    """
    result = subprocess.run(
        ["ffmpeg", "-encoders"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    return result.stdout


def _run_ffprobe(output_path: Path) -> dict:
    """Run ffprobe on the output file and return parsed JSON.

    Args:
        output_path: Path to the file to probe.

    Returns:
        Parsed ffprobe JSON output with format and streams keys.

    Raises:
        pytest.skip.Exception: If ffprobe is not available.
    """
    if shutil.which("ffprobe") is None:
        pytest.skip("ffprobe not available — skipping codec/container validation")
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(output_path),
        ],
        capture_output=True,
        timeout=10,
        check=False,
    )
    assert probe.returncode == 0, (
        f"ffprobe failed: {probe.stderr.decode('utf-8', errors='replace')}"
    )
    return json.loads(probe.stdout)  # type: ignore[no-any-return]


@requires_ffmpeg
@pytest.mark.contract
class TestRenderOutputFormatContract:
    """Render commands produce valid output files in all 4 supported formats."""

    @pytest.mark.parametrize(
        "output_ext,video_codec,format_flag,expected_codec,expected_format",
        [
            ("mp4", "libx264", "mp4", "h264", "mp4"),
            ("webm", "libvpx-vp9", "webm", "vp9", "webm"),
            ("mov", "libx264", "mov", "h264", "mov"),
            ("mkv", "libx265", "matroska", "hevc", "matroska"),
        ],
        ids=["mp4", "webm", "mov", "mkv"],
    )
    def test_render_format_produces_valid_output(
        self,
        tmp_path: Path,
        output_ext: str,
        video_codec: str,
        format_flag: str,
        expected_codec: str,
        expected_format: str,
    ) -> None:
        """Render command produces a valid file with correct codec and container.

        Uses lavfi testsrc2 virtual input to avoid requiring real media files.
        Validates the output via ffprobe for codec name and container format.
        """
        output_path = tmp_path / f"output.{output_ext}"

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "testsrc2=duration=1:size=320x240:rate=24",
                "-c:v",
                video_codec,
                "-an",
                "-t",
                "1",
                "-f",
                format_flag,
                "-y",
                str(output_path),
            ],
            timeout=30,
        )

        assert result.returncode == 0, (
            f"FFmpeg render failed for {output_ext} ({video_codec}): "
            f"{result.stderr.decode('utf-8', errors='replace')}"
        )
        assert output_path.exists(), f"Output file not created for {output_ext}"
        assert output_path.stat().st_size > 0, f"Output file is empty for {output_ext}"

        probe_data = _run_ffprobe(output_path)

        # Validate container format — ffprobe returns comma-separated format names
        format_name = probe_data.get("format", {}).get("format_name", "")
        format_names = format_name.split(",")
        assert expected_format in format_names, (
            f"Expected format '{expected_format}' in ffprobe "
            f"format_name '{format_name}' for {output_ext}"
        )

        # Validate video codec
        video_streams = [s for s in probe_data.get("streams", []) if s.get("codec_type") == "video"]
        assert len(video_streams) >= 1, f"No video streams found in {output_ext} output"
        codec_name = video_streams[0].get("codec_name", "")
        assert codec_name == expected_codec, (
            f"Expected video codec '{expected_codec}', got '{codec_name}' in {output_ext}"
        )


@requires_ffmpeg
@pytest.mark.contract
class TestRenderEdgeCases:
    """Edge case validation for render command behaviour."""

    def test_unavailable_codec_fails(self, tmp_path: Path) -> None:
        """FFmpeg returns non-zero when a nonexistent video codec is requested."""
        output_path = tmp_path / "bad_codec.mp4"

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "testsrc2=duration=1:size=320x240:rate=24",
                "-c:v",
                "nonexistent_codec_xyz_abc",
                "-an",
                "-f",
                "mp4",
                "-y",
                str(output_path),
            ],
            timeout=10,
        )

        assert result.returncode != 0, (
            "Expected FFmpeg to fail with a nonexistent codec, but it succeeded"
        )

    def test_zero_duration_produces_no_video_frames(self, tmp_path: Path) -> None:
        """A zero-duration render produces a container with no encoded video frames.

        FFmpeg exits successfully but logs "Output file is empty, nothing was encoded"
        and writes only a minimal container stub (~261 bytes on this platform).
        """
        output_path = tmp_path / "zero_dur.mp4"

        real = RealFFmpegExecutor()
        result = real.run(
            [
                "-f",
                "lavfi",
                "-i",
                "testsrc2=duration=0:size=320x240:rate=24",
                "-c:v",
                "libx264",
                "-an",
                "-f",
                "mp4",
                "-y",
                str(output_path),
            ],
            timeout=10,
        )

        if result.returncode != 0:
            return  # FFmpeg rejected the zero-duration input outright — acceptable

        # FFmpeg succeeded but must have produced no usable video content.
        # The output is either absent or a minimal container stub with 0 frames.
        if not output_path.exists():
            return  # No output file created — acceptable

        if shutil.which("ffprobe") is None:
            # Without ffprobe, verify the file is tiny (header-only container)
            assert output_path.stat().st_size < 1024, (
                f"Zero-duration render produced unexpectedly large output: "
                f"{output_path.stat().st_size} bytes"
            )
            return

        probe = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                str(output_path),
            ],
            capture_output=True,
            timeout=10,
            check=False,
        )
        if probe.returncode == 0:
            data = json.loads(probe.stdout)
            video_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
            total_frames = sum(int(s.get("nb_frames", 0) or 0) for s in video_streams)
            assert total_frames == 0, (
                f"Expected 0 video frames for zero-duration render, got {total_frames}"
            )


@requires_ffmpeg
@pytest.mark.contract
class TestMultiSegmentConcatContract:
    """Multi-segment concat via FFmpeg concat demuxer produces continuous output.

    Validates FR-001 through FR-004: two lavfi segments are encoded to temporary
    mp4 files, an ffconcat manifest is written, FFmpeg concat runs, and the output
    duration matches the sum of the segment durations within 0.1 s tolerance.
    """

    def test_concat_duration_equals_sum_of_segments(self, tmp_path: Path) -> None:
        """Concat of two segments produces output with duration ≈ segment1 + segment2.

        FR-001: 2 segments created via lavfi, ffconcat manifest written.
        FR-002: Concat executed with RealFFmpegExecutor.
        FR-003: Output duration ≈ sum of inputs (0.1 s tolerance).
        FR-004: All inputs are lavfi virtual sources.
        NFR-001: Completes within 30 s using short 2 s segments.
        """
        real = RealFFmpegExecutor()

        # Encode two 2-second lavfi segments to mp4 with libx264
        seg1 = tmp_path / "seg1.mp4"
        seg2 = tmp_path / "seg2.mp4"
        segment_duration = 2

        for seg_path in (seg1, seg2):
            result = real.run(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    f"testsrc2=duration={segment_duration}:size=320x240:rate=24",
                    "-c:v",
                    "libx264",
                    "-an",
                    "-t",
                    str(segment_duration),
                    "-f",
                    "mp4",
                    "-y",
                    str(seg_path),
                ],
                timeout=30,
            )
            assert result.returncode == 0, (
                f"FFmpeg failed to create segment {seg_path.name}: "
                f"{result.stderr.decode('utf-8', errors='replace')}"
            )

        # Write ffconcat manifest using absolute paths (safe=0 required for abs paths)
        manifest = tmp_path / "concat.txt"
        manifest.write_text(
            f"ffconcat version 1.0\nfile '{seg1}'\nfile '{seg2}'\n",
            encoding="utf-8",
        )

        # Concatenate via concat demuxer
        output_path = tmp_path / "output.mp4"
        concat_result = real.run(
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(manifest),
                "-c",
                "copy",
                "-y",
                str(output_path),
            ],
            timeout=30,
        )

        assert concat_result.returncode == 0, (
            f"FFmpeg concat failed: {concat_result.stderr.decode('utf-8', errors='replace')}"
        )
        assert output_path.exists(), "Concat output file was not created"
        assert output_path.stat().st_size > 0, "Concat output file is empty"

        # Validate duration via ffprobe
        probe_data = _run_ffprobe(output_path)
        duration_str = probe_data.get("format", {}).get("duration", "")
        assert duration_str, "ffprobe returned no duration for concat output"
        actual_duration = float(duration_str)
        expected_duration = float(segment_duration * 2)
        assert abs(actual_duration - expected_duration) <= 0.1, (
            f"Concat duration {actual_duration:.3f}s differs from expected "
            f"{expected_duration:.3f}s by more than 0.1 s"
        )


@requires_ffmpeg
@pytest.mark.contract
class TestEncoderDetectionContract:
    """Encoder detection parser correctly identifies encoders from real FFmpeg output.

    Stage 1 tests use the ``ffmpeg_encoder_output`` session fixture to validate
    the parser against the host's actual FFmpeg installation. Stage 2 tests use
    synthetic input to validate specific edge cases in the parser.
    """

    def test_software_encoders_detected(self, ffmpeg_encoder_output: str) -> None:
        """Real ``ffmpeg -encoders`` output contains expected software encoders.

        FR-001, FR-002, FR-003: Runs ``ffmpeg -encoders``, parses via
        ``detect_hardware_encoders``, and asserts libx264, libx265, and
        libvpx-vp9 are in the results.
        """
        encoders = detect_hardware_encoders(ffmpeg_encoder_output)
        names = {enc.name for enc in encoders}

        assert "libx264" in names, f"libx264 not found in detected encoders: {sorted(names)}"
        assert "libx265" in names, f"libx265 not found in detected encoders: {sorted(names)}"
        assert "libvpx-vp9" in names, f"libvpx-vp9 not found in detected encoders: {sorted(names)}"

    def test_encoder_output_captured_for_regression(self, ffmpeg_encoder_output: str) -> None:
        """Captured ``ffmpeg -encoders`` output is non-empty and yields parseable results.

        FR-004: The session fixture stores the captured output; this test asserts the
        snapshot is non-empty so any future format change that breaks parsing is detected.
        """
        assert len(ffmpeg_encoder_output) > 0, (
            "ffmpeg -encoders produced no stdout — output may have gone to stderr"
        )
        encoders = detect_hardware_encoders(ffmpeg_encoder_output)
        assert len(encoders) > 0, (
            "detect_hardware_encoders returned no video encoders from real FFmpeg output"
        )

    def test_audio_only_lines_filtered(self) -> None:
        """Audio encoder lines (``A`` type flag) are excluded from detection results.

        FR-005: Edge case — the ``A`` type flag must be filtered; only ``V`` lines
        are returned.
        """
        synthetic = (
            "Encoders:\n"
            " V..... = Video\n"
            " A..... = Audio\n"
            " ------\n"
            " A..... aac                  AAC (Advanced Audio Coding)\n"
            " A..... mp3lame              libmp3lame MP3 (MPEG audio layer 3)\n"
            " VFS... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10\n"
        )
        encoders = detect_hardware_encoders(synthetic)
        names = [enc.name for enc in encoders]

        assert "aac" not in names, "Audio encoder 'aac' should be filtered out (A flag)"
        assert "mp3lame" not in names, "Audio encoder 'mp3lame' should be filtered out (A flag)"
        assert "libx264" in names, "Video encoder 'libx264' should be included (V flag)"

    def test_optional_codec_suffix_extracted(self) -> None:
        """Encoder with ``(codec xxx)`` suffix uses extracted codec, not encoder name.

        FR-005: Edge case — when ``(codec xxx)`` is present, the codec field must be
        the extracted value; when absent, the encoder name is used as the codec.
        """
        synthetic = (
            "Encoders:\n"
            " ------\n"
            " V..... h264_nvenc           NVIDIA NVENC H.264 encoder (codec h264)\n"
            " VFS... libx264              libx264 H.264 / AVC / MPEG-4 AVC / MPEG-4 part 10\n"
        )
        encoders = detect_hardware_encoders(synthetic)
        by_name = {enc.name: enc for enc in encoders}

        assert "h264_nvenc" in by_name, "h264_nvenc should be detected"
        assert by_name["h264_nvenc"].codec == "h264", (
            f"Expected codec 'h264' for h264_nvenc (from suffix), "
            f"got '{by_name['h264_nvenc'].codec}'"
        )

        assert "libx264" in by_name, "libx264 should be detected"
        assert by_name["libx264"].codec == "libx264", (
            f"Expected codec 'libx264' for libx264 (no suffix, falls back to name), "
            f"got '{by_name['libx264'].codec}'"
        )

    def test_varying_flag_positions_parsed(self) -> None:
        """Encoders with varying flag combinations are all correctly parsed.

        FR-005: Edge case — flag slots 2-6 (F, S, X, B, D) may be set or unset
        in any combination; the parser must handle all variants.
        """
        synthetic = (
            "Encoders:\n"
            " ------\n"
            # Minimal flags (no optional capabilities)
            " V..... av1_amf              AMD AMF AV1 encoder (codec av1)\n"
            # Frame-level multithreading only
            " VF.... h264_amf             AMD AMF H.264 encoder (codec h264)\n"
            # Frame + slice multithreading
            " VFS... libx265              libx265 H.265 / HEVC\n"
            # All six flags set
            " VFSXBD libvpx-vp9           libvpx VP9\n"
        )
        encoders = detect_hardware_encoders(synthetic)
        by_name = {enc.name: enc for enc in encoders}

        assert "av1_amf" in by_name, "Encoder with minimal flags (V.....) should be parsed"
        assert "h264_amf" in by_name, "Encoder with F flag (VF....) should be parsed"
        assert "libx265" in by_name, "Encoder with FS flags (VFS...) should be parsed"
        assert "libvpx-vp9" in by_name, "Encoder with all flags (VFSXBD) should be parsed"

        # Hardware classification: AMF suffix → hardware; lib prefix → software
        assert by_name["h264_amf"].is_hardware is True, (
            "h264_amf should be classified as hardware (AMF suffix)"
        )
        assert by_name["libx265"].is_hardware is False, (
            "libx265 should be classified as software (no hardware suffix)"
        )


def _build_render_service() -> tuple[RenderService, ConnectionManager]:
    """Build a minimal RenderService with a mock WebSocket manager.

    Returns:
        Tuple of (service, ws_manager) where ws_manager.broadcast is an AsyncMock.
    """
    repo = InMemoryRenderRepository()
    ws: ConnectionManager = MagicMock(spec=ConnectionManager)
    ws.broadcast = AsyncMock()
    checkpoint_mgr = MagicMock()
    checkpoint_mgr.recover = AsyncMock(return_value=[])
    checkpoint_mgr.cleanup_stale = AsyncMock(return_value=0)
    queue = RenderQueue(repo, max_concurrent=4, max_depth=50)
    service = RenderService(
        repository=repo,
        queue=queue,
        executor=RenderExecutor(),
        checkpoint_manager=checkpoint_mgr,
        connection_manager=ws,
        settings=Settings(render_retry_count=0),
    )
    return service, ws


@pytest.mark.contract
class TestRenderProgressEnrichedSchema:
    """RENDER_PROGRESS WebSocket event carries enriched fields (BL-254).

    Validates that the WebSocket broadcast payload includes frame_count, fps,
    encoder_name, and encoder_type fields as required by FR-001 through FR-005.
    """

    async def test_progress_event_includes_enriched_fields(self) -> None:
        """_broadcast_throttled_progress emits frame_count, fps, encoder_name, encoder_type.

        FR-001: frame_count present; FR-002: fps present;
        FR-003: encoder_name present; FR-004: encoder_type present.
        """
        service, ws = _build_render_service()

        await service._broadcast_throttled_progress(
            "job-1",
            0.5,
            eta_seconds=30.0,
            speed_ratio=1.2,
            frame_count=600,
            fps=29.97,
            encoder_name="libx264",
            encoder_type="SW",
        )

        ws.broadcast.assert_called_once()
        event = ws.broadcast.call_args[0][0]
        payload = event["payload"]

        assert payload["job_id"] == "job-1"
        assert payload["progress"] == 0.5
        assert payload["frame_count"] == 600
        assert abs(payload["fps"] - 29.97) < 1e-6
        assert payload["encoder_name"] == "libx264"
        assert payload["encoder_type"] == "SW"

    async def test_progress_event_null_fields_do_not_raise(self) -> None:
        """Null enriched fields are serialised without error.

        FR-005: nullable fields must not cause parsing errors in consumers.
        """
        service, ws = _build_render_service()

        await service._broadcast_throttled_progress(
            "job-2",
            0.3,
            frame_count=None,
            fps=None,
            encoder_name=None,
            encoder_type=None,
        )

        ws.broadcast.assert_called_once()
        event = ws.broadcast.call_args[0][0]
        payload = event["payload"]

        assert payload["frame_count"] is None
        assert payload["fps"] is None
        assert payload["encoder_name"] is None
        assert payload["encoder_type"] is None

        # Confirm the entire payload is JSON-serialisable
        serialised = json.dumps(event)
        assert "frame_count" in serialised
        assert "encoder_name" in serialised

    async def test_hardware_encoder_type_emitted(self) -> None:
        """encoder_type is 'HW' when a hardware encoder name is provided.

        FR-004: encoder_type carries 'HW', 'SW', or null.
        """
        service, ws = _build_render_service()

        await service._broadcast_throttled_progress(
            "job-3",
            0.6,
            encoder_name="h264_nvenc",
            encoder_type="HW",
        )

        event = ws.broadcast.call_args[0][0]
        assert event["payload"]["encoder_type"] == "HW"

    async def test_final_progress_always_broadcast(self) -> None:
        """Final progress (1.0) is always broadcast regardless of throttle state.

        NFR-001: callback overhead — final event bypasses throttle gate.
        """
        service, ws = _build_render_service()

        # First call sets throttle state
        await service._broadcast_throttled_progress("job-4", 0.5)
        first_call_count = ws.broadcast.call_count

        # Final progress must be broadcast even within throttle window
        await service._broadcast_throttled_progress(
            "job-4",
            1.0,
            frame_count=1200,
            fps=24.0,
            encoder_name="libx264",
            encoder_type="SW",
        )

        assert ws.broadcast.call_count == first_call_count + 1, (
            "Final progress (1.0) must be broadcast even within throttle window"
        )
        final_event = ws.broadcast.call_args[0][0]
        assert final_event["payload"]["progress"] == 1.0
        assert final_event["payload"]["frame_count"] == 1200


def _make_minimal_jpeg(width: int = 960, height: int = 540) -> bytes:
    """Build a minimal in-memory JPEG at the given dimensions.

    Args:
        width: Image width in pixels.
        height: Image height in pixels.

    Returns:
        Raw JPEG bytes.
    """
    img = Image.new("RGB", (width, height), color=(128, 64, 32))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return buf.getvalue()


def _make_test_app_with_service(service: RenderService) -> FastAPI:
    """Build a FastAPI test app with a real render service wired in.

    Args:
        service: The RenderService instance to inject.

    Returns:
        A FastAPI app with render_service set on app.state.
    """
    repo = InMemoryRenderRepository()
    app = create_app(
        render_repository=repo,
        render_service=service,
    )
    return app


@pytest.mark.contract
class TestFrameStreamingContract:
    """Frame streaming endpoint and event throttling for Theater Mode (BL-255).

    Verifies that:
    - GET /render/{job_id}/frame_preview.jpg returns 200 + valid JPEG when
      a frame is cached in the service frame buffer.
    - GET /render/{job_id}/frame_preview.jpg returns 404 when no frame is cached.
    - render.frame_available events are throttled to ≤2/sec.
    - Each render.frame_available event carries the expected payload schema.
    """

    def test_render_frame_preview_endpoint_returns_jpeg(self) -> None:
        """Frame endpoint returns HTTP 200 with valid 540p JPEG when buffer populated.

        FR-002: GET /api/v1/render/{job_id}/frame_preview.jpg returns 540p JPEG.
        NFR-002: Response carries image/jpeg content-type.
        """
        service, _ = _build_render_service()
        job_id = "frame-test-job-1"
        jpeg_bytes = _make_minimal_jpeg(960, 540)
        service._frame_buffer[job_id] = jpeg_bytes

        app = _make_test_app_with_service(service)
        with TestClient(app) as client:
            resp = client.get(f"/api/v1/render/{job_id}/frame_preview.jpg")

        assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
        assert resp.headers["content-type"] == "image/jpeg", (
            f"Expected image/jpeg, got {resp.headers['content-type']}"
        )

        # Validate the returned bytes are a valid JPEG at the expected dimensions
        returned_img = Image.open(io.BytesIO(resp.content))
        assert returned_img.format == "JPEG", f"Expected JPEG format, got {returned_img.format}"
        assert returned_img.height == 540, f"Expected height=540, got {returned_img.height}"

    def test_render_frame_preview_endpoint_returns_404_when_no_frame(self) -> None:
        """Frame endpoint returns 404 when no frame is cached for the job.

        NFR-004: Graceful fallback — endpoint returns 404 when frame capture
        unavailable (e.g., encoder does not support mid-render extraction).
        """
        service, _ = _build_render_service()
        job_id = "no-frame-job"

        app = _make_test_app_with_service(service)
        with TestClient(app) as client:
            resp = client.get(f"/api/v1/render/{job_id}/frame_preview.jpg")

        assert resp.status_code == 404, f"Expected 404 for missing frame, got {resp.status_code}"
        assert resp.json()["detail"]["code"] == "FRAME_UNAVAILABLE"

    async def test_frame_events_emitted_and_throttled(self) -> None:
        """render.frame_available events are emitted and throttled to ≤2/sec.

        FR-001: Events emitted at throttled rate (≤2/sec = THROTTLE_INTERVAL=0.5s).
        NFR-001: At most 2 frame events per second.
        """
        service, ws = _build_render_service()

        # Fire multiple _broadcast_throttled_frame calls in rapid succession
        # All within the 0.5s throttle window — only the first should broadcast.
        await service._broadcast_throttled_frame("job-throttle-1", 0.1)
        await service._broadcast_throttled_frame("job-throttle-1", 0.2)
        await service._broadcast_throttled_frame("job-throttle-1", 0.3)

        # Exactly 1 frame event broadcast (throttle suppressed 2nd and 3rd)
        frame_calls = [
            c for c in ws.broadcast.call_args_list if c[0][0]["type"] == "render_frame_available"
        ]
        assert len(frame_calls) == 1, f"Expected 1 frame event (throttled), got {len(frame_calls)}"

    async def test_frame_event_payload_schema(self) -> None:
        """render.frame_available event carries required payload fields.

        FR-001: Events include job_id, frame_url, resolution, progress.
        """
        service, ws = _build_render_service()

        await service._broadcast_throttled_frame("job-schema-1", 0.42)

        frame_calls = [
            c for c in ws.broadcast.call_args_list if c[0][0]["type"] == "render_frame_available"
        ]
        assert len(frame_calls) == 1
        payload = frame_calls[0][0][0]["payload"]

        assert payload["job_id"] == "job-schema-1"
        assert payload["frame_url"] == "/api/v1/render/job-schema-1/frame_preview.jpg"
        assert payload["resolution"] == "540p"
        assert abs(payload["progress"] - 0.42) < 1e-6

    def test_frame_buffer_cleared_on_throttle_state_clear(self) -> None:
        """Frame buffer is cleared when job throttle state is cleared.

        Ensures no stale frame data persists after job completion.
        """
        service, _ = _build_render_service()
        job_id = "clear-test-job"
        service._frame_buffer[job_id] = _make_minimal_jpeg()
        assert service.get_frame_bytes(job_id) is not None

        service._clear_throttle_state(job_id)

        assert service.get_frame_bytes(job_id) is None, (
            "Frame buffer should be cleared after _clear_throttle_state"
        )

    def test_frame_endpoint_timing_under_100ms(self) -> None:
        """Frame endpoint responds in under 100ms when frame is pre-cached.

        NFR-002: Frame endpoint response time <100ms.
        """
        service, _ = _build_render_service()
        job_id = "timing-test-job"
        service._frame_buffer[job_id] = _make_minimal_jpeg()

        app = _make_test_app_with_service(service)
        with TestClient(app) as client:
            start = time.monotonic()
            resp = client.get(f"/api/v1/render/{job_id}/frame_preview.jpg")
            elapsed_ms = (time.monotonic() - start) * 1000

        assert resp.status_code == 200
        assert elapsed_ms < 100, (
            f"Frame endpoint took {elapsed_ms:.1f}ms — expected <100ms (NFR-002)"
        )

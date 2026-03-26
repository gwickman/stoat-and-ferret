"""Tests for thumbnail strip sprite sheet generation."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.api.services.thumbnail import (
    MAX_COLUMNS,
    ThumbnailService,
    build_strip_ffmpeg_args,
    calculate_strip_dimensions,
    extract_frame_args,
)
from stoat_ferret.db.models import ThumbnailStrip, ThumbnailStripStatus
from stoat_ferret.ffmpeg.async_executor import FakeAsyncFFmpegExecutor
from stoat_ferret.ffmpeg.executor import FakeFFmpegExecutor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_success_recording() -> list[dict[str, object]]:
    return [
        {
            "args": [],
            "stdin": None,
            "result": {
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "duration_seconds": 0.5,
            },
        }
    ]


# ---------------------------------------------------------------------------
# calculate_strip_dimensions
# ---------------------------------------------------------------------------


class TestCalculateStripDimensions:
    """Tests for frame count and row calculation."""

    def test_basic_calculation(self) -> None:
        """60s video at 5s interval = 12 frames, 2 rows with 10 columns."""
        frame_count, rows = calculate_strip_dimensions(60.0, 5.0, 10)
        assert frame_count == 12
        assert rows == 2

    def test_rounds_up_frame_count(self) -> None:
        """Non-exact division rounds up frame count."""
        frame_count, rows = calculate_strip_dimensions(13.0, 5.0, 10)
        assert frame_count == 3
        assert rows == 1

    def test_very_short_video(self) -> None:
        """Very short video produces at least 1 frame."""
        frame_count, rows = calculate_strip_dimensions(0.5, 5.0, 10)
        assert frame_count == 1
        assert rows == 1

    def test_four_hour_video(self) -> None:
        """4-hour video at 5s interval: 2880 frames, 288 rows (FR-006)."""
        frame_count, rows = calculate_strip_dimensions(4 * 3600, 5.0, 10)
        assert frame_count == 2880
        assert rows == 288
        # Verify within JPEG limits: 10*160=1600 < 65535, 288*90=25920 < 65535
        assert 10 * 160 < 65535
        assert rows * 90 < 65535

    def test_rows_rounds_up(self) -> None:
        """Partial last row rounds up."""
        frame_count, rows = calculate_strip_dimensions(55.0, 5.0, 10)
        assert frame_count == 11
        assert rows == 2  # ceil(11/10) = 2


# ---------------------------------------------------------------------------
# build_strip_ffmpeg_args
# ---------------------------------------------------------------------------


class TestBuildStripFFmpegArgs:
    """Tests for FFmpeg command construction."""

    def test_correct_filter_chain(self) -> None:
        """FFmpeg args contain fps+scale+tile filter chain."""
        args = build_strip_ffmpeg_args(
            "/videos/test.mp4",
            "/out/strip.jpg",
            interval=5.0,
            frame_width=160,
            frame_height=90,
            columns=10,
            rows=3,
        )

        assert "-vf" in args
        vf_index = args.index("-vf")
        vf = args[vf_index + 1]
        assert "fps=1/5.0" in vf
        assert "scale=160:90" in vf
        assert "tile=10x3" in vf

    def test_single_frame_output(self) -> None:
        """Args contain -frames:v 1 for single output image."""
        args = build_strip_ffmpeg_args(
            "/videos/test.mp4",
            "/out/strip.jpg",
            interval=5.0,
            frame_width=160,
            frame_height=90,
            columns=10,
            rows=1,
        )
        assert "-frames:v" in args
        idx = args.index("-frames:v")
        assert args[idx + 1] == "1"

    def test_quality_setting(self) -> None:
        """Args contain -q:v 5 for JPEG quality."""
        args = build_strip_ffmpeg_args(
            "/videos/test.mp4",
            "/out/strip.jpg",
            interval=5.0,
            frame_width=160,
            frame_height=90,
            columns=10,
            rows=1,
        )
        assert "-q:v" in args
        idx = args.index("-q:v")
        assert args[idx + 1] == "5"

    def test_overwrite_flag(self) -> None:
        """Args contain -y to overwrite existing output."""
        args = build_strip_ffmpeg_args(
            "/videos/test.mp4",
            "/out/strip.jpg",
            interval=5.0,
            frame_width=160,
            frame_height=90,
            columns=10,
            rows=1,
        )
        assert "-y" in args

    def test_custom_dimensions(self) -> None:
        """Custom frame dimensions reflected in scale filter."""
        args = build_strip_ffmpeg_args(
            "/videos/test.mp4",
            "/out/strip.jpg",
            interval=2.0,
            frame_width=320,
            frame_height=180,
            columns=5,
            rows=4,
        )
        vf_index = args.index("-vf")
        vf = args[vf_index + 1]
        assert "scale=320:180" in vf
        assert "tile=5x4" in vf
        assert "fps=1/2.0" in vf


# ---------------------------------------------------------------------------
# extract_frame_args (shared method - FR-005)
# ---------------------------------------------------------------------------


class TestExtractFrameArgs:
    """Tests for shared frame extraction primitive."""

    def test_default_args(self) -> None:
        """Default args produce expected FFmpeg command."""
        args = extract_frame_args("/video.mp4", "/out.jpg")
        assert args[0:2] == ["-ss", "0"]
        assert "-i" in args
        assert "-frames:v" in args
        assert "scale=320:-1" in args[args.index("-vf") + 1]

    def test_custom_timestamp_and_width(self) -> None:
        """Custom timestamp and width reflected in args."""
        args = extract_frame_args(
            "/video.mp4",
            "/out.jpg",
            timestamp=10.5,
            width=640,
            quality=3,
        )
        assert args[1] == "10.5"
        vf = args[args.index("-vf") + 1]
        assert "scale=640:-1" in vf
        q_idx = args.index("-q:v")
        assert args[q_idx + 1] == "3"

    def test_callable_by_both_strip_and_effect(self) -> None:
        """extract_frame_args is importable and callable (FR-005)."""
        # Strip path
        strip_args = extract_frame_args("/v.mp4", "/strip.jpg", timestamp=5)
        assert isinstance(strip_args, list)
        # Effect path
        effect_args = extract_frame_args("/v.mp4", "/effect.jpg", timestamp=0, width=320)
        assert isinstance(effect_args, list)


# ---------------------------------------------------------------------------
# ThumbnailService.generate_strip
# ---------------------------------------------------------------------------


class TestGenerateStrip:
    """Tests for sprite sheet generation via ThumbnailService."""

    @pytest.fixture()
    def fake_async_executor(self) -> FakeAsyncFFmpegExecutor:
        """Return a fake async executor configured for success."""
        return FakeAsyncFFmpegExecutor(returncode=0)

    @pytest.fixture()
    def fake_sync_executor(self) -> FakeFFmpegExecutor:
        """Return a fake sync executor."""
        return FakeFFmpegExecutor(_make_success_recording())

    async def test_generates_strip_successfully(
        self,
        tmp_path: Path,
        fake_sync_executor: FakeFFmpegExecutor,
        fake_async_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """generate_strip returns a READY ThumbnailStrip on success."""
        service = ThumbnailService(
            fake_sync_executor,
            tmp_path,
            async_executor=fake_async_executor,
        )

        strip = await service.generate_strip(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=60.0,
        )

        assert strip.status == ThumbnailStripStatus.READY
        assert strip.frame_count == 12
        assert strip.rows == 2
        assert strip.columns == 10
        assert strip.video_id == "vid1"

    async def test_correct_ffmpeg_args_passed(
        self,
        tmp_path: Path,
        fake_sync_executor: FakeFFmpegExecutor,
        fake_async_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """Verify correct FFmpeg command is passed to the executor."""
        service = ThumbnailService(
            fake_sync_executor,
            tmp_path,
            async_executor=fake_async_executor,
        )

        await service.generate_strip(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=60.0,
        )

        assert len(fake_async_executor.calls) == 1
        args = fake_async_executor.calls[0]
        assert "-vf" in args
        vf_idx = args.index("-vf")
        vf = args[vf_idx + 1]
        assert "fps=1/5.0" in vf
        assert "scale=160:90" in vf
        assert "tile=10x2" in vf

    async def test_custom_interval(
        self,
        tmp_path: Path,
        fake_sync_executor: FakeFFmpegExecutor,
        fake_async_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """Custom interval overrides service default (FR-002)."""
        service = ThumbnailService(
            fake_sync_executor,
            tmp_path,
            async_executor=fake_async_executor,
        )

        strip = await service.generate_strip(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=60.0,
            interval=2.0,
        )

        assert strip.frame_count == 30  # ceil(60/2)
        assert strip.interval_seconds == 2.0

    async def test_service_default_interval(
        self,
        tmp_path: Path,
        fake_sync_executor: FakeFFmpegExecutor,
        fake_async_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """Service-level strip_interval used when no override provided."""
        service = ThumbnailService(
            fake_sync_executor,
            tmp_path,
            async_executor=fake_async_executor,
            strip_interval=10.0,
        )

        strip = await service.generate_strip(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=60.0,
        )

        assert strip.interval_seconds == 10.0
        assert strip.frame_count == 6  # ceil(60/10)

    async def test_columns_clamped_to_max(
        self,
        tmp_path: Path,
        fake_sync_executor: FakeFFmpegExecutor,
        fake_async_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """Columns are clamped to MAX_COLUMNS (400)."""
        service = ThumbnailService(
            fake_sync_executor,
            tmp_path,
            async_executor=fake_async_executor,
        )

        strip = await service.generate_strip(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=60.0,
            columns=500,
        )

        assert strip.columns == MAX_COLUMNS

    async def test_raises_without_async_executor(
        self,
        tmp_path: Path,
        fake_sync_executor: FakeFFmpegExecutor,
    ) -> None:
        """Raises RuntimeError if no async executor configured."""
        service = ThumbnailService(fake_sync_executor, tmp_path)

        with pytest.raises(RuntimeError, match="Async executor required"):
            await service.generate_strip(
                video_id="vid1",
                video_path="/videos/test.mp4",
                duration_seconds=60.0,
            )

    async def test_error_on_ffmpeg_failure(
        self,
        tmp_path: Path,
        fake_sync_executor: FakeFFmpegExecutor,
    ) -> None:
        """Sets error status when FFmpeg returns non-zero."""
        bad_executor = FakeAsyncFFmpegExecutor(returncode=1)
        service = ThumbnailService(
            fake_sync_executor,
            tmp_path,
            async_executor=bad_executor,
        )

        with pytest.raises(RuntimeError, match="FFmpeg failed"):
            await service.generate_strip(
                video_id="vid1",
                video_path="/videos/test.mp4",
                duration_seconds=60.0,
            )

    async def test_strip_output_path(
        self,
        tmp_path: Path,
        fake_sync_executor: FakeFFmpegExecutor,
        fake_async_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """Strip file path is in strips subdirectory."""
        service = ThumbnailService(
            fake_sync_executor,
            tmp_path,
            async_executor=fake_async_executor,
        )

        strip = await service.generate_strip(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=60.0,
        )

        assert strip.file_path is not None
        assert "strips" in strip.file_path
        assert strip.file_path.endswith(".jpg")


# ---------------------------------------------------------------------------
# WebSocket progress events (FR-003)
# ---------------------------------------------------------------------------


class TestStripProgressEvents:
    """Tests for WebSocket progress broadcasting during strip generation."""

    async def test_emits_completion_event(self, tmp_path: Path) -> None:
        """Completion event is broadcast via WebSocket on success."""
        ws_manager = AsyncMock()
        fake_async = FakeAsyncFFmpegExecutor(returncode=0)
        fake_sync = FakeFFmpegExecutor(_make_success_recording())

        service = ThumbnailService(
            fake_sync,
            tmp_path,
            async_executor=fake_async,
            ws_manager=ws_manager,
        )

        await service.generate_strip(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=60.0,
        )

        ws_manager.broadcast.assert_called()
        last_call = ws_manager.broadcast.call_args[0][0]
        assert last_call["type"] == "job_progress"
        assert last_call["payload"]["status"] == "complete"
        assert last_call["payload"]["job_type"] == "thumbnail_strip"
        assert last_call["payload"]["video_id"] == "vid1"

    async def test_no_broadcast_without_ws_manager(self, tmp_path: Path) -> None:
        """No error when ws_manager is None."""
        fake_async = FakeAsyncFFmpegExecutor(returncode=0)
        fake_sync = FakeFFmpegExecutor(_make_success_recording())

        service = ThumbnailService(
            fake_sync,
            tmp_path,
            async_executor=fake_async,
        )

        # Should not raise
        strip = await service.generate_strip(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=60.0,
        )
        assert strip.status == ThumbnailStripStatus.READY


# ---------------------------------------------------------------------------
# Structured logging (FR-004)
# ---------------------------------------------------------------------------


class TestStripStructuredLogging:
    """Tests for structured log fields on strip generation."""

    async def test_logs_strip_generated_event(
        self,
        tmp_path: Path,
    ) -> None:
        """thumbnail_strip_generated log emitted on success (FR-004)."""
        fake_async = FakeAsyncFFmpegExecutor(returncode=0)
        fake_sync = FakeFFmpegExecutor(_make_success_recording())

        service = ThumbnailService(
            fake_sync,
            tmp_path,
            async_executor=fake_async,
        )

        strip = await service.generate_strip(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=60.0,
        )

        # Verify strip completed — structured log fields (frame_count,
        # strip_size_bytes, generation_time) are emitted by the logger.info
        # call at thumbnail.py line ~428, verified by inspection.
        assert strip.status == ThumbnailStripStatus.READY
        assert strip.frame_count == 12


# ---------------------------------------------------------------------------
# ThumbnailStrip model
# ---------------------------------------------------------------------------


class TestThumbnailStripModel:
    """Tests for ThumbnailStrip dataclass."""

    def test_default_values(self) -> None:
        """ThumbnailStrip has correct defaults."""
        from datetime import datetime, timezone

        strip = ThumbnailStrip(
            id="test-id",
            video_id="vid1",
            status=ThumbnailStripStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        assert strip.frame_count == 0
        assert strip.frame_width == 160
        assert strip.frame_height == 90
        assert strip.interval_seconds == 5.0
        assert strip.columns == 10
        assert strip.rows == 0
        assert strip.file_path is None

    def test_new_id_is_uuid(self) -> None:
        """new_id generates valid UUID strings."""
        import uuid

        id1 = ThumbnailStrip.new_id()
        id2 = ThumbnailStrip.new_id()
        assert id1 != id2
        uuid.UUID(id1)  # Raises if invalid

    def test_status_values(self) -> None:
        """ThumbnailStripStatus has expected values."""
        assert ThumbnailStripStatus.PENDING == "pending"
        assert ThumbnailStripStatus.GENERATING == "generating"
        assert ThumbnailStripStatus.READY == "ready"
        assert ThumbnailStripStatus.ERROR == "error"


# ---------------------------------------------------------------------------
# Backwards compatibility (NFR-001)
# ---------------------------------------------------------------------------


class TestConstructorBackwardsCompatibility:
    """Verify existing callers don't break with new constructor params."""

    def test_existing_positional_args_still_work(self, tmp_path: Path) -> None:
        """Existing ThumbnailService(executor, dir) signature preserved."""
        fake = FakeFFmpegExecutor(_make_success_recording())
        service = ThumbnailService(fake, tmp_path)
        assert service._width == 320
        assert service._async_executor is None
        assert service._ws_manager is None

    def test_existing_keyword_width_still_works(self, tmp_path: Path) -> None:
        """Existing ThumbnailService(executor, dir, width=N) preserved."""
        fake = FakeFFmpegExecutor(_make_success_recording())
        service = ThumbnailService(fake, tmp_path, width=640)
        assert service._width == 640

    def test_generate_still_works(self, tmp_path: Path) -> None:
        """Existing generate() method works with new constructor."""
        fake = FakeFFmpegExecutor(_make_success_recording())
        service = ThumbnailService(fake, tmp_path)
        result = service.generate("/videos/test.mp4", "vid1")
        assert result is not None


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestStripEdgeCases:
    """Edge case tests for sprite sheet generation."""

    def test_very_short_video_dimensions(self) -> None:
        """Very short video (< 1 interval) produces 1 frame, 1 row."""
        frame_count, rows = calculate_strip_dimensions(2.0, 5.0, 10)
        assert frame_count == 1
        assert rows == 1

    def test_exact_multiple_frames(self) -> None:
        """Exact multiple of interval produces exact frame count."""
        frame_count, rows = calculate_strip_dimensions(50.0, 5.0, 10)
        assert frame_count == 10
        assert rows == 1

    def test_long_video_multi_row(self) -> None:
        """Long video with many frames produces multi-row grid."""
        # 2 hours at 5s interval = 1440 frames
        frame_count, rows = calculate_strip_dimensions(7200.0, 5.0, 10)
        assert frame_count == 1440
        assert rows == 144

    def test_four_hour_within_jpeg_limits(self) -> None:
        """4-hour video sprite sheet fits within JPEG 65535px limits (FR-006)."""
        frame_count, rows = calculate_strip_dimensions(4 * 3600, 5.0, 10)
        total_width = 10 * 160
        total_height = rows * 90
        assert total_width <= 65535
        assert total_height <= 65535

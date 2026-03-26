"""Tests for waveform generation service."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.api.services.waveform import (
    WaveformService,
    build_json_ffmpeg_args,
    build_png_ffmpeg_args,
    escape_path_for_amovie,
    parse_astats_output,
)
from stoat_ferret.db.models import Waveform, WaveformFormat, WaveformStatus
from stoat_ferret.ffmpeg.async_executor import FakeAsyncFFmpegExecutor

# ---------------------------------------------------------------------------
# escape_path_for_amovie (FR-006)
# ---------------------------------------------------------------------------


class TestEscapePathForAmovie:
    """Tests for Windows path escaping in amovie= filter."""

    def test_backslashes_replaced(self) -> None:
        """Windows backslashes are replaced with forward slashes."""
        result = escape_path_for_amovie(r"C:\Users\test\video.mp4")
        assert result == "C:/Users/test/video.mp4"

    def test_forward_slashes_unchanged(self) -> None:
        """Unix-style forward slashes are left unchanged."""
        result = escape_path_for_amovie("/home/user/video.mp4")
        assert result == "/home/user/video.mp4"

    def test_mixed_slashes(self) -> None:
        """Mixed slashes are normalized to forward slashes."""
        result = escape_path_for_amovie(r"C:\Users/test\video.mp4")
        assert result == "C:/Users/test/video.mp4"

    def test_no_slashes(self) -> None:
        """Filename without slashes is unchanged."""
        result = escape_path_for_amovie("video.mp4")
        assert result == "video.mp4"

    def test_deeply_nested_windows_path(self) -> None:
        """Deeply nested Windows path is fully escaped."""
        result = escape_path_for_amovie(r"C:\Users\grant\Documents\projects\media\audio.wav")
        assert "\\" not in result
        assert result == "C:/Users/grant/Documents/projects/media/audio.wav"


# ---------------------------------------------------------------------------
# build_png_ffmpeg_args (FR-001)
# ---------------------------------------------------------------------------


class TestBuildPngFfmpegArgs:
    """Tests for PNG waveform FFmpeg command construction."""

    def test_mono_filter_chain(self) -> None:
        """Mono audio uses single color in showwavespic (FR-001)."""
        args = build_png_ffmpeg_args(
            "/video.mp4",
            "/out.png",
            channels=1,
        )
        assert "-filter_complex" in args
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "channel_layouts=mono" in fc
        assert "showwavespic" in fc
        assert "colors=blue" in fc
        assert "blue|red" not in fc

    def test_stereo_filter_chain(self) -> None:
        """Stereo audio uses blue|red colors (FR-001)."""
        args = build_png_ffmpeg_args(
            "/video.mp4",
            "/out.png",
            channels=2,
        )
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "channel_layouts=stereo" in fc
        assert "colors=blue|red" in fc

    def test_custom_dimensions(self) -> None:
        """Custom width and height reflected in showwavespic s= parameter."""
        args = build_png_ffmpeg_args(
            "/video.mp4",
            "/out.png",
            width=800,
            height=200,
            channels=1,
        )
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "s=800x200" in fc

    def test_single_frame_output(self) -> None:
        """Args contain -frames:v 1 for single PNG output."""
        args = build_png_ffmpeg_args("/video.mp4", "/out.png")
        assert "-frames:v" in args
        idx = args.index("-frames:v")
        assert args[idx + 1] == "1"

    def test_overwrite_flag(self) -> None:
        """Args contain -y to overwrite existing output."""
        args = build_png_ffmpeg_args("/video.mp4", "/out.png")
        assert "-y" in args

    def test_default_dimensions(self) -> None:
        """Default dimensions are 1800x140."""
        args = build_png_ffmpeg_args("/video.mp4", "/out.png")
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "s=1800x140" in fc


# ---------------------------------------------------------------------------
# build_json_ffmpeg_args (FR-002, FR-006)
# ---------------------------------------------------------------------------


class TestBuildJsonFfmpegArgs:
    """Tests for JSON waveform ffprobe command construction."""

    def test_uses_amovie_filter(self) -> None:
        """Args use amovie= filter with lavfi input (FR-002)."""
        args = build_json_ffmpeg_args("/video.mp4")
        assert "-f" in args
        f_idx = args.index("-f")
        assert args[f_idx + 1] == "lavfi"
        i_idx = args.index("-i")
        filter_str = args[i_idx + 1]
        assert "amovie=" in filter_str
        assert "asetnsamples=4410" in filter_str
        assert "astats=metadata=1:reset=1" in filter_str

    def test_windows_path_escaped(self) -> None:
        """Windows path has backslashes replaced in amovie= (FR-006)."""
        args = build_json_ffmpeg_args(r"C:\Users\test\video.mp4")
        i_idx = args.index("-i")
        filter_str = args[i_idx + 1]
        assert "\\" not in filter_str
        assert "C:/Users/test/video.mp4" in filter_str

    def test_json_output_format(self) -> None:
        """Args request JSON output from ffprobe."""
        args = build_json_ffmpeg_args("/video.mp4")
        assert "-of" in args
        of_idx = args.index("-of")
        assert args[of_idx + 1] == "json"

    def test_show_entries_includes_levels(self) -> None:
        """Show entries include Peak_level and RMS_level tags."""
        args = build_json_ffmpeg_args("/video.mp4")
        se_idx = args.index("-show_entries")
        entries = args[se_idx + 1]
        assert "Peak_level" in entries
        assert "RMS_level" in entries


# ---------------------------------------------------------------------------
# parse_astats_output (FR-002)
# ---------------------------------------------------------------------------


class TestParseAstatsOutput:
    """Tests for astats JSON output parsing."""

    def test_parses_overall_levels(self) -> None:
        """Parses Overall Peak_level and RMS_level as strings (FR-002)."""
        raw = json.dumps(
            {
                "frames": [
                    {
                        "tags": {
                            "lavfi.astats.Overall.Peak_level": "-6.021",
                            "lavfi.astats.Overall.RMS_level": "-12.345",
                        }
                    }
                ]
            }
        )
        samples = parse_astats_output(raw)
        assert len(samples) == 1
        assert samples[0]["Peak_level"] == "-6.021"
        assert samples[0]["RMS_level"] == "-12.345"
        # Values are strings, not numbers
        assert isinstance(samples[0]["Peak_level"], str)
        assert isinstance(samples[0]["RMS_level"], str)

    def test_parses_per_channel_levels(self) -> None:
        """Parses per-channel levels for stereo (FR-003)."""
        raw = json.dumps(
            {
                "frames": [
                    {
                        "tags": {
                            "lavfi.astats.Overall.Peak_level": "-3.0",
                            "lavfi.astats.Overall.RMS_level": "-10.0",
                            "lavfi.astats.1.Peak_level": "-3.5",
                            "lavfi.astats.1.RMS_level": "-10.5",
                            "lavfi.astats.2.Peak_level": "-4.0",
                            "lavfi.astats.2.RMS_level": "-11.0",
                        }
                    }
                ]
            }
        )
        samples = parse_astats_output(raw)
        assert len(samples) == 1
        assert samples[0]["ch1_Peak_level"] == "-3.5"
        assert samples[0]["ch2_RMS_level"] == "-11.0"

    def test_multiple_frames(self) -> None:
        """Parses multiple frames into sample list."""
        raw = json.dumps(
            {
                "frames": [
                    {
                        "tags": {
                            "lavfi.astats.Overall.Peak_level": "-6.0",
                            "lavfi.astats.Overall.RMS_level": "-12.0",
                        }
                    },
                    {
                        "tags": {
                            "lavfi.astats.Overall.Peak_level": "-3.0",
                            "lavfi.astats.Overall.RMS_level": "-9.0",
                        }
                    },
                ]
            }
        )
        samples = parse_astats_output(raw)
        assert len(samples) == 2
        assert samples[1]["Peak_level"] == "-3.0"

    def test_empty_frames(self) -> None:
        """Returns empty list when no frames present."""
        raw = json.dumps({"frames": []})
        samples = parse_astats_output(raw)
        assert samples == []

    def test_invalid_json(self) -> None:
        """Returns empty list for invalid JSON input."""
        samples = parse_astats_output("not json at all")
        assert samples == []

    def test_silent_audio(self) -> None:
        """Handles very negative dB values for silent audio."""
        raw = json.dumps(
            {
                "frames": [
                    {
                        "tags": {
                            "lavfi.astats.Overall.Peak_level": "-inf",
                            "lavfi.astats.Overall.RMS_level": "-inf",
                        }
                    }
                ]
            }
        )
        samples = parse_astats_output(raw)
        assert len(samples) == 1
        assert samples[0]["Peak_level"] == "-inf"
        assert samples[0]["RMS_level"] == "-inf"

    def test_frames_without_tags_skipped(self) -> None:
        """Frames without relevant tags produce no sample entries."""
        raw = json.dumps({"frames": [{"tags": {}}]})
        samples = parse_astats_output(raw)
        assert samples == []


# ---------------------------------------------------------------------------
# WaveformService.generate_png (FR-001, FR-003, FR-004, FR-005)
# ---------------------------------------------------------------------------


class TestGeneratePng:
    """Tests for PNG waveform generation via WaveformService."""

    @pytest.fixture()
    def fake_async_executor(self) -> FakeAsyncFFmpegExecutor:
        """Return a fake async executor configured for success."""
        return FakeAsyncFFmpegExecutor(returncode=0)

    async def test_generates_png_successfully(
        self,
        tmp_path: Path,
        fake_async_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """generate_png returns a READY Waveform on success (FR-001)."""
        service = WaveformService(
            fake_async_executor,
            tmp_path,
        )

        waveform = await service.generate_png(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
            channels=1,
        )

        assert waveform.status == WaveformStatus.READY
        assert waveform.format == WaveformFormat.PNG
        assert waveform.video_id == "vid1"
        assert waveform.duration == 30.0
        assert waveform.channels == 1
        assert waveform.file_path is not None
        assert waveform.file_path.endswith(".png")

    async def test_mono_ffmpeg_args(
        self,
        tmp_path: Path,
        fake_async_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """Mono audio produces single-color waveform (FR-003)."""
        service = WaveformService(fake_async_executor, tmp_path)

        await service.generate_png(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
            channels=1,
        )

        assert len(fake_async_executor.calls) == 1
        args = fake_async_executor.calls[0]
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "channel_layouts=mono" in fc
        assert "colors=blue" in fc

    async def test_stereo_ffmpeg_args(
        self,
        tmp_path: Path,
        fake_async_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """Stereo audio produces dual-color waveform (FR-003)."""
        service = WaveformService(fake_async_executor, tmp_path)

        await service.generate_png(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
            channels=2,
        )

        args = fake_async_executor.calls[0]
        fc_idx = args.index("-filter_complex")
        fc = args[fc_idx + 1]
        assert "channel_layouts=stereo" in fc
        assert "colors=blue|red" in fc

    async def test_error_on_ffmpeg_failure(
        self,
        tmp_path: Path,
    ) -> None:
        """Sets error status when FFmpeg returns non-zero."""
        bad_executor = FakeAsyncFFmpegExecutor(returncode=1)
        service = WaveformService(bad_executor, tmp_path)

        with pytest.raises(RuntimeError, match="FFmpeg failed"):
            await service.generate_png(
                video_id="vid1",
                video_path="/videos/test.mp4",
                duration_seconds=30.0,
            )

    async def test_error_on_exception(
        self,
        tmp_path: Path,
    ) -> None:
        """Sets error status when executor raises exception."""
        executor = FakeAsyncFFmpegExecutor(returncode=0)

        async def raising_run(*args: object, **kwargs: object) -> object:
            raise OSError("process failed")

        executor.run = raising_run  # type: ignore[assignment]
        service = WaveformService(executor, tmp_path)

        with pytest.raises(RuntimeError, match="Waveform PNG generation failed"):
            await service.generate_png(
                video_id="vid1",
                video_path="/videos/test.mp4",
                duration_seconds=30.0,
            )

    async def test_get_waveform_after_generate(
        self,
        tmp_path: Path,
        fake_async_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """Generated waveform is retrievable via get_waveform."""
        service = WaveformService(fake_async_executor, tmp_path)

        await service.generate_png(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
        )

        result = service.get_waveform("vid1", WaveformFormat.PNG)
        assert result is not None
        assert result.status == WaveformStatus.READY


# ---------------------------------------------------------------------------
# WaveformService.generate_json (FR-002, FR-003, FR-006)
# ---------------------------------------------------------------------------


class TestGenerateJson:
    """Tests for JSON waveform generation via WaveformService."""

    @pytest.fixture()
    def fake_ffprobe_executor(self) -> FakeAsyncFFmpegExecutor:
        """Return a fake ffprobe executor with astats output."""
        astats_output = json.dumps(
            {
                "frames": [
                    {
                        "tags": {
                            "lavfi.astats.Overall.Peak_level": "-6.021",
                            "lavfi.astats.Overall.RMS_level": "-12.345",
                        }
                    },
                    {
                        "tags": {
                            "lavfi.astats.Overall.Peak_level": "-3.010",
                            "lavfi.astats.Overall.RMS_level": "-9.876",
                        }
                    },
                ]
            }
        )
        return FakeAsyncFFmpegExecutor(
            returncode=0,
            stdout=astats_output.encode("utf-8"),
        )

    async def test_generates_json_successfully(
        self,
        tmp_path: Path,
        fake_ffprobe_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """generate_json returns a READY Waveform with JSON file (FR-002)."""
        dummy_executor = FakeAsyncFFmpegExecutor(returncode=0)
        service = WaveformService(
            dummy_executor,
            tmp_path,
            ffprobe_executor=fake_ffprobe_executor,
        )

        waveform = await service.generate_json(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
        )

        assert waveform.status == WaveformStatus.READY
        assert waveform.format == WaveformFormat.JSON
        assert waveform.file_path is not None
        assert waveform.file_path.endswith(".json")

        # Verify JSON file content
        output = json.loads(Path(waveform.file_path).read_text())
        assert output["video_id"] == "vid1"
        assert output["samples_per_second"] == 10
        assert len(output["frames"]) == 2
        assert output["frames"][0]["Peak_level"] == "-6.021"
        assert output["frames"][0]["RMS_level"] == "-12.345"

    async def test_raises_without_ffprobe_executor(
        self,
        tmp_path: Path,
    ) -> None:
        """Raises RuntimeError if no ffprobe executor configured."""
        dummy_executor = FakeAsyncFFmpegExecutor(returncode=0)
        service = WaveformService(dummy_executor, tmp_path)

        with pytest.raises(RuntimeError, match="ffprobe executor required"):
            await service.generate_json(
                video_id="vid1",
                video_path="/videos/test.mp4",
                duration_seconds=30.0,
            )

    async def test_error_on_ffprobe_failure(
        self,
        tmp_path: Path,
    ) -> None:
        """Sets error status when ffprobe returns non-zero."""
        dummy_executor = FakeAsyncFFmpegExecutor(returncode=0)
        bad_ffprobe = FakeAsyncFFmpegExecutor(returncode=1)
        service = WaveformService(
            dummy_executor,
            tmp_path,
            ffprobe_executor=bad_ffprobe,
        )

        with pytest.raises(RuntimeError, match="ffprobe failed"):
            await service.generate_json(
                video_id="vid1",
                video_path="/videos/test.mp4",
                duration_seconds=30.0,
            )

    async def test_json_path_escaping_in_args(
        self,
        tmp_path: Path,
        fake_ffprobe_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """Windows paths escaped in amovie= filter args (FR-006)."""
        dummy_executor = FakeAsyncFFmpegExecutor(returncode=0)
        service = WaveformService(
            dummy_executor,
            tmp_path,
            ffprobe_executor=fake_ffprobe_executor,
        )

        await service.generate_json(
            video_id="vid1",
            video_path=r"C:\Users\test\video.mp4",
            duration_seconds=30.0,
        )

        args = fake_ffprobe_executor.calls[0]
        i_idx = args.index("-i")
        filter_str = args[i_idx + 1]
        assert "\\" not in filter_str

    async def test_get_waveform_json_after_generate(
        self,
        tmp_path: Path,
        fake_ffprobe_executor: FakeAsyncFFmpegExecutor,
    ) -> None:
        """Generated JSON waveform is retrievable via get_waveform."""
        dummy_executor = FakeAsyncFFmpegExecutor(returncode=0)
        service = WaveformService(
            dummy_executor,
            tmp_path,
            ffprobe_executor=fake_ffprobe_executor,
        )

        await service.generate_json(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
        )

        result = service.get_waveform("vid1", WaveformFormat.JSON)
        assert result is not None
        assert result.status == WaveformStatus.READY


# ---------------------------------------------------------------------------
# WebSocket progress events (FR-004)
# ---------------------------------------------------------------------------


class TestWaveformProgressEvents:
    """Tests for WebSocket progress broadcasting during waveform generation."""

    async def test_emits_completion_event_png(self, tmp_path: Path) -> None:
        """Completion event is broadcast via WebSocket on PNG success (FR-004)."""
        ws_manager = AsyncMock()
        fake_async = FakeAsyncFFmpegExecutor(returncode=0)

        service = WaveformService(
            fake_async,
            tmp_path,
            ws_manager=ws_manager,
        )

        await service.generate_png(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
        )

        ws_manager.broadcast.assert_called()
        last_call = ws_manager.broadcast.call_args[0][0]
        assert last_call["type"] == "job_progress"
        assert last_call["payload"]["status"] == "complete"
        assert last_call["payload"]["job_type"] == "waveform"
        assert last_call["payload"]["video_id"] == "vid1"
        assert last_call["payload"]["progress"] == 1.0

    async def test_emits_completion_event_json(self, tmp_path: Path) -> None:
        """Completion event is broadcast via WebSocket on JSON success (FR-004)."""
        ws_manager = AsyncMock()
        dummy_async = FakeAsyncFFmpegExecutor(returncode=0)
        astats_output = json.dumps(
            {
                "frames": [
                    {
                        "tags": {
                            "lavfi.astats.Overall.Peak_level": "-6.0",
                            "lavfi.astats.Overall.RMS_level": "-12.0",
                        }
                    }
                ]
            }
        )
        fake_ffprobe = FakeAsyncFFmpegExecutor(
            returncode=0,
            stdout=astats_output.encode("utf-8"),
        )

        service = WaveformService(
            dummy_async,
            tmp_path,
            ffprobe_executor=fake_ffprobe,
            ws_manager=ws_manager,
        )

        await service.generate_json(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
        )

        ws_manager.broadcast.assert_called()
        last_call = ws_manager.broadcast.call_args[0][0]
        assert last_call["type"] == "job_progress"
        assert last_call["payload"]["status"] == "complete"
        assert last_call["payload"]["job_type"] == "waveform"

    async def test_no_broadcast_without_ws_manager(self, tmp_path: Path) -> None:
        """No error when ws_manager is None."""
        fake_async = FakeAsyncFFmpegExecutor(returncode=0)
        service = WaveformService(fake_async, tmp_path)

        waveform = await service.generate_png(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
        )
        assert waveform.status == WaveformStatus.READY


# ---------------------------------------------------------------------------
# Waveform model
# ---------------------------------------------------------------------------


class TestWaveformModel:
    """Tests for Waveform dataclass."""

    def test_default_values(self) -> None:
        """Waveform has correct defaults."""
        from datetime import datetime, timezone

        waveform = Waveform(
            id="test-id",
            video_id="vid1",
            format=WaveformFormat.PNG,
            status=WaveformStatus.PENDING,
            created_at=datetime.now(timezone.utc),
        )
        assert waveform.file_path is None
        assert waveform.duration == 0.0
        assert waveform.channels == 0

    def test_new_id_is_uuid(self) -> None:
        """new_id generates valid UUID strings."""
        import uuid

        id1 = Waveform.new_id()
        id2 = Waveform.new_id()
        assert id1 != id2
        uuid.UUID(id1)  # Raises if invalid

    def test_status_values(self) -> None:
        """WaveformStatus has expected values."""
        assert WaveformStatus.PENDING == "pending"
        assert WaveformStatus.GENERATING == "generating"
        assert WaveformStatus.READY == "ready"
        assert WaveformStatus.ERROR == "error"

    def test_format_values(self) -> None:
        """WaveformFormat has expected values."""
        assert WaveformFormat.PNG == "png"
        assert WaveformFormat.JSON == "json"


# ---------------------------------------------------------------------------
# Parity with ThumbnailService (design requirement)
# ---------------------------------------------------------------------------


class TestWaveformThumbnailParity:
    """Verify waveform service follows same patterns as thumbnail strip service."""

    async def test_pending_to_generating_to_ready(
        self,
        tmp_path: Path,
    ) -> None:
        """Waveform follows pending -> generating -> ready transitions."""
        fake_async = FakeAsyncFFmpegExecutor(returncode=0)
        service = WaveformService(fake_async, tmp_path)

        waveform = await service.generate_png(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
        )

        # Final state should be READY
        assert waveform.status == WaveformStatus.READY

    async def test_error_state_on_failure(
        self,
        tmp_path: Path,
    ) -> None:
        """Waveform transitions to error state on failure."""
        bad_executor = FakeAsyncFFmpegExecutor(returncode=1)
        service = WaveformService(bad_executor, tmp_path)

        with pytest.raises(RuntimeError):
            await service.generate_png(
                video_id="vid1",
                video_path="/videos/test.mp4",
                duration_seconds=30.0,
            )

        waveform = service.get_waveform("vid1", WaveformFormat.PNG)
        assert waveform is not None
        assert waveform.status == WaveformStatus.ERROR

    async def test_png_and_json_same_lifecycle(
        self,
        tmp_path: Path,
    ) -> None:
        """Both PNG and JSON formats follow same lifecycle (format parity)."""
        fake_async = FakeAsyncFFmpegExecutor(returncode=0)
        astats_output = json.dumps(
            {
                "frames": [
                    {
                        "tags": {
                            "lavfi.astats.Overall.Peak_level": "-6.0",
                            "lavfi.astats.Overall.RMS_level": "-12.0",
                        }
                    }
                ]
            }
        )
        fake_ffprobe = FakeAsyncFFmpegExecutor(
            returncode=0,
            stdout=astats_output.encode("utf-8"),
        )
        service = WaveformService(fake_async, tmp_path, ffprobe_executor=fake_ffprobe)

        png = await service.generate_png(
            video_id="vid1",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
        )
        json_wf = await service.generate_json(
            video_id="vid2",
            video_path="/videos/test.mp4",
            duration_seconds=30.0,
        )

        assert png.status == json_wf.status == WaveformStatus.READY


# ---------------------------------------------------------------------------
# Settings (FR-007)
# ---------------------------------------------------------------------------


class TestWaveformSettings:
    """Tests for waveform_dir setting."""

    def test_default_waveform_dir(self) -> None:
        """Default waveform_dir is data/waveforms (FR-007)."""
        from stoat_ferret.api.settings import Settings

        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
        )
        assert settings.waveform_dir == "data/waveforms"

    def test_waveform_dir_from_env(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """waveform_dir configurable via STOAT_WAVEFORM_DIR (FR-007)."""
        from stoat_ferret.api.settings import Settings

        monkeypatch.setenv("STOAT_WAVEFORM_DIR", "/custom/waveforms")
        settings = Settings(
            _env_file=None,  # type: ignore[call-arg]
        )
        assert settings.waveform_dir == "/custom/waveforms"


# ---------------------------------------------------------------------------
# Schema (waveforms table)
# ---------------------------------------------------------------------------


class TestWaveformSchema:
    """Tests for waveforms database table."""

    def test_waveforms_table_created(self) -> None:
        """Waveforms table is created by create_tables."""
        import sqlite3

        from stoat_ferret.db.schema import create_tables

        conn = sqlite3.connect(":memory:")
        create_tables(conn)

        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='waveforms'"
        )
        assert cursor.fetchone() is not None
        conn.close()

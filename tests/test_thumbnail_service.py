"""Unit tests for ThumbnailService."""

from __future__ import annotations

from pathlib import Path

from stoat_ferret.api.services.thumbnail import ThumbnailService
from stoat_ferret.ffmpeg.executor import ExecutionResult, FakeFFmpegExecutor


def _make_success_recording(args: list[str] | None = None) -> list[dict[str, object]]:
    """Create a fake recording for a successful thumbnail generation."""
    return [
        {
            "args": args or [],
            "stdin": None,
            "result": {
                "returncode": 0,
                "stdout": "",
                "stderr": "",
                "duration_seconds": 0.5,
            },
        }
    ]


def _make_failure_recording() -> list[dict[str, object]]:
    """Create a fake recording for a failed thumbnail generation."""
    return [
        {
            "args": [],
            "stdin": None,
            "result": {
                "returncode": 1,
                "stdout": "",
                "stderr": "4e6f20737563682066696c65",  # "No such file" in hex
                "duration_seconds": 0.1,
            },
        }
    ]


class TestThumbnailServiceGenerate:
    """Tests for ThumbnailService.generate()."""

    def test_generates_correct_ffmpeg_args(self, tmp_path: Path) -> None:
        """ThumbnailService builds expected FFmpeg args for thumbnail extraction."""
        video_path = "/videos/test.mp4"
        video_id = "abc123"

        expected_args = [
            "-ss",
            "5",
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-vf",
            "scale=320:-1",
            "-q:v",
            "5",
            "-y",
            str(tmp_path / f"{video_id}.jpg"),
        ]

        fake = FakeFFmpegExecutor(_make_success_recording(expected_args), strict=True)
        service = ThumbnailService(fake, tmp_path)

        # Create a dummy output to simulate FFmpeg creating the file
        result = service.generate(video_path, video_id)

        assert result == str(tmp_path / f"{video_id}.jpg")
        fake.assert_all_consumed()

    def test_stores_to_configured_directory(self, tmp_path: Path) -> None:
        """Thumbnails are saved to the configured thumbnail directory."""
        thumb_dir = tmp_path / "thumbnails"
        fake = FakeFFmpegExecutor(_make_success_recording())
        service = ThumbnailService(fake, thumb_dir)

        result = service.generate("/videos/test.mp4", "vid1")

        assert result is not None
        assert result.startswith(str(thumb_dir))
        assert result.endswith("vid1.jpg")

    def test_creates_thumbnail_directory(self, tmp_path: Path) -> None:
        """Thumbnail directory is created if it doesn't exist."""
        thumb_dir = tmp_path / "deep" / "nested" / "dir"
        fake = FakeFFmpegExecutor(_make_success_recording())
        service = ThumbnailService(fake, thumb_dir)

        service.generate("/videos/test.mp4", "vid1")

        assert thumb_dir.is_dir()

    def test_returns_none_on_ffmpeg_failure(self, tmp_path: Path) -> None:
        """Returns None when FFmpeg exits with non-zero code."""
        fake = FakeFFmpegExecutor(_make_failure_recording())
        service = ThumbnailService(fake, tmp_path)

        result = service.generate("/videos/test.mp4", "vid1")

        assert result is None

    def test_returns_none_on_exception(self, tmp_path: Path) -> None:
        """Returns None when FFmpeg executor raises an exception."""

        class RaisingExecutor:
            """Executor that always raises."""

            def run(
                self,
                args: list[str],
                *,
                stdin: bytes | None = None,
                timeout: float | None = None,
            ) -> ExecutionResult:
                raise RuntimeError("FFmpeg not found")

        service = ThumbnailService(RaisingExecutor(), tmp_path)

        result = service.generate("/videos/test.mp4", "vid1")

        assert result is None

    def test_configurable_width(self, tmp_path: Path) -> None:
        """Thumbnail width is configurable via constructor."""
        video_path = "/videos/test.mp4"
        video_id = "abc123"
        custom_width = 640

        expected_args = [
            "-ss",
            "5",
            "-i",
            video_path,
            "-frames:v",
            "1",
            "-vf",
            f"scale={custom_width}:-1",
            "-q:v",
            "5",
            "-y",
            str(tmp_path / f"{video_id}.jpg"),
        ]

        fake = FakeFFmpegExecutor(_make_success_recording(expected_args), strict=True)
        service = ThumbnailService(fake, tmp_path, width=custom_width)

        result = service.generate(video_path, video_id)

        assert result is not None
        fake.assert_all_consumed()

    def test_default_width_is_320(self, tmp_path: Path) -> None:
        """Default thumbnail width is 320 pixels."""
        service = ThumbnailService(FakeFFmpegExecutor(_make_success_recording()), tmp_path)
        assert service._width == 320


class TestThumbnailServiceGetPath:
    """Tests for ThumbnailService.get_thumbnail_path()."""

    def test_returns_path_when_file_exists(self, tmp_path: Path) -> None:
        """Returns thumbnail path when file exists on disk."""
        fake = FakeFFmpegExecutor([])
        service = ThumbnailService(fake, tmp_path)

        # Create a fake thumbnail file
        thumb_file = tmp_path / "vid1.jpg"
        thumb_file.write_bytes(b"\xff\xd8")

        result = service.get_thumbnail_path("vid1")

        assert result == str(thumb_file)

    def test_returns_none_when_file_missing(self, tmp_path: Path) -> None:
        """Returns None when thumbnail file doesn't exist."""
        fake = FakeFFmpegExecutor([])
        service = ThumbnailService(fake, tmp_path)

        result = service.get_thumbnail_path("nonexistent")

        assert result is None


class TestRecordingExecutorCapture:
    """Tests for recording executor capturing thumbnail commands."""

    def test_recording_captures_thumbnail_command(self, tmp_path: Path) -> None:
        """RecordingFFmpegExecutor captures thumbnail generation commands."""
        from stoat_ferret.ffmpeg.executor import RecordingFFmpegExecutor

        recording_path = tmp_path / "recording.json"

        class MockExecutor:
            """Minimal executor that returns success."""

            def run(
                self,
                args: list[str],
                *,
                stdin: bytes | None = None,
                timeout: float | None = None,
            ) -> ExecutionResult:
                return ExecutionResult(
                    returncode=0,
                    stdout=b"",
                    stderr=b"",
                    command=["ffmpeg", *args],
                    duration_seconds=0.1,
                )

        mock = MockExecutor()
        recorder = RecordingFFmpegExecutor(mock, recording_path)
        service = ThumbnailService(recorder, tmp_path)

        service.generate("/videos/test.mp4", "vid1")
        recorder.save()

        # Verify recording was captured
        import json

        recordings = json.loads(recording_path.read_text())
        assert len(recordings) == 1
        assert "-frames:v" in recordings[0]["args"]
        assert "scale=320:-1" in recordings[0]["args"]

    def test_fake_replays_thumbnail_recording(self, tmp_path: Path) -> None:
        """FakeFFmpegExecutor replays captured thumbnail recordings."""
        recordings = [
            {
                "args": [
                    "-ss",
                    "5",
                    "-i",
                    "/videos/test.mp4",
                    "-frames:v",
                    "1",
                    "-vf",
                    "scale=320:-1",
                    "-q:v",
                    "5",
                    "-y",
                    str(tmp_path / "vid1.jpg"),
                ],
                "stdin": None,
                "result": {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": "",
                    "duration_seconds": 0.5,
                },
            }
        ]

        fake = FakeFFmpegExecutor(recordings, strict=True)
        service = ThumbnailService(fake, tmp_path)

        result = service.generate("/videos/test.mp4", "vid1")

        assert result is not None
        fake.assert_all_consumed()

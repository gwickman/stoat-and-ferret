"""Contract tests verifying Real, Recording, and Fake FFmpeg executors behave identically.

Parametrized tests run the same commands against all three executor implementations.
Real executor tests require FFmpeg installed and are marked with @pytest.mark.requires_ffmpeg.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stoat_ferret.ffmpeg.executor import (
    ExecutionResult,
    FakeFFmpegExecutor,
    RealFFmpegExecutor,
    RecordingFFmpegExecutor,
)
from tests.conftest import requires_ffmpeg

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_recording(
    args: list[str],
    *,
    returncode: int = 0,
    stdout: bytes = b"",
    stderr: bytes = b"",
    duration: float = 0.01,
) -> dict[str, object]:
    """Build a single recording dict matching RecordingFFmpegExecutor's format."""
    return {
        "args": args,
        "stdin": None,
        "result": {
            "returncode": returncode,
            "stdout": stdout.hex(),
            "stderr": stderr.hex(),
            "duration_seconds": duration,
        },
    }


def _save_recordings(path: Path, recordings: list[dict[str, object]]) -> None:
    """Persist recordings to JSON file."""
    path.write_text(json.dumps(recordings, indent=2))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def recording_path(tmp_path: Path) -> Path:
    """Provide a temporary path for recording files."""
    return tmp_path / "contract_recording.json"


# ---------------------------------------------------------------------------
# Stage 2: Record-and-replay contract tests
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestRecordReplayContract:
    """Recording executor output replays identically through Fake executor."""

    COMMANDS: list[list[str]] = [
        ["-version"],
        ["-hide_banner", "-version"],
        ["-i", "nonexistent.mp4"],
        ["-filters"],
        ["-codecs"],
    ]

    @pytest.mark.parametrize(
        "args",
        COMMANDS,
        ids=[
            "version",
            "hide-banner-version",
            "missing-input",
            "filters",
            "codecs",
        ],
    )
    def test_recording_replays_identically(self, args: list[str], recording_path: Path) -> None:
        """A recorded interaction replays with identical returncode, stdout, stderr."""
        # Use a deterministic mock so the test never needs real FFmpeg.
        from tests.test_executor import MockExecutor

        mock = MockExecutor(returncode=0, stdout=b"mock-out", stderr=b"mock-err")

        # Record
        recorder = RecordingFFmpegExecutor(mock, recording_path)
        original = recorder.run(args)
        recorder.save()

        # Replay
        fake = FakeFFmpegExecutor.from_file(recording_path)
        replayed = fake.run(args)

        assert original.returncode == replayed.returncode
        assert original.stdout == replayed.stdout
        assert original.stderr == replayed.stderr
        fake.assert_all_consumed()


# ---------------------------------------------------------------------------
# Stage 3: Real-executor contract tests (requires FFmpeg)
# ---------------------------------------------------------------------------


@requires_ffmpeg
@pytest.mark.contract
class TestRealExecutorContract:
    """Real FFmpeg executor produces results that can be recorded and replayed."""

    def test_version_check(self, recording_path: Path) -> None:
        """ffmpeg -version: record real output and replay identically."""
        real = RealFFmpegExecutor()
        recorder = RecordingFFmpegExecutor(real, recording_path)

        original = recorder.run(["-version"])
        recorder.save()

        fake = FakeFFmpegExecutor.from_file(recording_path)
        replayed = fake.run(["-version"])

        assert original.returncode == replayed.returncode
        assert original.stdout == replayed.stdout
        assert original.stderr == replayed.stderr
        fake.assert_all_consumed()

    def test_filters_list(self, recording_path: Path) -> None:
        """ffmpeg -filters: record and replay."""
        real = RealFFmpegExecutor()
        recorder = RecordingFFmpegExecutor(real, recording_path)

        original = recorder.run(["-filters"])
        recorder.save()

        fake = FakeFFmpegExecutor.from_file(recording_path)
        replayed = fake.run(["-filters"])

        assert original.returncode == replayed.returncode
        assert original.stdout == replayed.stdout
        assert original.stderr == replayed.stderr
        fake.assert_all_consumed()

    def test_codecs_list(self, recording_path: Path) -> None:
        """ffmpeg -codecs: record and replay."""
        real = RealFFmpegExecutor()
        recorder = RecordingFFmpegExecutor(real, recording_path)

        original = recorder.run(["-codecs"])
        recorder.save()

        fake = FakeFFmpegExecutor.from_file(recording_path)
        replayed = fake.run(["-codecs"])

        assert original.returncode == replayed.returncode
        assert original.stdout == replayed.stdout
        assert original.stderr == replayed.stderr
        fake.assert_all_consumed()

    def test_invalid_input_returns_nonzero(self, recording_path: Path) -> None:
        """ffmpeg -i nonexistent.mp4: record error and replay."""
        real = RealFFmpegExecutor()
        recorder = RecordingFFmpegExecutor(real, recording_path)

        original = recorder.run(["-i", "nonexistent_file_12345.mp4"])
        recorder.save()

        fake = FakeFFmpegExecutor.from_file(recording_path)
        replayed = fake.run(["-i", "nonexistent_file_12345.mp4"])

        assert original.returncode != 0
        assert original.returncode == replayed.returncode
        assert original.stdout == replayed.stdout
        assert original.stderr == replayed.stderr
        fake.assert_all_consumed()

    def test_hide_banner_version(self, recording_path: Path) -> None:
        """ffmpeg -hide_banner -version: record and replay."""
        real = RealFFmpegExecutor()
        recorder = RecordingFFmpegExecutor(real, recording_path)

        original = recorder.run(["-hide_banner", "-version"])
        recorder.save()

        fake = FakeFFmpegExecutor.from_file(recording_path)
        replayed = fake.run(["-hide_banner", "-version"])

        assert original.returncode == replayed.returncode
        assert original.stdout == replayed.stdout
        assert original.stderr == replayed.stderr
        fake.assert_all_consumed()

    def test_multiple_commands_sequential(self, recording_path: Path) -> None:
        """Multiple commands recorded and replayed in sequence."""
        real = RealFFmpegExecutor()
        recorder = RecordingFFmpegExecutor(real, recording_path)

        originals: list[ExecutionResult] = []
        commands = [["-version"], ["-filters"], ["-codecs"]]
        for cmd in commands:
            originals.append(recorder.run(cmd))
        recorder.save()

        fake = FakeFFmpegExecutor.from_file(recording_path)
        for i, cmd in enumerate(commands):
            replayed = fake.run(cmd)
            assert originals[i].returncode == replayed.returncode
            assert originals[i].stdout == replayed.stdout
            assert originals[i].stderr == replayed.stderr
        fake.assert_all_consumed()


# ---------------------------------------------------------------------------
# Stage 4: Strict mode arg verification tests
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestStrictModeContract:
    """FakeFFmpegExecutor strict mode verifies args before replaying."""

    def test_strict_mode_passes_on_matching_args(self) -> None:
        """Strict mode replays normally when args match."""
        recordings = [_make_recording(["-version"], stdout=b"ffmpeg v1")]
        fake = FakeFFmpegExecutor(recordings, strict=True)

        result = fake.run(["-version"])

        assert result.returncode == 0
        assert result.stdout == b"ffmpeg v1"

    def test_strict_mode_raises_on_mismatched_args(self) -> None:
        """Strict mode raises RuntimeError when args differ."""
        recordings = [_make_recording(["-version"])]
        fake = FakeFFmpegExecutor(recordings, strict=True)

        with pytest.raises(RuntimeError, match="Strict mode: args mismatch"):
            fake.run(["-filters"])

    def test_strict_mode_error_shows_expected_and_actual(self) -> None:
        """Error message includes both expected and actual args."""
        recordings = [_make_recording(["-version"])]
        fake = FakeFFmpegExecutor(recordings, strict=True)

        with pytest.raises(RuntimeError, match=r"\['-version'\].*\['-codecs'\]"):
            fake.run(["-codecs"])

    def test_strict_mode_from_file(self, tmp_path: Path) -> None:
        """Strict mode works with from_file class method."""
        recordings = [_make_recording(["-version"], stdout=b"v1")]
        _save_recordings(tmp_path / "strict.json", recordings)

        fake = FakeFFmpegExecutor.from_file(tmp_path / "strict.json", strict=True)
        result = fake.run(["-version"])
        assert result.stdout == b"v1"

    def test_strict_mode_mismatch_from_file(self, tmp_path: Path) -> None:
        """Strict mode from_file raises on mismatch."""
        recordings = [_make_recording(["-version"])]
        _save_recordings(tmp_path / "strict.json", recordings)

        fake = FakeFFmpegExecutor.from_file(tmp_path / "strict.json", strict=True)
        with pytest.raises(RuntimeError, match="Strict mode"):
            fake.run(["-wrong"])

    def test_non_strict_mode_ignores_arg_mismatch(self) -> None:
        """Default non-strict mode replays regardless of args."""
        recordings = [_make_recording(["-version"], stdout=b"output")]
        fake = FakeFFmpegExecutor(recordings, strict=False)

        result = fake.run(["-totally-different-args"])

        assert result.stdout == b"output"

    def test_strict_mode_recording_replay_cycle(self, tmp_path: Path) -> None:
        """Full record-replay cycle works with strict mode."""
        from tests.test_executor import MockExecutor

        mock = MockExecutor(returncode=0, stdout=b"strict-output", stderr=b"")
        recording_path = tmp_path / "cycle.json"

        # Record
        recorder = RecordingFFmpegExecutor(mock, recording_path)
        recorder.run(["-i", "input.mp4", "-vf", "scale=640:480", "output.mp4"])
        recorder.save()

        # Replay with strict mode — matching args should succeed
        fake = FakeFFmpegExecutor.from_file(recording_path, strict=True)
        result = fake.run(["-i", "input.mp4", "-vf", "scale=640:480", "output.mp4"])
        assert result.stdout == b"strict-output"
        fake.assert_all_consumed()


# ---------------------------------------------------------------------------
# Error consistency tests
# ---------------------------------------------------------------------------


@pytest.mark.contract
class TestErrorConsistency:
    """All executor types handle edge cases consistently."""

    def test_fake_exhaustion_raises_runtime_error(self) -> None:
        """FakeFFmpegExecutor raises RuntimeError when recordings exhausted."""
        fake = FakeFFmpegExecutor([])
        with pytest.raises(RuntimeError, match="No more recordings"):
            fake.run(["-version"])

    def test_fake_strict_exhaustion_raises_runtime_error(self) -> None:
        """Strict-mode FakeFFmpegExecutor also raises when exhausted."""
        fake = FakeFFmpegExecutor([], strict=True)
        with pytest.raises(RuntimeError, match="No more recordings"):
            fake.run(["-version"])

    def test_recording_delegates_error_from_wrapped(self, tmp_path: Path) -> None:
        """RecordingFFmpegExecutor delegates errors from the wrapped executor."""
        from tests.test_executor import MockExecutor

        mock = MockExecutor(returncode=1, stdout=b"", stderr=b"error output")
        recording_path = tmp_path / "errors.json"
        recorder = RecordingFFmpegExecutor(mock, recording_path)

        result = recorder.run(["-invalid"])

        assert result.returncode == 1
        assert result.stderr == b"error output"

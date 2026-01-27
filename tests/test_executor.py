"""Tests for FFmpeg executor implementations."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from stoat_ferret.ffmpeg.executor import (
    ExecutionResult,
    FakeFFmpegExecutor,
    FFmpegExecutor,
    RealFFmpegExecutor,
    RecordingFFmpegExecutor,
)
from tests.conftest import requires_ffmpeg


class TestExecutionResult:
    """Tests for ExecutionResult dataclass."""

    def test_creation(self) -> None:
        """Test ExecutionResult can be created with all fields."""
        result = ExecutionResult(
            returncode=0,
            stdout=b"output",
            stderr=b"error",
            command=["ffmpeg", "-version"],
            duration_seconds=0.5,
        )
        assert result.returncode == 0
        assert result.stdout == b"output"
        assert result.stderr == b"error"
        assert result.command == ["ffmpeg", "-version"]
        assert result.duration_seconds == 0.5

    def test_fields_are_accessible(self) -> None:
        """Test all fields are properly accessible."""
        result = ExecutionResult(
            returncode=1,
            stdout=b"",
            stderr=b"error message",
            command=["ffmpeg", "-i", "input.mp4", "output.mp4"],
            duration_seconds=1.23,
        )
        assert result.returncode == 1
        assert result.stdout == b""
        assert result.stderr == b"error message"
        assert len(result.command) == 4
        assert result.duration_seconds == 1.23


class MockExecutor:
    """Mock executor for testing RecordingFFmpegExecutor."""

    def __init__(
        self,
        returncode: int = 0,
        stdout: bytes = b"mock output",
        stderr: bytes = b"",
    ) -> None:
        """Initialize with configurable return values."""
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        self.calls: list[tuple[list[str], bytes | None, float | None]] = []

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Return mock result and record the call."""
        self.calls.append((args, stdin, timeout))
        return ExecutionResult(
            returncode=self.returncode,
            stdout=self.stdout,
            stderr=self.stderr,
            command=["ffmpeg", *args],
            duration_seconds=0.1,
        )


class TestRecordingFFmpegExecutor:
    """Tests for RecordingFFmpegExecutor."""

    def test_delegates_to_wrapped_executor(self, tmp_path: Path) -> None:
        """Test that calls are delegated to wrapped executor."""
        mock = MockExecutor(stdout=b"delegated output")
        recording_path = tmp_path / "recording.json"
        recorder = RecordingFFmpegExecutor(mock, recording_path)

        result = recorder.run(["-i", "input.mp4", "output.mp4"])

        assert result.stdout == b"delegated output"
        assert len(mock.calls) == 1
        assert mock.calls[0][0] == ["-i", "input.mp4", "output.mp4"]

    def test_records_interactions(self, tmp_path: Path) -> None:
        """Test that interactions are recorded."""
        mock = MockExecutor(returncode=0, stdout=b"output", stderr=b"")
        recording_path = tmp_path / "recording.json"
        recorder = RecordingFFmpegExecutor(mock, recording_path)

        recorder.run(["-version"])
        recorder.save()

        recordings = json.loads(recording_path.read_text())
        assert len(recordings) == 1
        assert recordings[0]["args"] == ["-version"]
        assert recordings[0]["result"]["returncode"] == 0

    def test_records_multiple_interactions(self, tmp_path: Path) -> None:
        """Test that multiple interactions are recorded."""
        mock = MockExecutor()
        recording_path = tmp_path / "recording.json"
        recorder = RecordingFFmpegExecutor(mock, recording_path)

        recorder.run(["-version"])
        recorder.run(["-i", "input.mp4", "output.mp4"])
        recorder.run(["-filters"])
        recorder.save()

        recordings = json.loads(recording_path.read_text())
        assert len(recordings) == 3
        assert recordings[0]["args"] == ["-version"]
        assert recordings[1]["args"] == ["-i", "input.mp4", "output.mp4"]
        assert recordings[2]["args"] == ["-filters"]

    def test_records_stdin_as_hex(self, tmp_path: Path) -> None:
        """Test that stdin is recorded as hex."""
        mock = MockExecutor()
        recording_path = tmp_path / "recording.json"
        recorder = RecordingFFmpegExecutor(mock, recording_path)

        recorder.run(["-i", "pipe:"], stdin=b"\x00\x01\x02\x03")
        recorder.save()

        recordings = json.loads(recording_path.read_text())
        assert recordings[0]["stdin"] == "00010203"

    def test_records_stdout_stderr_as_hex(self, tmp_path: Path) -> None:
        """Test that stdout/stderr are recorded as hex."""
        mock = MockExecutor(stdout=b"\xff\xfe", stderr=b"\x01\x02")
        recording_path = tmp_path / "recording.json"
        recorder = RecordingFFmpegExecutor(mock, recording_path)

        recorder.run(["-version"])
        recorder.save()

        recordings = json.loads(recording_path.read_text())
        assert recordings[0]["result"]["stdout"] == "fffe"
        assert recordings[0]["result"]["stderr"] == "0102"

    def test_records_none_stdin(self, tmp_path: Path) -> None:
        """Test that None stdin is recorded as null."""
        mock = MockExecutor()
        recording_path = tmp_path / "recording.json"
        recorder = RecordingFFmpegExecutor(mock, recording_path)

        recorder.run(["-version"])
        recorder.save()

        recordings = json.loads(recording_path.read_text())
        assert recordings[0]["stdin"] is None

    def test_save_creates_valid_json(self, tmp_path: Path) -> None:
        """Test that saved recordings are valid JSON."""
        mock = MockExecutor()
        recording_path = tmp_path / "recording.json"
        recorder = RecordingFFmpegExecutor(mock, recording_path)

        recorder.run(["-version"])
        recorder.save()

        # Should not raise
        json.loads(recording_path.read_text())


class TestFakeFFmpegExecutor:
    """Tests for FakeFFmpegExecutor."""

    def test_replays_recorded_result(self) -> None:
        """Test that FakeFFmpegExecutor replays recorded results."""
        recordings = [
            {
                "args": ["-version"],
                "stdin": None,
                "result": {
                    "returncode": 0,
                    "stdout": "6f7574707574",  # "output" in hex
                    "stderr": "",
                    "duration_seconds": 0.1,
                },
            }
        ]
        fake = FakeFFmpegExecutor(recordings)

        result = fake.run(["-version"])

        assert result.returncode == 0
        assert result.stdout == b"output"
        assert result.duration_seconds == 0.1

    def test_replays_multiple_recordings_in_order(self) -> None:
        """Test that recordings are replayed in order."""
        recordings = [
            {
                "args": ["-version"],
                "stdin": None,
                "result": {
                    "returncode": 0,
                    "stdout": "6669727374",  # "first" in hex
                    "stderr": "",
                    "duration_seconds": 0.1,
                },
            },
            {
                "args": ["-filters"],
                "stdin": None,
                "result": {
                    "returncode": 0,
                    "stdout": "7365636f6e64",  # "second" in hex
                    "stderr": "",
                    "duration_seconds": 0.2,
                },
            },
        ]
        fake = FakeFFmpegExecutor(recordings)

        result1 = fake.run(["-version"])
        result2 = fake.run(["-filters"])

        assert result1.stdout == b"first"
        assert result2.stdout == b"second"

    def test_raises_when_exhausted(self) -> None:
        """Test that FakeFFmpegExecutor raises when no more recordings."""
        fake = FakeFFmpegExecutor([])

        with pytest.raises(RuntimeError, match="No more recordings"):
            fake.run(["-version"])

    def test_raises_with_correct_count(self) -> None:
        """Test error message includes correct call count."""
        recordings = [
            {
                "args": ["-version"],
                "stdin": None,
                "result": {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": "",
                    "duration_seconds": 0.1,
                },
            }
        ]
        fake = FakeFFmpegExecutor(recordings)

        fake.run(["-version"])
        with pytest.raises(RuntimeError, match="called 2 times.*1 recorded"):
            fake.run(["-version"])

    def test_from_file(self, tmp_path: Path) -> None:
        """Test loading recordings from file."""
        recordings = [
            {
                "args": ["-version"],
                "stdin": None,
                "result": {
                    "returncode": 0,
                    "stdout": "6c6f6164656420737464",  # "loaded std" in hex
                    "stderr": "",
                    "duration_seconds": 0.1,
                },
            }
        ]
        recording_path = tmp_path / "recording.json"
        recording_path.write_text(json.dumps(recordings))

        fake = FakeFFmpegExecutor.from_file(recording_path)
        result = fake.run(["-version"])

        assert result.stdout == b"loaded std"

    def test_assert_all_consumed_passes(self) -> None:
        """Test assert_all_consumed passes when all recordings used."""
        recordings = [
            {
                "args": ["-version"],
                "stdin": None,
                "result": {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": "",
                    "duration_seconds": 0.1,
                },
            }
        ]
        fake = FakeFFmpegExecutor(recordings)
        fake.run(["-version"])

        fake.assert_all_consumed()  # Should not raise

    def test_assert_all_consumed_fails(self) -> None:
        """Test assert_all_consumed fails when recordings remain."""
        recordings = [
            {
                "args": ["-version"],
                "stdin": None,
                "result": {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": "",
                    "duration_seconds": 0.1,
                },
            },
            {
                "args": ["-filters"],
                "stdin": None,
                "result": {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": "",
                    "duration_seconds": 0.1,
                },
            },
        ]
        fake = FakeFFmpegExecutor(recordings)
        fake.run(["-version"])

        with pytest.raises(AssertionError, match="1 of 2 recordings consumed"):
            fake.assert_all_consumed()

    def test_command_includes_ffmpeg_prefix(self) -> None:
        """Test that result command includes ffmpeg prefix."""
        recordings = [
            {
                "args": ["-version"],
                "stdin": None,
                "result": {
                    "returncode": 0,
                    "stdout": "",
                    "stderr": "",
                    "duration_seconds": 0.1,
                },
            }
        ]
        fake = FakeFFmpegExecutor(recordings)

        result = fake.run(["-version"])

        assert result.command == ["ffmpeg", "-version"]

    def test_decodes_hex_stderr(self) -> None:
        """Test that stderr is decoded from hex."""
        recordings = [
            {
                "args": ["-version"],
                "stdin": None,
                "result": {
                    "returncode": 1,
                    "stdout": "",
                    "stderr": "6572726f72",  # "error" in hex
                    "duration_seconds": 0.1,
                },
            }
        ]
        fake = FakeFFmpegExecutor(recordings)

        result = fake.run(["-version"])

        assert result.stderr == b"error"


class TestRecordingAndReplayCycle:
    """Tests for the complete recording and replay cycle."""

    def test_record_and_replay_produces_same_result(self, tmp_path: Path) -> None:
        """Test that recording and replaying produces identical results."""
        mock = MockExecutor(returncode=0, stdout=b"output data", stderr=b"")
        recording_path = tmp_path / "recording.json"

        # Record
        recorder = RecordingFFmpegExecutor(mock, recording_path)
        result1 = recorder.run(["-i", "input.mp4", "output.mp4"])
        recorder.save()

        # Replay
        fake = FakeFFmpegExecutor.from_file(recording_path)
        result2 = fake.run(["-i", "input.mp4", "output.mp4"])

        assert result1.returncode == result2.returncode
        assert result1.stdout == result2.stdout
        assert result1.stderr == result2.stderr
        fake.assert_all_consumed()

    def test_record_and_replay_multiple_calls(self, tmp_path: Path) -> None:
        """Test recording and replaying multiple calls."""
        mock = MockExecutor(returncode=0, stdout=b"output", stderr=b"")
        recording_path = tmp_path / "recording.json"

        # Record
        recorder = RecordingFFmpegExecutor(mock, recording_path)
        recorder.run(["-version"])
        recorder.run(["-i", "input.mp4", "output.mp4"])
        recorder.run(["-filters"])
        recorder.save()

        # Replay
        fake = FakeFFmpegExecutor.from_file(recording_path)
        fake.run(["-version"])
        fake.run(["-i", "input.mp4", "output.mp4"])
        fake.run(["-filters"])
        fake.assert_all_consumed()

    def test_record_and_replay_with_binary_data(self, tmp_path: Path) -> None:
        """Test recording and replaying preserves binary data."""
        binary_data = bytes(range(256))
        mock = MockExecutor(returncode=0, stdout=binary_data, stderr=b"\x00\xff")
        recording_path = tmp_path / "recording.json"

        # Record
        recorder = RecordingFFmpegExecutor(mock, recording_path)
        result1 = recorder.run(["-i", "pipe:"], stdin=b"\x01\x02\x03")
        recorder.save()

        # Replay
        fake = FakeFFmpegExecutor.from_file(recording_path)
        result2 = fake.run(["-i", "pipe:"])

        assert result1.stdout == result2.stdout
        assert result1.stderr == result2.stderr


@requires_ffmpeg
class TestRealFFmpegExecutor:
    """Tests for RealFFmpegExecutor with actual ffmpeg."""

    def test_run_version_command(self) -> None:
        """Test running ffmpeg -version."""
        executor = RealFFmpegExecutor()

        result = executor.run(["-version"])

        assert result.returncode == 0
        assert b"ffmpeg version" in result.stdout
        assert result.command == ["ffmpeg", "-version"]
        assert result.duration_seconds > 0

    def test_run_with_invalid_args(self) -> None:
        """Test running ffmpeg with invalid arguments."""
        executor = RealFFmpegExecutor()

        result = executor.run(["-invalid_option_that_does_not_exist"])

        assert result.returncode != 0

    def test_custom_ffmpeg_path(self) -> None:
        """Test that custom ffmpeg path is used."""
        executor = RealFFmpegExecutor(ffmpeg_path="ffmpeg")

        result = executor.run(["-version"])

        assert result.returncode == 0
        assert result.command[0] == "ffmpeg"


class TestFFmpegExecutorProtocol:
    """Tests that implementations satisfy the FFmpegExecutor protocol."""

    def test_real_executor_satisfies_protocol(self) -> None:
        """Test RealFFmpegExecutor satisfies FFmpegExecutor protocol."""

        def accepts_executor(executor: FFmpegExecutor) -> None:
            pass

        accepts_executor(RealFFmpegExecutor())

    def test_recording_executor_satisfies_protocol(self, tmp_path: Path) -> None:
        """Test RecordingFFmpegExecutor satisfies FFmpegExecutor protocol."""

        def accepts_executor(executor: FFmpegExecutor) -> None:
            pass

        mock = MockExecutor()
        accepts_executor(RecordingFFmpegExecutor(mock, tmp_path / "recording.json"))

    def test_fake_executor_satisfies_protocol(self) -> None:
        """Test FakeFFmpegExecutor satisfies FFmpegExecutor protocol."""

        def accepts_executor(executor: FFmpegExecutor) -> None:
            pass

        accepts_executor(FakeFFmpegExecutor([]))


class TestExports:
    """Tests for module exports."""

    def test_exports_from_ffmpeg_package(self) -> None:
        """Test that ffmpeg package exports executor classes."""
        from stoat_ferret.ffmpeg import (
            ExecutionResult,
            FakeFFmpegExecutor,
            FFmpegExecutor,
            RealFFmpegExecutor,
            RecordingFFmpegExecutor,
        )

        assert ExecutionResult is not None
        assert FFmpegExecutor is not None
        assert RealFFmpegExecutor is not None
        assert RecordingFFmpegExecutor is not None
        assert FakeFFmpegExecutor is not None

"""FFmpeg executor implementations with recording and replay support.

Provides a protocol-based abstraction for FFmpeg command execution with:
- RealFFmpegExecutor: Actual subprocess execution
- RecordingFFmpegExecutor: Captures interactions for testing
- FakeFFmpegExecutor: Replays recorded interactions without subprocess
"""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass
class ExecutionResult:
    """Result of an FFmpeg execution.

    Attributes:
        returncode: Process exit code.
        stdout: Standard output as bytes.
        stderr: Standard error as bytes.
        command: Full command that was executed.
        duration_seconds: Time taken to execute.
    """

    returncode: int
    stdout: bytes
    stderr: bytes
    command: list[str]
    duration_seconds: float


class FFmpegExecutor(Protocol):
    """Protocol for FFmpeg command execution."""

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Execute FFmpeg with the given arguments.

        Args:
            args: Arguments to pass to ffmpeg (not including the ffmpeg command).
            stdin: Optional bytes to pass to stdin.
            timeout: Optional timeout in seconds.

        Returns:
            ExecutionResult with the outcome of the execution.
        """
        ...


class RealFFmpegExecutor:
    """Executor that runs FFmpeg via subprocess.

    This is the production implementation that actually executes FFmpeg
    as a subprocess.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        """Initialize with the path to ffmpeg executable.

        Args:
            ffmpeg_path: Path to the ffmpeg executable.
        """
        self.ffmpeg_path = ffmpeg_path

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Execute FFmpeg with the given arguments.

        Args:
            args: Arguments to pass to ffmpeg (not including the ffmpeg command).
            stdin: Optional bytes to pass to stdin.
            timeout: Optional timeout in seconds.

        Returns:
            ExecutionResult with the outcome of the execution.
        """
        command = [self.ffmpeg_path, *args]
        start = time.monotonic()

        result = subprocess.run(
            command,
            input=stdin,
            capture_output=True,
            timeout=timeout,
        )

        duration = time.monotonic() - start

        return ExecutionResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command=command,
            duration_seconds=duration,
        )


class RecordingFFmpegExecutor:
    """Executor that wraps another executor and records all interactions.

    Useful for capturing real FFmpeg interactions to replay in tests.
    Uses hex encoding for binary stdout/stderr data.
    """

    def __init__(self, wrapped: FFmpegExecutor, recording_path: Path) -> None:
        """Initialize with a wrapped executor and recording path.

        Args:
            wrapped: The executor to wrap and record.
            recording_path: Path to save the recording JSON file.
        """
        self._wrapped = wrapped
        self._recording_path = recording_path
        self._recordings: list[dict[str, object]] = []

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Execute FFmpeg and record the interaction.

        Args:
            args: Arguments to pass to ffmpeg.
            stdin: Optional bytes to pass to stdin.
            timeout: Optional timeout in seconds.

        Returns:
            ExecutionResult from the wrapped executor.
        """
        result = self._wrapped.run(args, stdin=stdin, timeout=timeout)

        self._recordings.append(
            {
                "args": args,
                "stdin": stdin.hex() if stdin else None,
                "result": {
                    "returncode": result.returncode,
                    "stdout": result.stdout.hex(),
                    "stderr": result.stderr.hex(),
                    "duration_seconds": result.duration_seconds,
                },
            }
        )

        return result

    def save(self) -> None:
        """Save the recorded interactions to the recording path."""
        self._recording_path.write_text(json.dumps(self._recordings, indent=2))


class FakeFFmpegExecutor:
    """Executor that replays recorded FFmpeg interactions.

    Useful for testing without actually running FFmpeg.
    """

    def __init__(self, recordings: list[dict[str, object]]) -> None:
        """Initialize with a list of recorded interactions.

        Args:
            recordings: List of recorded interaction dictionaries.
        """
        self._recordings = recordings
        self._index = 0

    @classmethod
    def from_file(cls, path: Path) -> FakeFFmpegExecutor:
        """Load recordings from a JSON file.

        Args:
            path: Path to the recording JSON file.

        Returns:
            A FakeFFmpegExecutor loaded with the recordings.
        """
        return cls(json.loads(path.read_text()))

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Replay the next recorded interaction.

        Args:
            args: Arguments (used for command reconstruction).
            stdin: Ignored (not validated against recording).
            timeout: Ignored.

        Returns:
            ExecutionResult from the recording.

        Raises:
            RuntimeError: If no more recordings are available.
        """
        if self._index >= len(self._recordings):
            raise RuntimeError(
                f"No more recordings: called {self._index + 1} times, "
                f"but only {len(self._recordings)} recorded"
            )

        recording = self._recordings[self._index]
        self._index += 1

        result_data = recording["result"]
        assert isinstance(result_data, dict)

        return ExecutionResult(
            returncode=int(result_data["returncode"]),
            stdout=bytes.fromhex(str(result_data["stdout"])),
            stderr=bytes.fromhex(str(result_data["stderr"])),
            command=["ffmpeg", *args],
            duration_seconds=float(result_data["duration_seconds"]),
        )

    def assert_all_consumed(self) -> None:
        """Assert all recordings were used.

        Raises:
            AssertionError: If not all recordings were consumed.
        """
        if self._index < len(self._recordings):
            raise AssertionError(
                f"Only {self._index} of {len(self._recordings)} recordings consumed"
            )

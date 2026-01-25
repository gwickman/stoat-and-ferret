# FFmpegExecutor Interface Design

Protocol-based interface enabling recording, faking, and real execution.

## Protocol Definition

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class ExecutionResult:
    """Result of an FFmpeg command execution."""

    returncode: int
    stdout: bytes
    stderr: bytes
    command: list[str]


class FFmpegExecutor(Protocol):
    """Protocol for executing FFmpeg commands."""

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        """Execute FFmpeg with given arguments.

        Args:
            args: Command arguments (without 'ffmpeg' prefix).
            stdin: Optional input data for pipe.
            timeout: Maximum execution time in seconds.

        Returns:
            ExecutionResult with output and return code.
        """
        ...

    def probe(self, input_path: str) -> dict:
        """Probe media file for metadata using ffprobe.

        Args:
            input_path: Path to media file.

        Returns:
            Parsed JSON output from ffprobe.
        """
        ...
```

## Real Implementation

```python
import json
import subprocess


class RealFFmpegExecutor:
    """Execute real FFmpeg commands via subprocess."""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        command = [self.ffmpeg_path, *args]
        result = subprocess.run(
            command,
            input=stdin,
            capture_output=True,
            timeout=timeout,
        )
        return ExecutionResult(
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            command=command,
        )

    def probe(self, input_path: str) -> dict:
        result = subprocess.run(
            [self.ffprobe_path, "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", input_path],
            capture_output=True,
        )
        return json.loads(result.stdout)
```

## Recording Wrapper

```python
from pathlib import Path
import json


class RecordingExecutor:
    """Wraps an executor and records all interactions."""

    def __init__(self, wrapped: FFmpegExecutor, recording_path: Path):
        self._wrapped = wrapped
        self._recording_path = recording_path
        self._recordings: list[dict] = []

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        result = self._wrapped.run(args, stdin=stdin, timeout=timeout)
        self._recordings.append({
            "type": "run",
            "args": args,
            "stdin": stdin.hex() if stdin else None,
            "result": {
                "returncode": result.returncode,
                "stdout": result.stdout.hex(),
                "stderr": result.stderr.hex(),
            },
        })
        return result

    def probe(self, input_path: str) -> dict:
        result = self._wrapped.probe(input_path)
        self._recordings.append({
            "type": "probe",
            "input_path": input_path,
            "result": result,
        })
        return result

    def save(self) -> None:
        """Save recordings to disk."""
        self._recording_path.write_text(json.dumps(self._recordings, indent=2))
```

## Fake Implementation

```python
class FakeFFmpegExecutor:
    """Replays recorded FFmpeg interactions."""

    def __init__(self, recordings: list[dict]):
        self._recordings = recordings
        self._index = 0

    @classmethod
    def from_file(cls, path: Path) -> FakeFFmpegExecutor:
        return cls(json.loads(path.read_text()))

    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        recording = self._next("run")
        # Optionally verify args match recording["args"]
        return ExecutionResult(
            returncode=recording["result"]["returncode"],
            stdout=bytes.fromhex(recording["result"]["stdout"]),
            stderr=bytes.fromhex(recording["result"]["stderr"]),
            command=["ffmpeg", *args],
        )

    def probe(self, input_path: str) -> dict:
        recording = self._next("probe")
        return recording["result"]

    def _next(self, expected_type: str) -> dict:
        if self._index >= len(self._recordings):
            raise RuntimeError("No more recorded interactions")
        recording = self._recordings[self._index]
        if recording["type"] != expected_type:
            raise RuntimeError(f"Expected {expected_type}, got {recording['type']}")
        self._index += 1
        return recording
```

## Dependency Injection

```python
class VideoProcessor:
    """Example service using FFmpegExecutor."""

    def __init__(self, executor: FFmpegExecutor):
        self._executor = executor

    def transcode(self, input_path: str, output_path: str) -> ExecutionResult:
        return self._executor.run([
            "-i", input_path,
            "-c:v", "libx264",
            "-preset", "fast",
            output_path,
        ])
```

Services accept `FFmpegExecutor` via constructor injection, allowing tests to
substitute fakes without modifying production code.

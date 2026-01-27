# Implementation Plan: Executor Protocol

## Step 1: Create Executor Module
Create `src/stoat_ferret/ffmpeg/executor.py`:

```python
from dataclasses import dataclass
from typing import Protocol, Optional
import subprocess
import time
import json
from pathlib import Path

@dataclass
class ExecutionResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    command: list[str]
    duration_seconds: float


class FFmpegExecutor(Protocol):
    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        ...
```

## Step 2: Implement RealFFmpegExecutor
```python
class RealFFmpegExecutor:
    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path
    
    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        command = [self.ffmpeg_path] + args
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
```

## Step 3: Implement RecordingFFmpegExecutor
```python
class RecordingFFmpegExecutor:
    """Wraps an executor and records all interactions.
    
    Uses hex encoding for binary stdout/stderr per EXP-002 pattern.
    """
    
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
            "args": args,
            "stdin": stdin.hex() if stdin else None,
            "result": {
                "returncode": result.returncode,
                "stdout": result.stdout.hex(),
                "stderr": result.stderr.hex(),
                "duration_seconds": result.duration_seconds,
            },
        })
        
        return result
    
    def save(self) -> None:
        self._recording_path.write_text(
            json.dumps(self._recordings, indent=2)
        )
```

## Step 4: Implement FakeFFmpegExecutor
```python
class FakeFFmpegExecutor:
    """Replays recorded FFmpeg interactions."""
    
    def __init__(self, recordings: list[dict]):
        self._recordings = recordings
        self._index = 0
    
    @classmethod
    def from_file(cls, path: Path) -> "FakeFFmpegExecutor":
        return cls(json.loads(path.read_text()))
    
    def run(
        self,
        args: list[str],
        *,
        stdin: bytes | None = None,
        timeout: float | None = None,
    ) -> ExecutionResult:
        if self._index >= len(self._recordings):
            raise RuntimeError(
                f"No more recordings: called {self._index + 1} times, "
                f"but only {len(self._recordings)} recorded"
            )
        
        recording = self._recordings[self._index]
        self._index += 1
        
        return ExecutionResult(
            returncode=recording["result"]["returncode"],
            stdout=bytes.fromhex(recording["result"]["stdout"]),
            stderr=bytes.fromhex(recording["result"]["stderr"]),
            command=["ffmpeg"] + args,
            duration_seconds=recording["result"]["duration_seconds"],
        )
    
    def assert_all_consumed(self) -> None:
        """Assert all recordings were used."""
        if self._index < len(self._recordings):
            raise AssertionError(
                f"Only {self._index} of {len(self._recordings)} recordings consumed"
            )
```

## Step 5: Add Tests
```python
def test_recording_and_replay(tmp_path):
    # Create a mock "real" executor for testing
    class MockRealExecutor:
        def run(self, args, *, stdin=None, timeout=None):
            return ExecutionResult(
                returncode=0, 
                stdout=b"output data", 
                stderr=b"", 
                command=["ffmpeg"] + args, 
                duration_seconds=0.1
            )
    
    recording_path = tmp_path / "recording.json"
    
    # Record
    recorder = RecordingFFmpegExecutor(MockRealExecutor(), recording_path)
    result1 = recorder.run(["-i", "input.mp4", "output.mp4"])
    recorder.save()
    
    # Replay
    fake = FakeFFmpegExecutor.from_file(recording_path)
    result2 = fake.run(["-i", "input.mp4", "output.mp4"])
    
    assert result1.returncode == result2.returncode
    assert result1.stdout == result2.stdout
    fake.assert_all_consumed()

def test_fake_exhausted():
    fake = FakeFFmpegExecutor([])
    with pytest.raises(RuntimeError, match="No more recordings"):
        fake.run(["-version"])
```

## Verification
- All executor implementations work correctly
- Recording/replay cycle produces identical results
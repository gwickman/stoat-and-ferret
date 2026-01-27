# Implementation Plan: Command Integration

## Step 1: Create Integration Module
Create `src/stoat_ferret/ffmpeg/integration.py`:

```python
import subprocess
from stoat_ferret_core import FFmpegCommand, CommandError
from .executor import FFmpegExecutor, ExecutionResult


class CommandExecutionError(Exception):
    """Error executing FFmpeg command."""
    def __init__(
        self, 
        message: str, 
        command: list[str] | None = None, 
        cause: Exception | None = None
    ):
        super().__init__(message)
        self.command = command
        self.cause = cause


def execute_command(
    executor: FFmpegExecutor,
    command: FFmpegCommand,
    *,
    timeout: float | None = None,
) -> ExecutionResult:
    """Execute an FFmpegCommand using the given executor.
    
    Args:
        executor: The FFmpeg executor to use
        command: The Rust FFmpegCommand to execute
        timeout: Optional timeout in seconds
    
    Returns:
        ExecutionResult with output and return code
    
    Raises:
        CommandExecutionError: If command building or execution fails
    """
    # Build command args using Rust
    try:
        args = command.build()
    except (ValueError, CommandError) as e:
        raise CommandExecutionError(f"Failed to build command: {e}", cause=e)
    
    # Execute using Python executor
    try:
        return executor.run(args, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise CommandExecutionError(
            f"Command timed out after {timeout}s", 
            command=args, 
            cause=e
        )
    except Exception as e:
        raise CommandExecutionError(
            f"Command execution failed: {e}", 
            command=args, 
            cause=e
        )
```

## Step 2: Add Integration Tests
```python
import pytest
from stoat_ferret_core import FFmpegCommand
from stoat_ferret.ffmpeg.executor import FakeFFmpegExecutor, ExecutionResult
from stoat_ferret.ffmpeg.integration import execute_command, CommandExecutionError

def test_execute_command_success():
    # Create fake with pre-recorded response
    fake = FakeFFmpegExecutor([{
        "args": ["-i", "input.mp4", "output.mp4"],
        "stdin": None,
        "result": {
            "returncode": 0, 
            "stdout": "00",  # hex for empty
            "stderr": "00", 
            "duration_seconds": 0.5
        },
    }])
    
    command = FFmpegCommand().input("input.mp4").output("output.mp4")
    result = execute_command(fake, command)
    
    assert result.returncode == 0

def test_execute_command_validation_error():
    fake = FakeFFmpegExecutor([])
    command = FFmpegCommand()  # No inputs or outputs - invalid
    
    with pytest.raises(CommandExecutionError, match="Failed to build"):
        execute_command(fake, command)

def test_execute_command_with_options():
    fake = FakeFFmpegExecutor([{
        "args": ["-y", "-i", "input.mp4", "-c:v", "libx264", "output.mp4"],
        "stdin": None,
        "result": {"returncode": 0, "stdout": "", "stderr": "", "duration_seconds": 1.0},
    }])
    
    command = (
        FFmpegCommand()
        .overwrite(True)
        .input("input.mp4")
        .output("output.mp4")
        .video_codec("libx264")
    )
    
    result = execute_command(fake, command)
    assert result.returncode == 0
```

## Verification
- Integration tests pass
- Rust → Python flow works end-to-end
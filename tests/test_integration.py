"""Tests for FFmpeg command integration layer."""

from __future__ import annotations

import pytest

from stoat_ferret.ffmpeg.executor import FakeFFmpegExecutor
from stoat_ferret.ffmpeg.integration import CommandExecutionError, execute_command
from stoat_ferret_core import FFmpegCommand


class TestExecuteCommand:
    """Tests for execute_command function."""

    def test_execute_command_success(self) -> None:
        """Test successful command execution with fake executor."""
        fake = FakeFFmpegExecutor(
            [
                {
                    "args": ["-i", "input.mp4", "output.mp4"],
                    "stdin": None,
                    "result": {
                        "returncode": 0,
                        "stdout": "",
                        "stderr": "",
                        "duration_seconds": 0.5,
                    },
                }
            ]
        )

        command = FFmpegCommand().input("input.mp4").output("output.mp4")
        result = execute_command(fake, command)

        assert result.returncode == 0
        assert result.duration_seconds == 0.5
        fake.assert_all_consumed()

    def test_execute_command_validation_error_no_inputs(self) -> None:
        """Test that missing inputs raises CommandExecutionError."""
        fake = FakeFFmpegExecutor([])
        command = FFmpegCommand().output("output.mp4")  # No inputs

        with pytest.raises(CommandExecutionError, match="Failed to build"):
            execute_command(fake, command)

    def test_execute_command_validation_error_no_outputs(self) -> None:
        """Test that missing outputs raises CommandExecutionError."""
        fake = FakeFFmpegExecutor([])
        command = FFmpegCommand().input("input.mp4")  # No outputs

        with pytest.raises(CommandExecutionError, match="Failed to build"):
            execute_command(fake, command)

    def test_execute_command_validation_error_empty_command(self) -> None:
        """Test that empty command raises CommandExecutionError."""
        fake = FakeFFmpegExecutor([])
        command = FFmpegCommand()  # No inputs or outputs

        with pytest.raises(CommandExecutionError, match="Failed to build"):
            execute_command(fake, command)

    def test_execute_command_with_options(self) -> None:
        """Test command execution with various options."""
        fake = FakeFFmpegExecutor(
            [
                {
                    "args": ["-y", "-i", "input.mp4", "-c:v", "libx264", "output.mp4"],
                    "stdin": None,
                    "result": {
                        "returncode": 0,
                        "stdout": "",
                        "stderr": "",
                        "duration_seconds": 1.0,
                    },
                }
            ]
        )

        command = (
            FFmpegCommand()
            .overwrite(True)
            .input("input.mp4")
            .output("output.mp4")
            .video_codec("libx264")
        )

        result = execute_command(fake, command)

        assert result.returncode == 0
        fake.assert_all_consumed()

    def test_execute_command_nonzero_return(self) -> None:
        """Test that non-zero return code is passed through."""
        fake = FakeFFmpegExecutor(
            [
                {
                    "args": ["-i", "missing.mp4", "output.mp4"],
                    "stdin": None,
                    "result": {
                        "returncode": 1,
                        "stdout": "",
                        "stderr": "6572726f72",  # "error" in hex
                        "duration_seconds": 0.1,
                    },
                }
            ]
        )

        command = FFmpegCommand().input("missing.mp4").output("output.mp4")
        result = execute_command(fake, command)

        assert result.returncode == 1
        assert result.stderr == b"error"
        fake.assert_all_consumed()

    def test_execute_command_with_seek_and_duration(self) -> None:
        """Test command with seek and duration options."""
        fake = FakeFFmpegExecutor(
            [
                {
                    "args": ["-ss", "10.0", "-t", "5.0", "-i", "input.mp4", "output.mp4"],
                    "stdin": None,
                    "result": {
                        "returncode": 0,
                        "stdout": "",
                        "stderr": "",
                        "duration_seconds": 0.3,
                    },
                }
            ]
        )

        command = FFmpegCommand().input("input.mp4").seek(10.0).duration(5.0).output("output.mp4")

        result = execute_command(fake, command)

        assert result.returncode == 0
        fake.assert_all_consumed()


class TestCommandExecutionError:
    """Tests for CommandExecutionError exception class."""

    def test_error_with_message_only(self) -> None:
        """Test error with just a message."""
        error = CommandExecutionError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.command is None
        assert error.cause is None

    def test_error_with_command(self) -> None:
        """Test error with command args."""
        error = CommandExecutionError("Command failed", command=["-i", "input.mp4", "output.mp4"])

        assert str(error) == "Command failed"
        assert error.command == ["-i", "input.mp4", "output.mp4"]
        assert error.cause is None

    def test_error_with_cause(self) -> None:
        """Test error with underlying cause."""
        cause = ValueError("Invalid value")
        error = CommandExecutionError("Wrapped error", cause=cause)

        assert str(error) == "Wrapped error"
        assert error.command is None
        assert error.cause is cause

    def test_error_with_all_attributes(self) -> None:
        """Test error with all attributes set."""
        cause = RuntimeError("Subprocess failed")
        error = CommandExecutionError(
            "Execution failed",
            command=["-i", "input.mp4", "output.mp4"],
            cause=cause,
        )

        assert str(error) == "Execution failed"
        assert error.command == ["-i", "input.mp4", "output.mp4"]
        assert error.cause is cause

    def test_validation_error_preserves_cause(self) -> None:
        """Test that validation errors preserve the cause chain."""
        fake = FakeFFmpegExecutor([])
        command = FFmpegCommand()

        with pytest.raises(CommandExecutionError) as exc_info:
            execute_command(fake, command)

        assert exc_info.value.cause is not None


class TestExports:
    """Tests for module exports."""

    def test_exports_from_ffmpeg_package(self) -> None:
        """Test that ffmpeg package exports integration functions."""
        from stoat_ferret.ffmpeg import CommandExecutionError, execute_command

        assert CommandExecutionError is not None
        assert execute_command is not None

"""Integration layer connecting Rust FFmpegCommand to Python executor.

This module provides the glue between the type-safe Rust command builder
and the Python executor implementations, handling error translation and
context wrapping.
"""

from __future__ import annotations

import subprocess

from stoat_ferret_core import CommandError, FFmpegCommand

from .executor import ExecutionResult, FFmpegExecutor


class CommandExecutionError(Exception):
    """Error executing FFmpeg command.

    Attributes:
        command: The FFmpeg command arguments, if available.
        cause: The underlying exception that caused this error.
    """

    def __init__(
        self,
        message: str,
        command: list[str] | None = None,
        cause: Exception | None = None,
    ) -> None:
        """Initialize the error with context.

        Args:
            message: Human-readable error message.
            command: The FFmpeg command arguments that failed.
            cause: The underlying exception that caused this error.
        """
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

    This function bridges the Rust FFmpegCommand builder with Python
    executor implementations. It handles command building, error
    translation, and execution.

    Args:
        executor: The FFmpeg executor to use (real, fake, or recording).
        command: The Rust FFmpegCommand to execute.
        timeout: Optional timeout in seconds for execution.

    Returns:
        ExecutionResult with output, return code, and execution details.

    Raises:
        CommandExecutionError: If command building or execution fails.
            The cause attribute contains the underlying exception.
    """
    # Build command args using Rust
    try:
        args = command.build()
    except (ValueError, CommandError) as e:
        raise CommandExecutionError(f"Failed to build command: {e}", cause=e) from e

    # Execute using Python executor
    try:
        return executor.run(args, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        raise CommandExecutionError(
            f"Command timed out after {timeout}s",
            command=args,
            cause=e,
        ) from e
    except Exception as e:
        raise CommandExecutionError(
            f"Command execution failed: {e}",
            command=args,
            cause=e,
        ) from e

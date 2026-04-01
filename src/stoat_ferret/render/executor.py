"""Render executor with FFmpeg process management.

Manages FFmpeg subprocess lifecycle with real-time progress parsing via
Rust PyO3 bindings, cross-platform graceful cancellation using stdin ``q``
(not ``process.terminate()``), configurable timeout, and temp file cleanup.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from pathlib import Path

import structlog

from stoat_ferret.render.models import RenderJob

try:
    from stoat_ferret_core import calculate_progress, parse_ffmpeg_progress

    _HAS_RUST_BINDINGS = True
except ImportError:
    _HAS_RUST_BINDINGS = False

logger = structlog.get_logger(__name__)

# Type alias for progress callbacks (progress ratio 0.0-1.0)
ProgressCallback = Callable[[str, float], Awaitable[None]]


class RenderExecutor:
    """Execute FFmpeg render jobs with progress tracking and cancellation.

    Manages the full subprocess lifecycle: start, progress monitoring,
    timeout enforcement, graceful cancellation via stdin ``q``, and
    temp file cleanup. Never uses ``process.terminate()`` which corrupts
    output on Windows.

    Args:
        timeout_seconds: Maximum render duration before killing the process.
        cancel_grace_seconds: Seconds to wait for FFmpeg to finalize after cancel.
        progress_callback: Optional async callback invoked with (job_id, progress).
        ffmpeg_path: Path to the ffmpeg executable.
    """

    def __init__(
        self,
        *,
        timeout_seconds: int = 3600,
        cancel_grace_seconds: int = 10,
        progress_callback: ProgressCallback | None = None,
        ffmpeg_path: str = "ffmpeg",
    ) -> None:
        self._timeout_seconds = timeout_seconds
        self._cancel_grace_seconds = cancel_grace_seconds
        self._progress_callback = progress_callback
        self._ffmpeg_path = ffmpeg_path
        self._active_processes: dict[str, asyncio.subprocess.Process] = {}
        self._temp_files: dict[str, list[Path]] = {}

    def register_temp_file(self, job_id: str, path: Path) -> None:
        """Register a temp file for cleanup when the job terminates.

        Args:
            job_id: The render job ID.
            path: Path to the temporary file.
        """
        self._temp_files.setdefault(job_id, []).append(path)

    async def execute(
        self,
        job: RenderJob,
        command: list[str],
        *,
        total_duration_us: int = 0,
    ) -> bool:
        """Execute an FFmpeg render job.

        Starts the FFmpeg subprocess, parses progress from stdout via
        the Rust ``parse_ffmpeg_progress`` binding, enforces a timeout,
        and cleans up temp files on completion or failure.

        Args:
            job: The render job to execute.
            command: Full FFmpeg command arguments (including ffmpeg path).
            total_duration_us: Total expected duration in microseconds for
                progress calculation. 0 disables progress reporting.

        Returns:
            True if FFmpeg completed successfully, False otherwise.
        """
        job_id = job.id
        log = logger.bind(job_id=job_id)

        log.info("render_executor.starting", command=command)
        start = time.monotonic()

        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        self._active_processes[job_id] = process

        try:
            success = await asyncio.wait_for(
                self._run_process(job_id, process, total_duration_us),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError:
            log.warning(
                "render_executor.timeout",
                timeout_seconds=self._timeout_seconds,
                elapsed=round(time.monotonic() - start, 2),
            )
            await self._kill_process(job_id, process)
            return False
        finally:
            self._active_processes.pop(job_id, None)
            self._cleanup_temp_files(job_id)

        elapsed = time.monotonic() - start
        log.info(
            "render_executor.finished",
            success=success,
            elapsed_seconds=round(elapsed, 2),
            returncode=process.returncode,
        )
        return success

    async def cancel(self, job_id: str) -> bool:
        """Cancel a running render job gracefully.

        Sends ``q`` via stdin to request FFmpeg to finalize and exit.
        If the process does not exit within the grace period, escalates
        to ``process.kill()``. Never uses ``process.terminate()``.

        Args:
            job_id: The render job ID to cancel.

        Returns:
            True if the process was found and cancellation initiated,
            False if no active process was found for the job ID.
        """
        process = self._active_processes.get(job_id)
        if process is None:
            logger.debug("render_executor.cancel_no_process", job_id=job_id)
            return False

        log = logger.bind(job_id=job_id)
        log.info("render_executor.cancelling", pid=process.pid)

        try:
            # Send 'q' via stdin for graceful FFmpeg shutdown
            if process.stdin is not None:
                process.stdin.write(b"q")
                await process.stdin.drain()
                process.stdin.close()
        except (BrokenPipeError, ConnectionResetError, OSError):
            log.debug("render_executor.cancel_stdin_closed")

        # Wait for graceful shutdown. Shield process.wait() so that
        # timeout cancellation does not propagate to the shared process
        # future — which would cancel _run_process on Python 3.10.
        try:
            await asyncio.wait_for(
                asyncio.shield(process.wait()),
                timeout=self._cancel_grace_seconds,
            )
            log.info("render_executor.cancelled_gracefully", returncode=process.returncode)
        except asyncio.TimeoutError:
            log.warning("render_executor.cancel_escalating_to_kill")
            await self._kill_process(job_id, process)

        self._active_processes.pop(job_id, None)
        self._cleanup_temp_files(job_id)
        return True

    async def _run_process(
        self,
        job_id: str,
        process: asyncio.subprocess.Process,
        total_duration_us: int,
    ) -> bool:
        """Read FFmpeg output and parse progress until process exits.

        Args:
            job_id: The render job ID.
            process: The FFmpeg subprocess.
            total_duration_us: Total expected duration for progress calculation.

        Returns:
            True if FFmpeg exited with return code 0.
        """
        stdout_chunks: list[bytes] = []

        if process.stdout is not None:
            while True:
                try:
                    # Timeout readline so we detect a killed process on
                    # Python 3.10 where pipe close doesn't unblock reads.
                    chunk = await asyncio.wait_for(process.stdout.readline(), timeout=1.0)
                except asyncio.TimeoutError:
                    if process.returncode is not None:
                        break
                    continue
                if not chunk:
                    break
                stdout_chunks.append(chunk)

                if self._progress_callback and total_duration_us > 0:
                    await self._parse_and_report_progress(job_id, chunk, total_duration_us)

        # Wait for process to exit after stdout is exhausted
        await process.wait()

        return process.returncode == 0

    async def _parse_and_report_progress(
        self,
        job_id: str,
        chunk: bytes,
        total_duration_us: int,
    ) -> None:
        """Parse a chunk of FFmpeg output and invoke the progress callback.

        Uses the Rust ``parse_ffmpeg_progress`` and ``calculate_progress``
        functions via PyO3 bindings.

        Args:
            job_id: The render job ID.
            chunk: Raw bytes from FFmpeg stdout.
            total_duration_us: Total expected duration in microseconds.
        """
        if not _HAS_RUST_BINDINGS:
            return

        try:
            line = chunk.decode("utf-8", errors="replace")
            updates = parse_ffmpeg_progress(line)
            for update in updates:
                progress = calculate_progress(update.out_time_us, total_duration_us)
                if self._progress_callback is not None:
                    await self._progress_callback(job_id, progress)
        except Exception:
            logger.debug("render_executor.progress_parse_error", job_id=job_id, exc_info=True)

    async def _kill_process(
        self,
        job_id: str,
        process: asyncio.subprocess.Process,
    ) -> None:
        """Kill the FFmpeg process. Does NOT use terminate().

        Args:
            job_id: The render job ID.
            process: The subprocess to kill.
        """
        if process.returncode is not None:
            return

        logger.warning("render_executor.killing", job_id=job_id, pid=process.pid)
        try:
            process.kill()
            await process.wait()
        except ProcessLookupError:
            pass

    def _cleanup_temp_files(self, job_id: str) -> None:
        """Remove registered temp files for a job.

        Args:
            job_id: The render job ID whose temp files should be cleaned up.
        """
        temp_files = self._temp_files.pop(job_id, [])
        for path in temp_files:
            try:
                if path.exists():
                    path.unlink()
                    logger.debug(
                        "render_executor.temp_file_removed",
                        job_id=job_id,
                        path=str(path),
                    )
            except OSError:
                logger.warning(
                    "render_executor.temp_file_cleanup_failed",
                    job_id=job_id,
                    path=str(path),
                    exc_info=True,
                )

"""Job queue protocol and implementations."""

from __future__ import annotations

import asyncio
import enum
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

import structlog

logger = structlog.get_logger(__name__)


class JobStatus(enum.Enum):
    """Status of a job in the queue."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"
    FAILED = "failed"
    TIMEOUT = "timeout"


class JobOutcome(enum.Enum):
    """Configurable outcome for InMemoryJobQueue."""

    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"


@dataclass
class JobResult:
    """Result of a completed job.

    Attributes:
        job_id: Unique identifier for the job.
        status: Final status of the job.
        result: The return value if successful, None otherwise.
        error: Error message if failed or timed out, None otherwise.
    """

    job_id: str
    status: JobStatus
    result: Any = None
    error: str | None = None


class AsyncJobQueue(Protocol):
    """Protocol for async job queue operations.

    Implementations must provide methods to submit jobs,
    check their status, and retrieve results.
    """

    async def submit(self, job_type: str, payload: dict[str, Any]) -> str:
        """Submit a job to the queue.

        Args:
            job_type: Type identifier for the job.
            payload: Job parameters.

        Returns:
            The unique job ID.
        """
        ...

    async def get_status(self, job_id: str) -> JobStatus:
        """Get the current status of a job.

        Args:
            job_id: The job ID.

        Returns:
            Current job status.

        Raises:
            KeyError: If the job ID is not found.
        """
        ...

    async def get_result(self, job_id: str) -> JobResult:
        """Get the result of a completed job.

        Args:
            job_id: The job ID.

        Returns:
            The job result.

        Raises:
            KeyError: If the job ID is not found.
        """
        ...


@dataclass
class _JobEntry:
    """Internal storage for a submitted job."""

    job_id: str
    job_type: str
    payload: dict[str, Any]
    result: JobResult = field(init=False)

    def __post_init__(self) -> None:
        """Initialize with pending result."""
        self.result = JobResult(job_id=self.job_id, status=JobStatus.PENDING)


class InMemoryJobQueue:
    """In-memory job queue with synchronous deterministic execution.

    Jobs are executed synchronously at submit time for deterministic
    test behavior. Outcomes can be configured per job type.
    """

    def __init__(self) -> None:
        """Initialize the job queue with empty storage."""
        self._jobs: dict[str, _JobEntry] = {}
        self._outcomes: dict[str, JobOutcome] = {}
        self._default_outcome: JobOutcome = JobOutcome.SUCCESS
        self._results: dict[str, Any] = {}

    def configure_outcome(
        self,
        job_type: str,
        outcome: JobOutcome,
        result: Any = None,
        error: str | None = None,
    ) -> None:
        """Configure the outcome for a job type.

        Args:
            job_type: The job type to configure.
            outcome: The outcome to produce when this type is submitted.
            result: The result value for SUCCESS outcomes.
            error: The error message for FAILURE/TIMEOUT outcomes.
        """
        self._outcomes[job_type] = outcome
        if result is not None:
            self._results[job_type] = result
        if error is not None:
            self._results[f"{job_type}:error"] = error

    def set_default_outcome(self, outcome: JobOutcome) -> None:
        """Set the default outcome for unconfigured job types.

        Args:
            outcome: The default outcome.
        """
        self._default_outcome = outcome

    async def submit(self, job_type: str, payload: dict[str, Any]) -> str:
        """Submit and synchronously execute a job.

        Args:
            job_type: Type identifier for the job.
            payload: Job parameters.

        Returns:
            The unique job ID.
        """
        job_id = str(uuid.uuid4())
        entry = _JobEntry(job_id=job_id, job_type=job_type, payload=payload)

        outcome = self._outcomes.get(job_type, self._default_outcome)

        if outcome == JobOutcome.SUCCESS:
            result_value = self._results.get(job_type, {"status": "ok"})
            entry.result = JobResult(
                job_id=job_id,
                status=JobStatus.COMPLETE,
                result=result_value,
            )
        elif outcome == JobOutcome.FAILURE:
            error_msg = self._results.get(f"{job_type}:error", f"Job {job_type} failed")
            entry.result = JobResult(
                job_id=job_id,
                status=JobStatus.FAILED,
                error=error_msg,
            )
        elif outcome == JobOutcome.TIMEOUT:
            error_msg = self._results.get(f"{job_type}:error", f"Job {job_type} timed out")
            entry.result = JobResult(
                job_id=job_id,
                status=JobStatus.TIMEOUT,
                error=error_msg,
            )

        self._jobs[job_id] = entry
        return job_id

    async def get_status(self, job_id: str) -> JobStatus:
        """Get the current status of a job.

        Args:
            job_id: The job ID.

        Returns:
            Current job status.

        Raises:
            KeyError: If the job ID is not found.
        """
        if job_id not in self._jobs:
            raise KeyError(f"Job {job_id} not found")
        return self._jobs[job_id].result.status

    async def get_result(self, job_id: str) -> JobResult:
        """Get the result of a completed job.

        Args:
            job_id: The job ID.

        Returns:
            The job result.

        Raises:
            KeyError: If the job ID is not found.
        """
        if job_id not in self._jobs:
            raise KeyError(f"Job {job_id} not found")
        return self._jobs[job_id].result


# Type alias for job handler functions
JobHandler = Callable[[str, dict[str, Any]], Awaitable[Any]]


@dataclass
class _AsyncJobEntry:
    """Internal storage for a job in the async queue."""

    job_id: str
    job_type: str
    payload: dict[str, Any]
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: str | None = None


class AsyncioJobQueue:
    """Async job queue using asyncio.Queue with a background worker.

    Jobs are submitted to an internal asyncio.Queue and processed by a
    background worker coroutine. Each job is dispatched to a registered
    handler based on job_type.

    Attributes:
        DEFAULT_TIMEOUT: Default per-job timeout in seconds (300 = 5 minutes).
    """

    DEFAULT_TIMEOUT: float = 300.0

    def __init__(self, *, timeout: float | None = None) -> None:
        """Initialize the async job queue.

        Args:
            timeout: Per-job timeout in seconds. Defaults to DEFAULT_TIMEOUT.
        """
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._jobs: dict[str, _AsyncJobEntry] = {}
        self._handlers: dict[str, JobHandler] = {}
        self._timeout = timeout if timeout is not None else self.DEFAULT_TIMEOUT

    def register_handler(self, job_type: str, handler: JobHandler) -> None:
        """Register a handler for a job type.

        Args:
            job_type: The job type identifier.
            handler: Async callable that processes the job payload.
        """
        self._handlers[job_type] = handler

    async def submit(self, job_type: str, payload: dict[str, Any]) -> str:
        """Submit a job to the queue for async processing.

        Args:
            job_type: Type identifier for the job.
            payload: Job parameters.

        Returns:
            The unique job ID.
        """
        job_id = str(uuid.uuid4())
        entry = _AsyncJobEntry(job_id=job_id, job_type=job_type, payload=payload)
        self._jobs[job_id] = entry
        await self._queue.put(job_id)
        logger.info("job_submitted", job_id=job_id, job_type=job_type)
        return job_id

    async def get_status(self, job_id: str) -> JobStatus:
        """Get the current status of a job.

        Args:
            job_id: The job ID.

        Returns:
            Current job status.

        Raises:
            KeyError: If the job ID is not found.
        """
        if job_id not in self._jobs:
            raise KeyError(f"Job {job_id} not found")
        return self._jobs[job_id].status

    async def get_result(self, job_id: str) -> JobResult:
        """Get the result of a job.

        Args:
            job_id: The job ID.

        Returns:
            The job result.

        Raises:
            KeyError: If the job ID is not found.
        """
        if job_id not in self._jobs:
            raise KeyError(f"Job {job_id} not found")
        entry = self._jobs[job_id]
        return JobResult(
            job_id=entry.job_id,
            status=entry.status,
            result=entry.result,
            error=entry.error,
        )

    async def process_jobs(self) -> None:
        """Worker coroutine that processes jobs from the queue.

        Runs indefinitely, pulling jobs from the queue and dispatching them
        to registered handlers. Handles timeout and errors gracefully.
        Exits cleanly on cancellation.
        """
        logger.info("worker_started")
        try:
            while True:
                job_id = await self._queue.get()
                entry = self._jobs.get(job_id)
                if entry is None:
                    self._queue.task_done()
                    continue

                handler = self._handlers.get(entry.job_type)
                if handler is None:
                    entry.status = JobStatus.FAILED
                    entry.error = f"No handler registered for job type: {entry.job_type}"
                    logger.error(
                        "job_no_handler",
                        job_id=job_id,
                        job_type=entry.job_type,
                    )
                    self._queue.task_done()
                    continue

                entry.status = JobStatus.RUNNING
                logger.info("job_started", job_id=job_id, job_type=entry.job_type)

                try:
                    result = await asyncio.wait_for(
                        handler(entry.job_type, entry.payload),
                        timeout=self._timeout,
                    )
                    entry.status = JobStatus.COMPLETE
                    entry.result = result
                    logger.info("job_completed", job_id=job_id, job_type=entry.job_type)
                except TimeoutError:
                    entry.status = JobStatus.TIMEOUT
                    entry.error = f"Job timed out after {self._timeout}s"
                    logger.warning(
                        "job_timeout",
                        job_id=job_id,
                        job_type=entry.job_type,
                        timeout=self._timeout,
                    )
                except Exception as exc:
                    entry.status = JobStatus.FAILED
                    entry.error = str(exc)
                    logger.error(
                        "job_failed",
                        job_id=job_id,
                        job_type=entry.job_type,
                        error=str(exc),
                    )
                finally:
                    self._queue.task_done()
        except asyncio.CancelledError:
            logger.info("worker_stopped")
            raise

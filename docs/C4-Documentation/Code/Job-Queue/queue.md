# Job Queue

**Source:** `src/stoat_ferret/jobs/queue.py`
**Component:** Job Queue

## Purpose

Provides protocol and implementations for async job queue operations with support for both synchronous deterministic testing (InMemoryJobQueue) and true async processing (AsyncioJobQueue). Includes job status tracking, progress reporting, and timeout management.

## Public Interface

### Enums

- `JobStatus`: Status of a job in the queue
  - `PENDING = "pending"`: Job queued but not yet running
  - `RUNNING = "running"`: Job currently executing
  - `COMPLETE = "complete"`: Job completed successfully
  - `FAILED = "failed"`: Job execution failed
  - `TIMEOUT = "timeout"`: Job exceeded timeout
  - `CANCELLED = "cancelled"`: Job was cancelled

- `JobOutcome`: Configurable outcome for InMemoryJobQueue
  - `SUCCESS = "success"`: Job should complete successfully
  - `FAILURE = "failure"`: Job should fail
  - `TIMEOUT = "timeout"`: Job should timeout

### Classes

- `JobResult`: Result of a completed job
  - `job_id: str`: Unique identifier for the job
  - `status: JobStatus`: Final status of the job
  - `result: Any = None`: The return value if successful
  - `error: str | None = None`: Error message if failed or timed out
  - `progress: float | None = None`: Progress value 0.0-1.0 for running jobs

- `AsyncJobQueue`: Protocol for async job queue operations
  - `async submit(job_type: str, payload: dict[str, Any]) -> str`: Submit a job and return job ID
  - `async get_status(job_id: str) -> JobStatus`: Get current job status (raises KeyError if not found)
  - `async get_result(job_id: str) -> JobResult`: Get result of completed job (raises KeyError if not found)
  - `set_progress(job_id: str, value: float) -> None`: Update progress for running job
  - `cancel(job_id: str) -> None`: Request job cancellation

- `InMemoryJobQueue`: In-memory job queue with synchronous deterministic execution
  - `__init__() -> None`: Initialize empty queue
  - `register_handler(job_type: str, handler: JobHandler) -> None`: Register async handler for job type
  - `configure_outcome(job_type: str, outcome: JobOutcome, result: Any = None, error: str | None = None) -> None`: Configure preconfigured outcome
  - `set_default_outcome(outcome: JobOutcome) -> None`: Set default outcome for unconfigured types
  - `set_progress(job_id: str, value: float) -> None`: No-op (for protocol compliance)
  - `cancel(job_id: str) -> None`: No-op (for protocol compliance)
  - `async submit(job_type: str, payload: dict[str, Any]) -> str`: Submit and synchronously execute
  - `async get_status(job_id: str) -> JobStatus`: Get job status
  - `async get_result(job_id: str) -> JobResult`: Get job result

- `AsyncioJobQueue`: Async job queue using asyncio.Queue with background worker
  - `DEFAULT_TIMEOUT: float = 300.0`: Default per-job timeout (5 minutes)
  - `__init__(*, timeout: float | None = None) -> None`: Initialize with optional timeout
  - `register_handler(job_type: str, handler: JobHandler) -> None`: Register async handler
  - `set_progress(job_id: str, value: float) -> None`: Update progress for running job
  - `cancel(job_id: str) -> None`: Request cancellation (sets event; raises KeyError if not found)
  - `async submit(job_type: str, payload: dict[str, Any]) -> str`: Submit job to queue
  - `async get_status(job_id: str) -> JobStatus`: Get job status (raises KeyError if not found)
  - `async get_result(job_id: str) -> JobResult`: Get job result (raises KeyError if not found)
  - `async process_jobs() -> None`: Worker coroutine that processes jobs from queue

### Type Aliases

- `JobHandler = Callable[[str, dict[str, Any]], Awaitable[Any]]`: Async callable that processes job

## Dependencies

### Internal Dependencies

None

### External Dependencies

- `asyncio`: Async primitives and subprocess:
  - `asyncio.Queue`: Job queue
  - `asyncio.Event`: Cancellation signaling
  - `asyncio.wait_for()`: Timeout enforcement
  - `asyncio.TimeoutError`: Timeout exception (Python 3.10 compatible)
  - `asyncio.CancelledError`: Graceful worker shutdown
- `uuid`: Job ID generation via `uuid.uuid4()`
- `enum`: Status and outcome enumerations
- `dataclasses`: Data class definitions with field()
- `structlog`: Structured logging via `structlog.get_logger(__name__)`

## Key Implementation Details

### Protocol-Based Design

`AsyncJobQueue` is a Protocol enabling:
- Multiple implementations (InMemory, Asyncio, custom)
- Type-safe structural subtyping
- Decoupling implementations from consumers

### InMemoryJobQueue Pattern

Synchronous deterministic testing implementation:
- Jobs execute immediately at `submit()` time
- No background processing
- Two execution modes:
  1. **Handler mode**: If handler registered, executes it synchronously
  2. **Outcome mode**: Uses preconfigured outcome (SUCCESS/FAILURE/TIMEOUT)
- Useful for unit tests where determinism is needed
- No actual async execution despite async method signatures

**Execution Flow:**
1. Generate UUID job_id
2. Create _JobEntry with PENDING status
3. Check for registered handler
4. If handler exists:
   - Execute handler synchronously with `await handler(...)`
   - Catch Exception and set FAILED status
5. If no handler:
   - Use configured outcome or default
   - Set result/status accordingly
6. Store entry and return job_id

### AsyncioJobQueue Pattern

True async queue-based implementation:
- Jobs submitted to internal asyncio.Queue
- Background worker processes jobs from queue
- Each job dispatched to registered handler
- Supports timeout, cancellation, progress tracking

**Job Lifecycle:**
1. `submit()`: Create entry, add to queue, return job_id
2. `process_jobs()`: Worker pulls from queue and processes
3. Handler execution with timeout: `asyncio.wait_for(handler(...), timeout=self._timeout)`
4. Status transitions: PENDING → RUNNING → COMPLETE/FAILED/TIMEOUT/CANCELLED
5. Result stored in job entry for retrieval

**Timeout Implementation:**
- Uses `asyncio.wait_for()` with per-job timeout
- Caught as `asyncio.TimeoutError` (Python 3.10 compatible)
- Sets status to TIMEOUT with error message including timeout duration

**Cancellation Pattern:**
- Each job entry has `cancel_event: asyncio.Event`
- `cancel()` sets the event, handler checks it cooperatively
- If cancel_event is set after completion, status is set to CANCELLED
- Enables graceful cancellation without forceful termination

**Payload Injection:**
- Workers inject special keys into payload:
  - `_job_id`: Current job ID
  - `_cancel_event`: asyncio.Event for cancellation
- Handlers can use these to check cancellation and report job_id

**Worker Lifecycle:**
- Runs in separate task: `asyncio.create_task(queue.process_jobs())`
- Runs indefinitely in `while True` loop
- Exits gracefully on `asyncio.CancelledError`
- Logs worker_started and worker_stopped

### Error Handling

Comprehensive error handling patterns:

**InMemoryJobQueue:**
- Catches Exception from handler execution
- Stores error message in JobResult
- Does not re-raise (for testing determinism)

**AsyncioJobQueue:**
- asyncio.TimeoutError: Sets TIMEOUT status with error message
- Exception from handler: Sets FAILED status with error message
- No handler registered: Sets FAILED status immediately
- Exceptions logged with job_id and context
- Finally block always calls `self._queue.task_done()`

### Structured Logging

Both implementations use structlog:
- `job_submitted`: job_id, job_type
- `job_started`: job_id, job_type
- `job_completed`: job_id, job_type
- `job_timeout`: job_id, job_type, timeout
- `job_failed`: job_id, job_type, error message
- `job_cancelled`: job_id, job_type
- `job_no_handler`: job_id, job_type
- `job_cancel_requested`: job_id
- `worker_started`: No context
- `worker_stopped`: No context (on CancelledError)

## Relationships

- **Used by:** Job processing subsystems that need to queue and execute async operations
- **Uses:** asyncio for async primitives, structlog for observability

# Job Queue

## Purpose

The Job Queue component provides the infrastructure for executing long-running operations asynchronously in the background. It defines a protocol for async job submission, status tracking, progress reporting, and cancellation, with two implementations: a true asyncio queue for production use and an in-memory synchronous queue for testing.

## Responsibilities

- Accept job submissions keyed by job type and return an opaque job ID immediately
- Dispatch jobs to registered type-specific handler functions
- Track job lifecycle transitions: PENDING → RUNNING → COMPLETE / FAILED / TIMEOUT / CANCELLED
- Report per-job progress as a 0.0–1.0 float that handlers update incrementally
- Support cooperative cancellation via per-job asyncio events that handlers check at yield points
- Enforce a configurable per-job timeout (default 5 minutes) using `asyncio.wait_for()`
- Inject `_job_id` and `_cancel_event` keys into each job's payload so handlers can self-report progress and check cancellation without additional arguments
- Provide an in-memory implementation with configurable pre-set outcomes for deterministic unit tests

## Interfaces

### Provided Interfaces

**AsyncJobQueue (protocol)**
- `submit(job_type: str, payload: dict) -> str` — Enqueue a job; returns job ID
- `get_status(job_id: str) -> JobStatus` — Returns current status; raises `KeyError` if unknown
- `get_result(job_id: str) -> JobResult` — Returns result struct; raises `KeyError` if unknown
- `set_progress(job_id: str, value: float) -> None` — Update progress (0.0–1.0) for a running job
- `cancel(job_id: str) -> None` — Request cancellation; raises `KeyError` if unknown

**JobStatus (enum)**
- `PENDING`, `RUNNING`, `COMPLETE`, `FAILED`, `TIMEOUT`, `CANCELLED`

**JobResult (dataclass)**
- `job_id: str`
- `status: JobStatus`
- `result: Any` — Return value on success, None otherwise
- `error: str | None` — Error message on failure
- `progress: float | None` — Most recent progress value

**AsyncioJobQueue (class)**
- `register_handler(job_type: str, handler: JobHandler) -> None` — Register async callable for a job type
- `async process_jobs() -> None` — Worker coroutine; must be started as an asyncio task by the caller

**InMemoryJobQueue (class)**
- `register_handler(job_type: str, handler: JobHandler) -> None`
- `configure_outcome(job_type: str, outcome: JobOutcome, result, error) -> None` — Pre-configure synthetic result
- `set_default_outcome(outcome: JobOutcome) -> None`

**Type Alias**
- `JobHandler = Callable[[str, dict], Awaitable[Any]]` — Async function receiving (job_type, payload) and returning result

### Required Interfaces

None — the component has no dependencies on other application components. It uses only Python standard library asyncio primitives.

## Code Modules

| Module | Source | Purpose |
|--------|--------|---------|
| Queue | `src/stoat_ferret/jobs/queue.py` | `AsyncJobQueue` protocol; `JobStatus` and `JobOutcome` enums; `JobResult` dataclass; `AsyncioJobQueue` (production, asyncio.Queue-based worker); `InMemoryJobQueue` (testing, synchronous execution) |

## Key Behaviors

**Worker Lifecycle:** `AsyncioJobQueue.process_jobs()` runs in an infinite loop, pulling entries from an internal `asyncio.Queue`. The API Gateway creates it as an asyncio task during lifespan startup and cancels it on shutdown. The worker exits cleanly on `asyncio.CancelledError`.

**Payload Injection:** Before invoking a handler, the worker injects `_job_id` and `_cancel_event` into the payload dict. Handlers use `_cancel_event.is_set()` to check whether cancellation has been requested before each unit of work.

**Timeout Enforcement:** The worker wraps each handler call in `asyncio.wait_for(..., timeout=self._timeout)`. Timed-out jobs transition to the `TIMEOUT` state. The implementation catches `asyncio.TimeoutError` explicitly (not `builtins.TimeoutError`) for Python 3.10 compatibility.

**Cancellation Semantics:** `cancel()` sets the job's `cancel_event` asyncio Event. The handler checks this cooperatively; the job transitions to `CANCELLED` only after the handler observes the event. If a job is already in a terminal state when `cancel()` is called, a `KeyError` is not raised — the request is ignored.

**In-Memory Testing Mode:** `InMemoryJobQueue` executes handlers synchronously at `submit()` time (no background task). This enables deterministic test assertions immediately after submission. For tests that do not register a handler, `configure_outcome()` allows pre-setting a synthetic `SUCCESS`, `FAILURE`, or `TIMEOUT` result.

## Inter-Component Relationships

```
API Gateway
    |-- creates and starts worker --> Job Queue (AsyncioJobQueue.process_jobs)
    |-- submits scan jobs --> Job Queue
    |-- submits batch render jobs --> Job Queue
    |-- polls status --> Job Queue
    |-- requests cancellation --> Job Queue
    |
    |-- registers handler: scan --> Job Queue
    |   (handler calls FFmpeg Integration, Data Access)
    |
    |-- queries progress --> Job Queue (router-jobs.py)

Tests
    |-- injects --> Job Queue (InMemoryJobQueue)
```

## Version History

| Version | Changes |
|---------|---------|
| v009 | Initial job queue with protocol, AsyncioJobQueue, InMemoryJobQueue, and job status tracking |

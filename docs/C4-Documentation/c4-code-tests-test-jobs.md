# C4 Code Level: Job Queue Tests

## Overview

- **Name**: Job Queue Tests
- **Description**: Tests for the AsyncioJobQueue and worker lifecycle integration with FastAPI lifespan
- **Location**: [tests/test_jobs/](../../tests/test_jobs/)
- **Language**: Python (pytest, asyncio)
- **Purpose**: Validates job submission, status tracking, completion, failure, timeout behavior, and worker lifecycle management

## Code Elements

### Test Inventory

| File | Tests | Coverage |
|------|-------|----------|
| test_asyncio_queue.py | 10 | AsyncioJobQueue submit, status, completion, failure, timeout |
| test_worker.py | 4 | Worker cancellation, lifespan integration |
| **Total** | **14** | **Job queue infrastructure** |

### test_asyncio_queue.py

#### Test Handlers (Test Fixtures)
- `_success_handler(job_type: str, payload: dict[str, Any]) -> dict[str, str]` (line 16)
  - Returns immediately with success response

- `_slow_handler(job_type: str, payload: dict[str, Any]) -> str` (line 21)
  - Sleeps 10 seconds to trigger timeout during testing

- `_failing_handler(job_type: str, payload: dict[str, Any]) -> None` (line 27)
  - Raises RuntimeError to test failure handling

#### Test Classes

**TestSubmitAndStatus** (5 tests, lines 32-70)
- `test_submit_returns_job_id()` — Verifies submit returns non-empty string ID
- `test_submit_generates_unique_ids()` — Each submit creates different job IDs
- `test_initial_status_is_pending()` — New jobs start in PENDING status
- `test_get_status_unknown_job_raises()` — Raises KeyError for unknown job
- `test_get_result_unknown_job_raises()` — Raises KeyError for unknown result

**TestJobCompletion** (2 tests, lines 72-119)
- `test_job_completes_successfully()` — Worker processes job to COMPLETE status with result
- `test_multiple_jobs_processed_in_order()` — Sequential job processing maintains order

**TestJobFailure** (2 tests, lines 121-161)
- `test_handler_exception_sets_failed_status()` — Exception produces FAILED status + error message
- `test_no_handler_sets_failed_status()` — Missing handler produces FAILED status

**TestJobTimeout** (3 tests, lines 163-194)
- `test_timeout_sets_timeout_status()` — Slow job exceeding timeout gets TIMEOUT status
- `test_custom_timeout_is_used()` — Custom timeout value is stored and used
- `test_default_timeout_is_300()` — Default timeout is 300 seconds (5 minutes)

### test_worker.py

#### Test Handler
- `_noop_handler(job_type: str, payload: dict[str, Any]) -> str` (line 17)
  - Minimal handler returning "ok" for worker lifecycle testing

#### Test Classes

**TestWorkerLifecycle** (2 tests, lines 22-53)
- `test_worker_cancels_cleanly()` — Worker exits without error on cancellation signal
- `test_worker_processes_job_then_cancels()` — Job completes before cancellation takes effect

**TestLifespanIntegration** (2 tests, lines 55-70)
- `test_app_with_injected_job_queue()` — DI injects queue into app.state
- `test_app_without_injection_works()` — create_app() works without injection (production path)

## Dependencies

### Internal Dependencies
- `stoat_ferret.jobs.queue` (AsyncioJobQueue, JobStatus)
- `stoat_ferret.api.app` (create_app)

### External Dependencies
- pytest (5.0+)
- asyncio (Python standard library)

## Relationships

```mermaid
---
title: Job Queue Test Architecture
---
classDiagram
    namespace TestSuites {
        class AsyncioQueueTests {
            +TestSubmitAndStatus: 5 tests
            +TestJobCompletion: 2 tests
            +TestJobFailure: 2 tests
            +TestJobTimeout: 3 tests
        }
        class WorkerTests {
            +TestWorkerLifecycle: 2 tests
            +TestLifespanIntegration: 2 tests
        }
    }
    namespace UnderTest {
        class AsyncioJobQueue {
            +submit(job_type, payload)
            +get_status(job_id)
            +get_result(job_id)
            +process_jobs()
            +register_handler(job_type, fn)
            -_timeout: float
        }
        class FastAPIApp {
            +create_app(job_queue?)
            +lifespan startup
            +app.state.job_queue
        }
    }

    AsyncioQueueTests --> AsyncioJobQueue : tests
    WorkerTests --> AsyncioJobQueue : tests lifecycle
    WorkerTests --> FastAPIApp : tests DI integration
    AsyncioJobQueue --> "JobStatus" : uses
```

## Notes

- All tests use `asyncio.create_task()` to run workers in background
- Worker cancellation tests verify clean exit via `asyncio.CancelledError`
- Timeout behavior tested with 0.05s custom timeout to avoid 300s waits
- DI pattern stores queue on `app.state.job_queue` for handler access
- Test doubles (_success_handler, _slow_handler, _failing_handler) isolate queue logic

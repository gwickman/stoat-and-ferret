# C4 Code Level: tests/test_jobs

## Overview

- **Name**: Job Queue Test Suite
- **Description**: Tests for AsyncioJobQueue and worker lifecycle integration with FastAPI
- **Location**: tests/test_jobs/
- **Language**: Python
- **Purpose**: Validate job submission, status tracking, completion, failure, timeout, cancellation, and progress tracking
- **Parent Component**: [Test Infrastructure](./c4-component-test-infrastructure.md)

## Code Elements

### Test Inventory

- **Total Tests**: 25 verified tests
- **Test Files**: 2 test files + 1 __init__.py

| File | Test Count | Description |
|------|-----------|-------------|
| test_asyncio_queue.py | 17 | Submit, status, completion, failure, timeout, cancellation, progress |
| test_worker.py | 8 | Worker lifecycle, lifespan integration |

### test_asyncio_queue.py (17 tests)

**Test Handlers**
- `_success_handler(job_type, payload)` → dict[str, str] (line 16)
  - Returns immediately with success
- `_slow_handler(job_type, payload)` → str (line 21)
  - Sleeps 10 seconds to trigger timeout
- `_failing_handler(job_type, payload)` → None (line 27)
  - Raises RuntimeError("something went wrong")

**Test Classes**
- TestSubmitAndStatus (5 tests) - submit returns unique IDs, initial PENDING status
  - test_submit_returns_job_id
  - test_submit_generates_unique_ids
  - test_initial_status_is_pending
  - test_get_status_unknown_job_raises
  - test_get_result_unknown_job_raises

- TestJobCompletion (2 tests) - worker processes jobs to COMPLETE status
  - test_job_completes_successfully
  - test_multiple_jobs_processed_in_order

- TestJobFailure (2 tests) - exceptions set FAILED status
  - test_handler_exception_sets_failed_status
  - test_no_handler_sets_failed_status

- TestJobTimeout (3 tests) - timeout behavior with custom/default values
  - test_timeout_sets_timeout_status
  - test_custom_timeout_is_used
  - test_default_timeout_is_300

- TestCancellation (5 tests) - cancel_event control and CANCELLED status
  - test_entry_initializes_with_unset_cancel_event
  - test_cancel_sets_cancel_event
  - test_cancel_unknown_job_raises
  - test_cancelled_job_has_cancelled_status
  - test_cancelled_status_serializes_correctly

- TestProgress (5 tests) - progress tracking and state preservation
  - test_entry_initializes_with_progress_none
  - test_set_progress_updates_entry
  - test_set_progress_unknown_job_is_noop
  - test_progress_preserved_after_completion

### test_worker.py (8 tests)

**Test Handlers**
- `_noop_handler(job_type, payload)` → str (line 17)
  - Minimal handler returning "ok"

**Test Classes**
- TestWorkerLifecycle (2 tests) - worker coroutine behavior
  - test_worker_cancels_cleanly
  - test_worker_processes_job_then_cancels

- TestLifespanIntegration (2 tests) - FastAPI integration
  - test_app_with_injected_job_queue
  - test_app_without_injection_works

## Dependencies

### Internal Dependencies
- stoat_ferret.jobs.queue.AsyncioJobQueue
- stoat_ferret.jobs.queue.JobStatus
- stoat_ferret.api.app.create_app

### External Dependencies
- pytest
- asyncio (Python standard library)

## Relationships

```mermaid
---
title: Job Queue Test Suite - Queue Operations and Lifecycle
---
classDiagram
    namespace Handlers {
        class SuccessHandler {
            <<function>>
            +returns result immediately
        }
        class SlowHandler {
            <<function>>
            +sleeps 10 seconds
        }
        class FailingHandler {
            <<function>>
            +raises RuntimeError
        }
    }

    namespace QueueTests {
        class TestSubmitAndStatus {
            +test_submit_returns_job_id()
            +test_submit_generates_unique_ids()
            +test_initial_status_is_pending()
            +test_get_status_unknown_job_raises()
            +test_get_result_unknown_job_raises()
        }
        class TestJobCompletion {
            +test_job_completes_successfully()
            +test_multiple_jobs_processed_in_order()
        }
        class TestJobFailure {
            +test_handler_exception_sets_failed_status()
            +test_no_handler_sets_failed_status()
        }
        class TestJobTimeout {
            +test_timeout_sets_timeout_status()
            +test_custom_timeout_is_used()
            +test_default_timeout_is_300()
        }
        class TestCancellation {
            +test_entry_initializes_with_unset_cancel_event()
            +test_cancel_sets_cancel_event()
            +test_cancel_unknown_job_raises()
            +test_cancelled_job_has_cancelled_status()
            +test_cancelled_status_serializes_correctly()
        }
        class TestProgress {
            +test_entry_initializes_with_progress_none()
            +test_set_progress_updates_entry()
            +test_set_progress_unknown_job_is_noop()
            +test_progress_preserved_after_completion()
        }
    }

    namespace WorkerTests {
        class TestWorkerLifecycle {
            +test_worker_cancels_cleanly()
            +test_worker_processes_job_then_cancels()
        }
        class TestLifespanIntegration {
            +test_app_with_injected_job_queue()
            +test_app_without_injection_works()
        }
    }

    namespace Core {
        class AsyncioJobQueue {
            -_jobs dict
            -_timeout float
            +submit(job_type, payload) job_id
            +get_status(job_id) JobStatus
            +get_result(job_id) JobResult
            +process_jobs() async
            +register_handler(job_type, fn)
            +cancel(job_id)
            +set_progress(job_id, value)
        }
        class JobStatus {
            <<enum>>
            PENDING
            COMPLETE
            FAILED
            TIMEOUT
            CANCELLED
        }
        class FastAPI {
            +create_app(job_queue?)
        }
    }

    TestSubmitAndStatus --> AsyncioJobQueue : tests
    TestJobCompletion --> AsyncioJobQueue : tests
    TestJobFailure --> AsyncioJobQueue : tests
    TestJobTimeout --> AsyncioJobQueue : tests
    TestCancellation --> AsyncioJobQueue : tests
    TestProgress --> AsyncioJobQueue : tests
    TestWorkerLifecycle --> AsyncioJobQueue : tests
    TestLifespanIntegration --> FastAPI : tests DI
    AsyncioJobQueue --> JobStatus : uses
    SuccessHandler -.-> AsyncioJobQueue : handler
    SlowHandler -.-> AsyncioJobQueue : handler
    FailingHandler -.-> AsyncioJobQueue : handler
```

## Notes

- All async tests use `asyncio.create_task()` to run workers in background
- Worker cancellation verified via `asyncio.CancelledError` exception handling
- Timeout tests use short custom timeouts (0.05s) to avoid long waits
- DI pattern stores queue on `app.state.job_queue` for handler access
- Test handlers isolated with minimal payloads for focused queue logic testing
- Cancellation tested via `cancel_event` cooperative control flow
- Progress tested for preservation after job completion

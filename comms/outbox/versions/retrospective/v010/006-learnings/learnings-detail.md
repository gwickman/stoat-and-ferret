# Learning Extraction Detail - v010

Full content of each learning saved during the v010 retrospective.

---

## LRN-053: Layered Defense-in-Depth for Critical Bug Fixes

**Tags:** process, bug-fixes, defense-in-depth, static-analysis, testing, decision-framework
**Source:** v010/01-async-pipeline-fix retrospective, v010 version retrospective

### Context

When fixing a critical bug (P0/P1), a single fix addresses the immediate symptom but leaves the codebase vulnerable to the same class of bug recurring. Bug-fix themes benefit from a structured three-layer approach.

### Learning

Apply a three-layer defense-in-depth pattern for critical bug fixes: (1) fix the immediate bug, (2) add static analysis rules to catch the same class of bug at CI time, (3) add a runtime regression test that detects the failure mode. This ensures the specific bug is fixed, similar bugs are caught before merge, and regressions are detected if the static analysis is insufficient.

### Evidence

v010 Theme 01 (async-pipeline-fix) applied this pattern successfully:
- Feature 001: Fixed the blocking `subprocess.run()` call by converting to `asyncio.create_subprocess_exec()`
- Feature 002: Enabled ruff ASYNC rules (ASYNC221/210/230) to catch blocking calls in async functions at CI time
- Feature 003: Added an integration test verifying event-loop responsiveness during scans

All three features shipped with all acceptance criteria met. The ruff rules would have caught the original bug before it reached production.

### Application

When designing a bug-fix theme for P0/P1 issues:
1. First feature: Fix the specific bug
2. Second feature: Add static analysis or linting rules that catch the same class of bug
3. Third feature: Add a runtime regression test that detects the failure mode under realistic conditions

This pattern is most valuable when the bug class is likely to recur (e.g., blocking calls in async code, security boundary violations, data consistency issues).

---

## LRN-054: Use new_callable=AsyncMock for Cleaner Async Test Mocking

**Tags:** testing, async, mocking, pytest, pattern
**Source:** v010/01-async-pipeline-fix/001-fix-blocking-ffprobe completion-report, v010/01-async-pipeline-fix retrospective

### Context

When testing async code that calls other async functions, the standard `unittest.mock.patch()` creates a regular `MagicMock` by default. This requires manually wrapping return values in coroutines or using `AsyncMock` directly, which is verbose and error-prone.

### Learning

Use `new_callable=AsyncMock` in `patch()` calls to automatically create an async-compatible mock. This is cleaner than manually wrapping return values in coroutines and ensures the mock behaves correctly as an awaitable in all cases, including when used as a context manager or iterable.

### Evidence

v010 Feature 001 (fix-blocking-ffprobe) converted `ffprobe_video()` to async and needed to update all test mocks. Using `new_callable=AsyncMock` in `patch()` calls was identified as cleaner than wrapping return values:

```python
# Clean approach (recommended)
with patch("module.ffprobe_video", new_callable=AsyncMock, return_value=metadata):
    result = await scan_directory(path)

# Verbose approach (avoid)
mock = MagicMock()
mock.return_value = asyncio.coroutine(lambda: metadata)()
```

The clean approach worked across all test files (test_videos.py, test_jobs.py, test_ffprobe.py) without issues.

### Application

When patching async functions in tests:
- Always use `new_callable=AsyncMock` in `patch()` calls
- Set `return_value` normally — `AsyncMock` handles the awaitable wrapping
- For `side_effect`, use an async function (`async def`) rather than a sync one
- This pattern works with both `patch()` as a decorator and as a context manager

---

## LRN-055: asyncio.to_thread() Bridges Legacy Sync Code in Async Contexts

**Tags:** pattern, async, asyncio, migration, subprocess
**Source:** v010/01-async-pipeline-fix/002-async-blocking-ci-gate completion-report, v010/01-async-pipeline-fix retrospective

### Context

When migrating a codebase from sync to async, some functions contain sync blocking calls (like `subprocess.run()`) that cannot be easily converted to fully async equivalents. This is common in utility functions, health checks, and third-party library calls.

### Learning

Use `asyncio.to_thread()` to wrap blocking synchronous calls in async contexts when a full async rewrite is impractical or unnecessary. This moves the blocking call to a thread pool, preventing event-loop starvation while maintaining the existing sync implementation. Reserve `asyncio.create_subprocess_exec()` for new code or high-frequency paths where the full async approach is warranted.

### Evidence

v010 Feature 002 (async-blocking-ci-gate) used `asyncio.to_thread()` to wrap the health check's `subprocess.run()` call rather than converting it to `asyncio.create_subprocess_exec()`. This was appropriate because:
- Health checks run infrequently (not a hot path)
- The existing sync implementation was well-tested
- The change was minimal and low-risk

Meanwhile, Feature 001 used `asyncio.create_subprocess_exec()` for `ffprobe_video()` because it runs per-file during scans (hot path).

### Application

When encountering blocking sync calls in async code:
- **High-frequency paths**: Convert to native async (`asyncio.create_subprocess_exec()`, `aiohttp`, etc.)
- **Low-frequency paths**: Wrap with `asyncio.to_thread()` for minimal-risk unblocking
- **Third-party sync libraries**: `asyncio.to_thread()` is the only practical option without replacing the library
- Note: `asyncio.to_thread()` is available from Python 3.9+

---

## LRN-056: Use Production Implementations in Integration Tests for Async Concurrency

**Tags:** testing, async, integration-tests, concurrency, test-doubles
**Source:** v010/01-async-pipeline-fix/003-event-loop-responsiveness-test completion-report, v010/01-async-pipeline-fix retrospective

### Context

Integration tests that verify concurrent async behavior need to exercise real async scheduling and task interleaving. Synchronous test doubles that execute operations immediately mask concurrency issues.

### Learning

Use production async implementations (not synchronous test doubles) in integration tests that verify concurrent behavior. Synchronous in-memory stubs execute handlers immediately at submit time, bypassing async task scheduling entirely, which defeats the purpose of testing async concurrency properties like event-loop responsiveness or task interleaving.

### Evidence

v010 Feature 003 (event-loop-responsiveness-test) used the production `AsyncioJobQueue` instead of `InMemoryJobQueue` for its integration test. The `InMemoryJobQueue` executes jobs synchronously at submit time, which would not exercise actual async concurrency. The production queue's async task scheduling was essential to verify that the event loop stayed responsive during a scan with simulated-slow processing.

### Application

When writing integration tests for async behavior:
- Use the production async queue/scheduler, not a synchronous test double
- Synchronous test doubles are appropriate for unit tests where you test handler logic in isolation
- Only integration tests that specifically verify concurrency properties need the production implementation
- Clearly mark these tests with appropriate markers (`@pytest.mark.integration`, `@pytest.mark.slow`)

---

## LRN-057: Cooperative Cancellation via asyncio.Event with Checkpoint Pattern

**Tags:** pattern, async, cancellation, asyncio, api-design
**Source:** v010/02-job-controls/002-job-cancellation completion-report, v010/02-job-controls retrospective

### Context

Long-running async operations (file scans, batch processing, data imports) need cancellation support. Thread interruption is unsafe, and `asyncio.Task.cancel()` can leave resources in inconsistent states. A cooperative approach is needed where the operation checks for cancellation at safe points.

### Learning

Use `asyncio.Event` as a cancellation signal combined with checkpoint checks at natural processing boundaries (e.g., after each file in a scan loop). The operation checks `event.is_set()` at each checkpoint and breaks cleanly, returning partial results. This is testable, Python 3.10-compatible, and avoids the complexity of forced task cancellation.

### Evidence

v010 Feature 002 (job-cancellation) implemented cooperative cancellation for directory scans:
- `cancel_event: asyncio.Event` added to job entries
- `AsyncioJobQueue.cancel()` sets the event
- `scan_directory()` checks `cancel_event.is_set()` after processing each file
- On cancellation, the scan breaks and returns partial results (files scanned so far)
- REST endpoint returns 200 (cancelled), 404 (unknown job), or 409 (already completed)

The pattern was clean to implement, easy to test (just set the event before calling the scan), and correctly preserved partial results.

### Application

When implementing cancellation for long-running async operations:
1. Add an `asyncio.Event` to the operation's context/entry
2. Check `event.is_set()` at natural processing boundaries (after each item, each batch, etc.)
3. On cancellation, break cleanly and return partial results rather than raising an exception
4. Expose cancellation via a state-transition API (check current state before allowing cancel)
5. Use 409 Conflict for cancel requests on already-completed operations

---

## LRN-058: Payload Injection Extends Handler Interfaces Without Signature Changes

**Tags:** pattern, backward-compatibility, api-design, dependency-injection, job-queue
**Source:** v010/02-job-controls/001-progress-reporting completion-report, v010/02-job-controls retrospective

### Context

Job queue systems often need to pass new contextual information (job ID, cancellation signals, progress callbacks) to handlers. Changing the handler function signature breaks all existing handlers and their tests.

### Learning

Inject contextual information into the handler's payload dictionary (e.g., `payload["_job_id"] = job_id`) rather than adding parameters to the handler function signature. This preserves backward compatibility with existing handlers while giving new handlers access to the context they need. Use underscore-prefixed keys to distinguish injected context from user-provided data.

### Evidence

v010 Feature 001 (progress-reporting) needed to give scan handlers access to their job ID for progress updates. Rather than changing the handler signature from `(job_type, payload)` to `(job_type, payload, job_id)`, the `process_jobs()` worker injected `_job_id` into the payload dict. This:
- Kept all existing handlers working without changes
- Avoided modifying the handler Protocol or type signature
- Let the scan handler access `payload["_job_id"]` for progress callbacks
- Maintained backward compatibility across all test fixtures and conftest wiring

### Application

When extending a callback/handler interface with new context:
- Inject into existing data structures (dicts, context objects) rather than adding function parameters
- Use underscore-prefixed or namespaced keys to avoid collisions with user data
- This approach works best when the interface is used by many callsites and backward compatibility matters
- For greenfield designs, explicit parameters are preferable for type safety

---

## LRN-059: Pre-Collect Items When Progress Reporting Needs a Known Total

**Tags:** pattern, progress-reporting, ux, iteration, api-design
**Source:** v010/02-job-controls/001-progress-reporting completion-report, v010/02-job-controls retrospective

### Context

Progress reporting requires knowing both the current position and the total count. Lazy iterators and generators process items one at a time without knowing the total upfront, making accurate percentage-based progress impossible.

### Learning

When adding progress reporting to an operation that uses lazy iteration, pre-collect items into a list first to determine the total count. The cost of collecting upfront (memory for the item list) is typically negligible compared to the per-item processing cost, and it enables accurate `processed / total` progress calculation.

### Evidence

v010 Feature 001 (progress-reporting) changed `scan_directory()` from lazy `root.glob()` iteration to pre-collecting video files into a list:
- Before: `for path in root.glob("**/*"):` — no total count available
- After: `video_files = [p for p in root.glob("**/*") if p.suffix in VIDEO_EXTENSIONS]` — total known
- Progress callback: `progress_callback(processed / len(video_files))`

The pre-collection cost was minimal (just path objects in memory) while enabling real-time 0.0-1.0 progress updates per file.

### Application

When adding progress reporting to existing iterative operations:
1. Collect the work items into a list/sequence before starting processing
2. Calculate progress as `completed_count / total_count`
3. This pattern is appropriate when the collection is much cheaper than per-item processing
4. For very large collections where memory is a concern, consider a two-pass approach: first count, then process

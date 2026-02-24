## Context

Long-running async operations (file scans, batch processing, data imports) need cancellation support. Thread interruption is unsafe, and `asyncio.Task.cancel()` can leave resources in inconsistent states. A cooperative approach is needed where the operation checks for cancellation at safe points.

## Learning

Use `asyncio.Event` as a cancellation signal combined with checkpoint checks at natural processing boundaries (e.g., after each file in a scan loop). The operation checks `event.is_set()` at each checkpoint and breaks cleanly, returning partial results. This is testable, Python 3.10-compatible, and avoids the complexity of forced task cancellation.

## Evidence

v010 Feature 002 (job-cancellation) implemented cooperative cancellation for directory scans:
- `cancel_event: asyncio.Event` added to job entries
- `AsyncioJobQueue.cancel()` sets the event
- `scan_directory()` checks `cancel_event.is_set()` after processing each file
- On cancellation, the scan breaks and returns partial results (files scanned so far)
- REST endpoint returns 200 (cancelled), 404 (unknown job), or 409 (already completed)

The pattern was clean to implement, easy to test (just set the event before calling the scan), and correctly preserved partial results.

## Application

When implementing cancellation for long-running async operations:
1. Add an `asyncio.Event` to the operation's context/entry
2. Check `event.is_set()` at natural processing boundaries (after each item, each batch, etc.)
3. On cancellation, break cleanly and return partial results rather than raising an exception
4. Expose cancellation via a state-transition API (check current state before allowing cancel)
5. Use 409 Conflict for cancel requests on already-completed operations
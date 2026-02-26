# Root Cause Analysis

## Primary Bug: Status String Mismatch

The backend and frontend use different strings for the "job complete" status.

### Backend — `src/stoat_ferret/jobs/queue.py:22`

```python
class JobStatus(enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETE = "complete"       # ← serialized as "complete"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
```

Serialized at `src/stoat_ferret/api/routers/jobs.py:41`:

```python
return JobStatusResponse(
    ...
    status=result.status.value,   # ← sends "complete"
    ...
)
```

### Frontend — `gui/src/components/ScanModal.tsx:12-18`

```typescript
interface JobStatus {
  job_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  //                               ^^^^^^^^^^
  //                               expects "completed" — wrong!
  progress: number | null
  result: Record<string, unknown> | null
  error: string | null
}
```

The polling check at `ScanModal.tsx:98`:

```typescript
if (status.status === 'completed') {   // never matches "complete"
  cleanup()
  setScanStatus('complete')
  onScanComplete()
}
```

### Why This Causes a Freeze

1. Scan runs normally, progress updates from 0% → 100%
2. Backend sets job status to `JobStatus.COMPLETE` (serialized as `"complete"`)
3. Frontend polls and receives `{ status: "complete", progress: 1.0, result: {...} }`
4. Comparison `"complete" === "completed"` evaluates to `false`
5. None of the `if/else if` branches match — polling continues forever
6. Dialog stays in `scanning` state showing 100% with no completion message

### Fix

In `gui/src/components/ScanModal.tsx`:

```typescript
// Line 14: Fix the interface type
interface JobStatus {
  job_id: string
  status: 'pending' | 'running' | 'complete' | 'failed' | 'cancelled' | 'timeout'
  progress: number | null
  result: Record<string, unknown> | null
  error: string | null
}

// Line 98: Already correct — checks for 'complete' which now matches
if (status.status === 'complete') {     // was 'completed'
  cleanup()
  setScanStatus('complete')
  onScanComplete()
} else if (status.status === 'cancelled') {
  cleanup()
  setScanStatus('cancelled')
} else if (status.status === 'failed' || status.status === 'timeout') {
  cleanup()
  setScanStatus('error')
  setErrorMessage(status.error ?? 'Scan failed')
}
```

## Secondary Bug: Timeout Status Not Handled

The backend can return `"timeout"` status when a scan exceeds 300 seconds (`AsyncioJobQueue.DEFAULT_TIMEOUT`), but the frontend has no handler for it. The polling loop ignores the `"timeout"` status entirely, causing the same infinite-polling freeze.

The fix above adds `status.status === 'timeout'` to the `'failed'` branch.

## How This Bug Was Introduced

The `JobStatus` TypeScript interface was written with `'completed'` (past participle, REST convention) but the backend Python enum uses `'complete'` (adjective). This mismatch has existed since the scan polling was implemented in the v010 cycle. The `'timeout'` value was also omitted from the interface entirely.

The previous `scan-directory-stuck` exploration (commit `82d99b0`) identified the blocking subprocess and missing progress as the primary issues, which masked this status mismatch — the dialog was already frozen before reaching 100% due to the event loop being blocked. After those fixes were applied in commits `32859cc` and `81984e4`, the status mismatch became the remaining blocker.

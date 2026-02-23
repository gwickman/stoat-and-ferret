# Frontend Issues

## Issue 1: Progress Bar Always at 0% (Confirmed Bug)

**File:** `gui/src/components/ScanModal.tsx:78`

```tsx
setProgress(status.progress)
```

The frontend correctly reads `status.progress` from the polling response, but the backend never populates it (see backend-issues.md Issue 2). The value is always `null`.

**File:** `gui/src/components/ScanModal.tsx:155-159`

```tsx
<div className="h-2 overflow-hidden rounded bg-gray-800">
  <div
    className="h-full bg-blue-500 transition-all"
    style={{ width: `${(progress ?? 0) * 100}%` }}
  />
</div>
```

When `progress` is `null`, the nullish coalescing `?? 0` sets width to `0%`. The progress bar never moves.

**Impact:** User sees a permanently empty progress bar during the entire scan.

**Fix:** This is primarily a backend issue (progress needs to be populated). On the frontend side, consider showing an indeterminate/pulsing progress bar when `progress` is `null` but scan status is `scanning`, to indicate activity even without precise percentage:

```tsx
style={{
  width: progress !== null ? `${progress * 100}%` : '100%',
  animation: progress === null ? 'pulse 1.5s infinite' : 'none',
}}
```

## Issue 2: Cancel Button Disabled During Scan (Confirmed Bug)

**File:** `gui/src/components/ScanModal.tsx:183-191`

```tsx
<button
  type="button"
  onClick={onClose}
  disabled={scanStatus === 'scanning'}
  className="... disabled:opacity-50"
  data-testid="scan-cancel"
>
  {scanStatus === 'complete' ? 'Close' : 'Cancel'}
</button>
```

The cancel button is **disabled** (`disabled={scanStatus === 'scanning'}`) while a scan is in progress — exactly when the user would want to cancel. It only calls `onClose()` to dismiss the modal, with no backend cancel request.

**Impact:** User cannot cancel a running scan. The button is greyed out and unclickable during scanning.

**Fix:** Two changes needed:
1. Remove or change the `disabled` condition so the button is clickable during scanning
2. When clicked during a scan, send a cancel request to the backend (requires backend cancel endpoint) and then call `cleanup()` to stop polling

```tsx
async function handleCancel() {
  if (scanStatus === 'scanning' && currentJobId) {
    await fetch(`/api/v1/jobs/${currentJobId}/cancel`, { method: 'POST' })
    cleanup()
    setScanStatus('idle')
  }
  onClose()
}
```

## Issue 3: Timeout Status Not Handled (Confirmed Bug)

**File:** `gui/src/components/ScanModal.tsx:80-88`

```tsx
if (status.status === 'completed') {
  cleanup()
  setScanStatus('complete')
  onScanComplete()
} else if (status.status === 'failed') {
  cleanup()
  setScanStatus('error')
  setErrorMessage(status.error ?? 'Scan failed')
}
```

The polling handler only checks for `completed` and `failed`. The backend can also return `timeout` status (from `src/stoat_ferret/jobs/queue.py:407`), but the frontend ignores it.

**Impact:** If a scan job times out (exceeds 300s), the frontend continues polling indefinitely. The progress bar stays at 0%, the scan status stays `scanning`, and the modal cannot be closed (cancel button is disabled).

**Fix:** Add a handler for `timeout` status:

```tsx
} else if (status.status === 'timeout') {
  cleanup()
  setScanStatus('error')
  setErrorMessage(status.error ?? 'Scan timed out')
}
```

## Issue 4: Status Enum Mismatch (Suspected Issue)

**File:** `gui/src/components/ScanModal.tsx:13`

Frontend expects: `'pending' | 'running' | 'completed' | 'failed'`

**File:** `src/stoat_ferret/jobs/queue.py:17-24`

Backend sends: `'pending' | 'running' | 'complete' | 'failed' | 'timeout'`

Note: The frontend checks for `'completed'` (with 'd') but the backend sends `'complete'` (without 'd'). This means the `status.status === 'completed'` check on line 80 would **never match**.

**Impact:** If this mismatch exists, the frontend would never detect scan completion, resulting in infinite polling even after successful scans. **This needs verification** — the test suite may use mocked responses that mask this mismatch.

**Verification needed:** Check the actual HTTP response to confirm whether `status` is `"complete"` or `"completed"`. The `JobStatus.COMPLETE` enum value is `"complete"` (line 22 of queue.py), and `JobStatusResponse.status` is a plain `str` (line 27 of schemas/job.py), so the backend sends `"complete"`.

**Fix if confirmed:** Change the frontend check to match the backend value:

```tsx
if (status.status === 'complete') {    // was 'completed'
```

## Issue 5: No Polling Timeout / Safety Limit (Design Gap)

**File:** `gui/src/components/ScanModal.tsx:72-92`

The polling `setInterval` runs indefinitely with no maximum duration or retry limit. If the backend job disappears (e.g., server restart clearing the in-memory queue), the 404 response is swallowed by the catch block (line 89-91) and polling continues forever.

**Impact:** In edge cases (server restart, memory pressure clearing jobs), the frontend can poll forever with no user feedback.

**Fix:** Add a maximum poll count or timeout, and transition to an error state if exceeded:

```tsx
let pollCount = 0
pollRef.current = setInterval(async () => {
  if (++pollCount > 600) { // 10 min max
    cleanup()
    setScanStatus('error')
    setErrorMessage('Scan timed out waiting for response')
    return
  }
  // ... existing poll logic
}, 1000)
```

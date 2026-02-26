# Scan Directory Freeze - Investigation Results

The scan dialog freezes at 100% because of a **status string mismatch** between backend and frontend. The backend job queue serializes the completion status as `"complete"` (`JobStatus.COMPLETE = "complete"` in `queue.py:22`), but the frontend polling loop checks for `"completed"` (`ScanModal.tsx:98`). Since `"complete" !== "completed"`, the completion branch never fires — the dialog stays in `scanning` state with 100% progress forever.

A secondary issue: the frontend still does not handle the `"timeout"` status from the backend, so jobs that exceed the 300-second timeout also leave the dialog frozen.

## Findings

- [root-cause-analysis.md](./root-cause-analysis.md) — The status string mismatch bug with code snippets and fix
- [backend-scan-flow.md](./backend-scan-flow.md) — Full backend endpoint trace from request to database write
- [frontend-scan-dialog.md](./frontend-scan-dialog.md) — Frontend dialog component analysis and state management
- [recent-changes.md](./recent-changes.md) — Git history of scan-related changes and regression analysis

## Fix Summary

Two changes needed:

1. **ScanModal.tsx:14** — Change `'completed'` to `'complete'` in the `JobStatus` interface type, and update the check at line 98
2. **ScanModal.tsx:105-108** — Add handling for `'timeout'` status (treat it like `'failed'`)

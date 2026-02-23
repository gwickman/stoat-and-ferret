Investigate the Scan Directory feature to understand why it appears to hang indefinitely when a user adds a folder.

Reported symptoms:
1. Progress bar never moves after initiating a scan
2. Backend console shows the job processing forever (never completes)
3. Cancel button does nothing

## Investigation Areas

1. **Backend scan endpoint**: Find the API endpoint(s) that handle directory scanning. Trace the full request lifecycle - what happens when a scan is initiated? Is there a background task/job queue involved?
2. **Progress reporting mechanism**: How does the backend communicate scan progress to the frontend? Is it polling, SSE, websockets? Is the progress calculation correct or could it be stuck at 0%?
3. **Job completion logic**: What conditions must be met for a scan job to complete? Are there error paths that could cause it to loop or hang? Check for missing break conditions, uncaught exceptions, or infinite loops.
4. **Cancel mechanism**: How is cancellation implemented? Does the cancel button send a request to the backend? Does the backend check for cancellation flags during processing? Is there a race condition?
5. **Frontend state management**: How does the frontend track scan state? Could there be a state update issue preventing the progress bar from reflecting actual progress?
6. **File processing**: What happens for each file during scanning? Are there file types or directory structures that could cause issues (symlinks, very large files, permission errors)?

## Output Requirements

Create findings in comms/outbox/exploration/scan-directory-stuck/:

### README.md (required)
First paragraph: Concise summary of root cause(s) found.
Then: Overview of the scan directory architecture and identified issues.

### scan-flow-analysis.md
End-to-end trace of the scan directory flow from button click to completion, identifying where it breaks down.

### backend-issues.md
Backend-specific issues found: endpoint logic, job processing, error handling gaps.

### frontend-issues.md
Frontend-specific issues: progress bar updates, cancel button wiring, state management problems.

## Guidelines
- Keep each document under 200 lines
- Include relevant code snippets showing the problematic areas
- Reference exact file paths and line numbers
- Distinguish between confirmed bugs and suspected issues

## When Complete
git add comms/outbox/exploration/scan-directory-stuck/
git commit -m "exploration: scan-directory-stuck complete"

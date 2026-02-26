Investigate the directory scan feature in the stoat-and-ferret GUI and backend to understand why scanning a directory reaches 100% progress but then the dialog freezes and no videos are imported into the library.

Specific questions to answer:

1. **Backend scan endpoint**: Find the API endpoint that handles directory scanning. Trace the full request/response flow. Does it return a proper completion response? Are there error handling gaps where exceptions might be swallowed silently?

2. **Frontend scan dialog**: Find the React/Svelte component handling the scan dialog. How does it determine when scanning is complete? What triggers the dialog to close and the video library to refresh? Is there a missing state transition or callback after progress hits 100%?

3. **Progress tracking mechanism**: How is scan progress communicated (SSE, polling, websocket)? Is there a race condition or disconnect between the progress reaching 100% and the final "scan complete" signal?

4. **Data flow**: Trace what happens to discovered video files. Are they being written to the database? Is the library view querying correctly after scan completes?

5. **Recent changes**: Check git log for recent changes to scan-related code, particularly from v012 execution. Did any refactoring break the scan completion flow?

6. **Logs and error handling**: Look for any try/except blocks that might be swallowing errors, missing await calls on async operations, or response format mismatches between backend and frontend.

## Output Requirements

Create findings in comms/outbox/exploration/scan-directory-freeze/:

### README.md (required)
First paragraph: Concise diagnosis of the root cause (or top candidates if ambiguous).
Then: Overview of findings with links to detailed documents.

### backend-scan-flow.md
Full trace of the backend scan endpoint, including request handling, file discovery, database writes, and response format.

### frontend-scan-dialog.md
Analysis of the frontend scan dialog component, state management, progress tracking, and completion handling.

### root-cause-analysis.md
Specific identification of the bug(s) causing the freeze. Include code snippets showing the problematic code and what the fix should look like.

### recent-changes.md
Git log analysis of recent changes to scan-related files, identifying any commits that may have introduced the regression.

## Guidelines
- Keep each document under 200 lines
- Include relevant code snippets with file paths
- Focus on the specific bug, not general architecture review
- If you find the root cause, be explicit about what's broken and how to fix it

## When Complete
git add comms/outbox/exploration/scan-directory-freeze/
git commit -m "exploration: scan-directory-freeze complete"

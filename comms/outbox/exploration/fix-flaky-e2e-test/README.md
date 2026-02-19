# Fix Flaky E2E Test: project-creation.spec.ts

The `toBeHidden` assertion on the project creation modal (line 31) was flaky because it raced against the backend API call. The modal only closes after the POST to `/api/v1/projects` completes, but the assertion used Playwright's default 5s timeout with no awareness of network timing. In CI (GitHub Actions), variable backend latency could push the response past that window. The fix adds `page.waitForResponse()` to synchronize on the POST completing before asserting the modal is gone.

## What Changed

In `gui/e2e/project-creation.spec.ts`, the "Submit" section now sets up a response waiter **before** clicking the Create button, then awaits that response before checking `toBeHidden()`. This decouples the assertion from any fixed timeout by waiting for the actual event that triggers the modal close.

## Why This Works

- `waitForResponse` returns as soon as the POST response arrives, regardless of how long it takes
- The modal's `handleSubmit` calls `onClose()` synchronously after the API resolves, so the DOM update follows within milliseconds of the response
- The `toBeHidden()` assertion can then use the default timeout safely since React removes the element almost immediately
- No excessive timeouts are needed; the test is deterministic with respect to backend latency

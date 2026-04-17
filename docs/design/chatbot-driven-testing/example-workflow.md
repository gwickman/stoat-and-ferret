# Example Workflow - Chatbot-Driven End-to-End Test

## Summary

This example shows how a local chatbot operator could test Stoat and Ferret without a custom MCP server. The chatbot uses the existing API and WebSocket surfaces, with optional browser validation at the end.

This is an example of a realistic internal testing session, not a productized end-user flow.

## Scenario

Goal:

- verify that Stoat and Ferret can ingest media, build a simple project, preview it, render it, and expose enough state for a chatbot to summarize the outcome

Assumptions:

- backend is running locally
- frontend is available under `/gui`
- FFmpeg is installed
- sample media exists in a known folder

## High-Level Steps

### 1. Preflight

The chatbot begins by checking:

- `GET /health/live`
- `GET /health/ready`
- available render encoders and formats
- whether a sample project already exists

Expected result:

- system is healthy
- required subsystems are available
- no obvious blockers before mutation begins

### 2. Scan Source Media

The chatbot submits a scan request for a test media directory, then monitors job progress.

Likely flow:

- `POST /api/v1/videos/scan`
- `GET /api/v1/jobs/{job_id}` or WebSocket monitoring
- `GET /api/v1/videos`

Expected result:

- videos appear in library
- metadata is available
- thumbnails or proxy generation may begin

### 3. Create a Project

The chatbot creates a new project with standard output settings and selects a few source videos.

Likely flow:

- `POST /api/v1/projects`
- `POST /api/v1/projects/{id}/clips`
- `GET /api/v1/projects/{id}/clips`

Expected result:

- project exists
- clips are attached in the intended order

### 4. Discover and Apply Effects

The chatbot queries effect discovery and chooses one or two simple effects that are easy to validate, such as:

- text overlay
- fade
- speed change

Likely flow:

- `GET /api/v1/effects`
- `POST /api/v1/effects/preview`
- `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects`

Expected result:

- chatbot can explain which effect it chose and why
- filter preview strings match the requested operation
- effect application succeeds with valid parameters

### 5. Preview the Project

The chatbot starts a preview session and watches for readiness and progress.

Likely flow:

- `POST /api/v1/projects/{id}/preview/start`
- `GET /api/v1/projects/{id}/preview/status` or WebSocket monitoring
- optional thumbnail strip and waveform fetches

Expected result:

- preview reaches ready state
- manifest/segment URLs are available
- player-visible state is consistent with backend state

### 6. Optional GUI Validation

The chatbot opens the GUI and verifies that the frontend reflects the same state:

- project visible
- preview page available
- Theater Mode can show current progress
- render page is reachable

This step is optional and should be used for:

- end-to-end confidence
- visual verification
- regression detection on user-facing surfaces

### 7. Start a Render

The chatbot submits a render with known-good settings and monitors progress.

Likely flow:

- `POST /api/v1/render/preview` to inspect generated command
- `POST /api/v1/render`
- WebSocket monitoring of queue and progress
- `GET /api/v1/render/{job_id}` or render list endpoints

Expected result:

- job enters queue
- job transitions to running
- progress/ETA events arrive
- job reaches completed or failed terminal state

### 8. Validate Output

If render succeeds, the chatbot verifies:

- output file exists
- output is non-empty
- format/container matches expectation

If render fails, the chatbot verifies:

- failure is visible through API/UI
- error message is captured
- retry path works if appropriate

### 9. Summarize

The chatbot produces a test summary:

- what it attempted
- which endpoints and surfaces were exercised
- whether preview and render completed
- any failures or degraded behavior
- recommended next debugging step

## Why This Workflow Fits The Current Architecture

This workflow works because Stoat and Ferret already provides:

- structured API mutation points
- discovery endpoints
- progress/event channels
- observable GUI surfaces
- render and preview infrastructure

The chatbot does not need a custom tool server to execute this scenario. It needs only:

- access to the local app
- a stable workflow reference
- enough reliability in the event and persistence layers

## What Would Make This Easier

Three small additions would improve this workflow significantly without adding MCP:

1. An agent operator guide listing canonical call sequences.
2. A helper script for "wait until preview/render completes."
3. A compact event reference for WebSocket payloads and terminal states.

## Bottom Line

This example shows that chatbot-driven testing is already a natural extension of the current architecture. The remaining work is mainly about making the workflow more reliable and easier to repeat, not about inventing a new integration model.

# Requirements — async-scan-endpoint

## Goal

Refactor scan endpoint to return job ID immediately, add GET /jobs/{id} status endpoint.

## Background

`POST /videos/scan` currently blocks until scan completes, returning `ScanResponse` directly. This is an API breaking change, but R1 investigation confirmed no external consumers beyond the test suite. The endpoint returns a job ID and callers poll `GET /jobs/{id}` for status. Depends on job-queue-infrastructure (BL-027 part 1).

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|---------|
| FR-1 | `POST /videos/scan` returns `{"job_id": "..."}` instead of blocking ScanResponse | BL-027 |
| FR-2 | `GET /jobs/{id}` returns job status, progress, and result when complete | BL-027 |
| FR-3 | Job failure returns error status with descriptive message | BL-027 |
| FR-4 | Scan operation runs as a job in the AsyncJobQueue | BL-027 |
| FR-5 | Existing scan tests updated to use async pattern (submit + poll) | BL-027 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | `POST /videos/scan` returns immediately (< 100ms response time) |
| NFR-2 | Job ID is a UUID string |
| NFR-3 | `GET /jobs/{id}` returns 404 for unknown job IDs |

## Out of Scope

- WebSocket-based progress streaming — polling is sufficient
- Scan cancellation — not required for initial implementation
- Batch job submission — single job per request

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Integration | POST /videos/scan returns job ID (not ScanResponse) | 1–2 |
| Integration | GET /jobs/{id} returns status, progress, and result when complete | 2–3 |
| Integration | Job failure returns error status with message | 1–2 |
| Black box | Full async workflow: scan → poll → complete | 2–3 |
| Regression | Existing scan tests updated to async pattern | (modified) |

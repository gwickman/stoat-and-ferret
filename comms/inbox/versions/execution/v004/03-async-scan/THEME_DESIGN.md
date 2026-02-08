# THEME DESIGN — 03: Async Scan Infrastructure

## Goal

Replace synchronous blocking scan with async job queue pattern, enabling progress tracking and non-blocking API behavior.

## Design Artifacts

- Refined logical design: `comms/outbox/versions/design/v004/006-critical-thinking/refined-logical-design.md` (Theme 03 section)
- Codebase patterns: `comms/outbox/versions/design/v004/004-research/codebase-patterns.md` (Scan Service section)
- External research: `comms/outbox/versions/design/v004/004-research/external-research.md` (§5 Async Job Queue Patterns)
- Test strategy: `comms/outbox/versions/design/v004/005-logical-design/test-strategy.md` (Theme 03 section)
- Risk assessment: `comms/outbox/versions/design/v004/006-critical-thinking/risk-assessment.md` (R1, U1)

## Features

| # | Feature | Backlog | Dependencies |
|---|---------|---------|-------------|
| 1 | job-queue-infrastructure | BL-027 (part 1) | Theme 01 feature 1 (InMemoryJobQueue) |
| 2 | async-scan-endpoint | BL-027 (part 2) | Feature 1 |
| 3 | scan-doc-updates | BL-027 (part 3) | Feature 2 |

## Dependencies

- **Upstream**: Theme 01 feature 1 (InMemoryJobQueue created in BL-020).
- **Internal**: Strict sequential chain — each feature depends on the previous.
- **External**: None.

## Technical Approach

1. **Job queue infrastructure** (BL-027 part 1): Create `AsyncJobQueue` protocol with `submit()`, `get_status()`, `get_result()`. Implement `AsyncioJobQueue` using `asyncio.Queue` producer-consumer pattern. Integrate with FastAPI lifespan context manager (start worker on startup, cancel on shutdown).
2. **Async scan endpoint** (BL-027 part 2): Refactor `POST /videos/scan` to return `{\"job_id\": \"...\"}` instead of `ScanResponse`. Add `GET /jobs/{id}` endpoint for status polling. Migrate existing scan tests to async pattern.
3. **Scan doc updates** (BL-027 part 3): Update `05-api-specification.md`, `03-prototype-design.md`, `02-architecture.md`, and `04-technical-stack.md` to document async scan behavior.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| R1: Scan API breaking change | Low (resolved) | No external consumers — only test migration needed |
| U1: Job queue timeout values | TBD | Default 5-minute timeout, configurable per job; tune at runtime |
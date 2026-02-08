# Implementation Plan — scan-doc-updates

## Overview

Update design documents to reflect the async scan endpoint and job queue pattern.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|--------|
| Modify | `docs/design/05-api-specification.md` | New scan contract, add GET /jobs/{id} |
| Modify | `docs/design/03-prototype-design.md` | Async scan flow description |
| Modify | `docs/design/02-architecture.md` | Add job queue component |
| Modify | `docs/design/04-technical-stack.md` | Add asyncio.Queue to dependencies |

## Implementation Stages

### Stage 1: API Specification Update
Update `05-api-specification.md`:
- Change `POST /videos/scan` response from `ScanResponse` to `JobSubmitResponse`
- Add `GET /jobs/{id}` endpoint with `JobStatusResponse` schema
- Include request/response examples

### Stage 2: Architecture Update
Update `02-architecture.md`:
- Add job queue as a component in the system diagram
- Describe producer-consumer pattern
- Document lifespan integration

### Stage 3: Prototype and Tech Stack Updates
Update `03-prototype-design.md` with async scan workflow description. Update `04-technical-stack.md` to list `asyncio.Queue` as an internal dependency.

## Quality Gates

- All 4 design documents updated
- No placeholder text
- API examples match actual implementation
- `uv run ruff check src/ tests/` passes (no code changes, but verify)

## Risks

| Risk | Mitigation |
|------|------------|
| Documentation drifts from implementation | Update docs immediately after implementation, in same PR cycle |

## Commit Message

```
docs: update design docs for async scan and job queue pattern
```
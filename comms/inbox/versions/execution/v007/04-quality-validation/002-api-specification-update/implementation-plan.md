# Implementation Plan: api-specification-update

## Overview

Update API specification documentation and related design docs with all new endpoints from v007: transition, preview, effect CRUD. Update roadmap milestones and GUI architecture docs. Document SPA fallback as known limitation.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `docs/design/05-api-specification.md` | Add transition, preview, CRUD endpoint documentation |
| Modify | `docs/design/01-roadmap.md` | Mark M2.4-2.6, M2.8-2.9 milestones complete |
| Modify | `docs/design/08-gui-architecture.md` | Add effect workshop components and routes |

## Test Files

(none — documentation feature)

## Implementation Stages

### Stage 1: Update API specification

1. Document POST /effects/transition with full request/response schemas
2. Document effect preview endpoint
3. Document PATCH /projects/{id}/clips/{id}/effects/{index} (update)
4. Document DELETE /projects/{id}/clips/{id}/effects/{index} (remove)
5. Update GET /effects response with new effect types
6. Add "Known Limitations" section documenting SPA fallback absence

**Verification:**
```bash
# Manual review for completeness and accuracy
```

### Stage 2: Update roadmap and GUI architecture

1. Update `01-roadmap.md`: mark milestones M2.4, M2.5, M2.6, M2.8, M2.9 complete
2. Update `08-gui-architecture.md`: add effect workshop components, stores, routes
3. Document /gui/effects route and SPA fallback workaround

**Verification:**
```bash
# Manual review
```

## Test Infrastructure Updates

None.

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Documentation may not capture edge cases from implementation. See `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`

## Commit Message

```
docs: update API specification, roadmap, and GUI architecture for v007
```
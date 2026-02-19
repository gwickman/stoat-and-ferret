# Requirements: api-specification-update

## Goal

Update OpenAPI spec and docs/design/05-api-specification.md with transition, preview, and CRUD endpoints.

## Background

This is a documentation feature consolidating all API endpoint additions from T02 and T03. Placing docs in T04 ensures they capture the final API surface after all endpoint implementations are complete. Also updates roadmap milestones and GUI architecture docs.

## Functional Requirements

**FR-001**: Update docs/design/05-api-specification.md with new endpoints
- AC: POST /effects/transition endpoint documented with request/response schemas
- AC: Effect preview endpoint documented
- AC: PATCH /projects/{id}/clips/{id}/effects/{index} documented
- AC: DELETE /projects/{id}/clips/{id}/effects/{index} documented
- AC: GET /effects response updated with new effect types

**FR-002**: Update docs/design/01-roadmap.md milestone checkboxes
- AC: M2.4 (audio mixing), M2.5 (transitions), M2.6 (registry), M2.8 (catalog/forms/preview), M2.9 (workflow) marked complete

**FR-003**: Update docs/design/08-gui-architecture.md
- AC: Effect workshop components documented in GUI architecture
- AC: New routes documented

**FR-004**: Document SPA fallback as known limitation
- AC: Known limitation section notes that direct URL access to /gui/effects returns 404
- AC: Workaround (client-side navigation) documented

## Non-Functional Requirements

**NFR-001**: Documentation matches actual implementation
- Metric: All documented endpoints match implemented code

## Out of Scope

- Auto-generating OpenAPI spec from code (manual update)
- API versioning strategy

## Test Requirements

No tests — documentation feature.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `impact-analysis.md`: Documentation impacts consolidated
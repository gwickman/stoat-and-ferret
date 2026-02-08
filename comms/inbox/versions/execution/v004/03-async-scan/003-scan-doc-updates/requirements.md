# Requirements — scan-doc-updates

## Goal

Update API spec and design docs for async scan pattern.

## Background

The scan endpoint contract changed from synchronous `ScanResponse` to async `JobSubmitResponse` + polling. Design documents in `docs/design/` reference the old synchronous behavior. Documentation updates are separated into their own feature to keep the implementation focused in BL-027 part 2.

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|--------|
| FR-1 | `docs/design/05-api-specification.md` updated with new scan endpoint contract and jobs endpoint | BL-027 |
| FR-2 | `docs/design/03-prototype-design.md` updated to reflect async scan behavior | BL-027 |
| FR-3 | `docs/design/02-architecture.md` updated with job queue component | BL-027 |
| FR-4 | `docs/design/04-technical-stack.md` updated with asyncio.Queue dependency | BL-027 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Documentation accurately reflects the implemented async behavior |
| NFR-2 | API specification includes request/response examples |

## Out of Scope

- Creating new design documents — only updating existing ones
- GUI documentation updates — that's v005
- OpenAPI schema generation — manual doc updates only

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| (none) | Documentation-only feature — no new tests | 0 |
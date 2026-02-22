# 006 Critical Thinking — v009

All 7 risks from Task 005 were investigated. 5 required codebase or external research, 2 were accepted with mitigation. Three investigations produced design-changing findings: (1) SPA catch-all route conflicts with StaticFiles mount — resolved by replacing the mount with a dual-purpose route handler, (2) AuditLogger needs a separate sync connection because aiosqlite has no public API for its underlying sync connection, (3) Projects page has no pagination UI, requiring scope increase for BL-064.

## Risks Investigated

- **Total risks:** 7
- **Investigated now:** 5 (SPA routing, AuditLogger connection, WebSocket broadcasts, test double injection, frontend pagination)
- **Accepted with mitigation:** 2 (lifespan complexity, log settings)
- **TBD/runtime:** 0

## Resolutions

1. **SPA routing (medium):** StaticFiles mount replaced by catch-all route that serves real files or index.html. Confirmed via Starlette routing semantics — routes and mounts cannot coexist with fallthrough at the same path.
2. **AuditLogger (medium):** Separate sync `sqlite3.Connection` created in lifespan. Brief event loop blocking acceptable for single INSERT per mutation.
3. **WebSocket broadcasts (medium):** Scan events fire from job handler (not router), reducing cross-cutting modifications from 2 routers to 1 router + scan service.

## Design Changes

- **Feature 001-spa-routing:** Implementation changed from "add catch-all alongside StaticFiles" to "replace StaticFiles with dual-purpose route handler"
- **Feature 002-audit-logging:** Added separate sync connection creation in lifespan
- **Feature 002-pagination-fix:** Scope increased from Low to Medium — frontend pagination UI required to meet AC3
- **Feature 003-websocket-broadcasts:** Scan broadcast points moved from videos router to scan job handler

## Remaining TBDs

- **HEALTH_STATUS broadcast trigger:** No clear operation point identified. May be deferred within Feature 003 if no natural trigger exists during implementation.

## Confidence Assessment

**High confidence.** All medium-severity risks have been resolved with concrete implementation strategies backed by codebase evidence and external documentation. The design changes are incremental refinements, not structural overhauls. The scope increase for BL-064 follows an existing proven pattern (Library page pagination). No blocking unknowns remain.

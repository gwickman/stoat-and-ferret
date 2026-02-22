# 003 Impact Assessment — v009

Impact assessment identified 10 impacts across 6 backlog items: 8 small (sub-task scope) and 2 substantial (feature scope). No cross-version impacts. The substantial impacts both relate to BL-060 (AuditLogger) and concern caller-adoption gaps that must be addressed during implementation to avoid the LRN-079 dead-code pattern.

## Generic Impacts

- **Documentation**: 4 impacts across 2 design documents
  - `docs/design/08-gui-architecture.md`: 1 known-limitation paragraph to remove (BL-063)
  - `docs/design/05-api-specification.md`: 3 sections to update — SPA fallback known limitation removal, GUI static files description correction, and projects pagination response example (BL-063, BL-064)
- **Configuration**: 1 impact — `.gitignore` needs `logs/` directory entry (BL-057)

## Project-Specific Impacts

N/A — no `IMPACT_ASSESSMENT.md` configured for this project.

## Caller-Impact Findings

5 caller-adoption risks identified:

| Item | Risk | Classification |
|------|------|----------------|
| BL-060 | AsyncProjectRepository lacks audit_logger parameter — project mutations won't produce audit entries | substantial |
| BL-060 | Route handler dependency functions don't pass audit_logger to repository constructors — LRN-079 pattern | substantial |
| BL-060 | app.py:78 creates AsyncSQLiteVideoRepository without audit_logger | small |
| BL-064 | Existing pagination tests assert buggy total count — will break on fix | small |
| BL-065 | make_scan_handler factory lacks ws_manager parameter for broadcasts | small |

## Work Items Generated

- **Small (8)**: Sub-tasks within existing features — documentation updates, .gitignore entry, test assertion fixes, caller wiring
- **Substantial (2)**: Both within BL-060 scope — AsyncProjectRepository audit_logger support and route handler factory wiring
- **Cross-version (0)**: No impacts deferred

## Recommendations

1. **BL-060 implementation plan must explicitly include** extending `AsyncProjectRepository` (protocol + both implementations) with `audit_logger` parameter and wiring all repository factory functions. Without this, AuditLogger will be dead code for project operations.

2. **BL-063 doc updates** (impacts #1-3) should be handled as a final sub-task after the SPA fallback implementation is verified working. All three are in design docs and describe the same limitation being fixed.

3. **BL-064 test updates** (impact #9) should be handled alongside the pagination fix itself — the test changes validate the fix is working correctly.

4. **BL-065 scan handler refactoring** (impact #8) — the `make_scan_handler` factory function signature needs ws_manager. This should be designed during theme implementation to avoid breaking the existing scan flow.

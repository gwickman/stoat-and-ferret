# 005 Architecture Alignment: v011

Minor drift detected. C4 documentation was regenerated for v011 via delta mode, and code-level documentation is accurate. However, higher-level summary counts and name lists at the component and container levels were not updated to reflect new GUI components and stores added in v011.

## Existing Open Items

- **BL-069** (P2, open): "Update C4 architecture documentation for v009 changes" — originally tracked 5 v009 drift items, with 11 v010 drift items added in notes. Now carries 19 total items including 4 new from v011.
- **PR-007** (P1, open): "C4 architecture documentation drift accumulating across v009-v010" — product request noting the pattern of drift accumulation and recommending re-establishment of dedicated architecture documentation features.

## Changes in v011

v011 delivered 5 features across 2 themes:

**Theme 01: scan-and-clip-ux**
- New `GET /api/v1/filesystem/directories` endpoint with `validate_scan_path()` security enforcement
- New `DirectoryBrowser` React component (overlay within ScanModal)
- New `ClipFormModal` React component for Add/Edit/Delete clip controls
- New `clipStore` Zustand store following per-entity store pattern
- Wired clip CRUD controls to existing backend endpoints (no new backend CRUD endpoints)

**Theme 02: developer-onboarding**
- `.env.example` created (documentation/config, no architecture impact)
- Windows Git Bash guidance in AGENTS.md (documentation, no architecture impact)
- `IMPACT_ASSESSMENT.md` design-time checks (documentation, no architecture impact)

## Documentation Status

| Document | Exists | Last Updated | Generated For |
|----------|--------|-------------|---------------|
| docs/C4-Documentation/README.md | Yes | 2026-02-24 | v011 (delta) |
| docs/C4-Documentation/c4-context.md | Yes | 2026-02-24 | v011 |
| docs/C4-Documentation/c4-container.md | Yes | 2026-02-24 | v011 |
| docs/C4-Documentation/c4-component.md | Yes | 2026-02-24 | v011 |
| docs/ARCHITECTURE.md | Yes | — | — |
| 43 code-level docs | Yes | 2026-02-24 | v011 |

C4 documentation was regenerated in delta mode for v011. Code-level documents correctly document all new v011 components (DirectoryBrowser, ClipFormModal, clipStore, filesystem router/schemas). The `Filesystem Browser` feature is listed in the context-level features table. The filesystem endpoint appears in the container-level API interface list.

## Drift Assessment

**Code-level docs**: No drift. All v011 additions are correctly documented at the code level.

**Higher-level summary drift** (4 items, all count/list inconsistencies):

1. **Component count stale**: c4-component-web-gui.md and c4-container.md say "22 React components" but there are 24 (DirectoryBrowser and ClipFormModal added in v011). Evidence: `gui/src/components/` contains 24 `.tsx` files.

2. **Store count stale**: c4-component-web-gui.md and c4-container.md say "7 Zustand stores" but there are 8 (clipStore added in v011). Evidence: `gui/src/stores/` contains 8 `.ts` files.

3. **Component name list incomplete**: c4-component-web-gui.md line 32 explicitly lists 22 component names, omitting DirectoryBrowser and ClipFormModal.

4. **Store name list incomplete**: c4-component-web-gui.md line 35 explicitly lists 7 store names, omitting clipStore.

**Root cause**: Delta regeneration updated code-level docs but did not propagate count/name-list updates to higher-level summary sections in component and container docs.

**Severity**: Low. The detailed code-level documentation is accurate — only aggregate counts and inline name lists at higher C4 levels are stale. This would not cause incorrect architectural decisions but could cause confusion during onboarding.

## Action Taken

Updated existing **BL-069** notes with 4 new v011 drift items (items 12-15), bringing the total to 19 drift items across v009/v010/v011. No new backlog item was created since BL-069 already covers this scope.

The v011 drift items are minor compared to the v009/v010 items (which include stale API contracts, missing async patterns, and undocumented dispatch mechanisms). The v011 items are purely count/list inconsistencies at higher C4 levels where code-level docs are already correct.

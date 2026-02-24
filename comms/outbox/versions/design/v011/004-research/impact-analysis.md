# Impact Analysis: v011

## Dependencies

### Code Dependencies

| BL | Files Modified | Files Created | Dependencies |
|----|---------------|---------------|-------------|
| BL-075 | `gui/src/components/ProjectDetails.tsx`, `gui/src/hooks/useProjects.ts` | `gui/src/stores/clipStore.ts`, `gui/src/components/ClipFormModal.tsx`, `gui/src/components/DeleteConfirmation.tsx` (may reuse existing) | Backend clip CRUD endpoints (exist), Zustand (installed), Tailwind CSS (installed) |
| BL-070 | `gui/src/components/ScanModal.tsx` | New backend endpoint file (e.g., `src/stoat_ferret/api/routers/filesystem.py`), `gui/src/components/DirectoryBrowser.tsx` | `allowed_scan_roots` security pattern, `os.listdir` / `os.scandir` |
| BL-071 | `docs/setup/02_development-setup.md`, `docs/manual/01_getting-started.md` | `.env.example` (project root) | `src/stoat_ferret/api/settings.py` (read-only reference) |
| BL-076 | None | `docs/auto-dev/IMPACT_ASSESSMENT.md` | Auto-dev Task 003 consumption pathway |
| BL-019 | `AGENTS.md` | None | None |

### Tool/Config Dependencies

- **BL-070**: If a new API endpoint is added, `docs/design/05-api-specification.md` needs updating (impact #9 from Task 003)
- **BL-075**: No new backend work — all endpoints exist. Frontend-only.
- **BL-071**: No tool dependencies. File creation only.

## Breaking Changes

**None identified.** All v011 backlog items are additive:
- BL-075: Adds UI controls to existing read-only page. No API changes.
- BL-070: Adds browse button alongside existing text input (both remain functional).
- BL-071: New file (`.env.example`). No existing behavior changed.
- BL-076: New file (`IMPACT_ASSESSMENT.md`). Auto-dev gracefully handles its absence.
- BL-019: Documentation addition only.

## Test Impact

### New Tests Required

| BL | Test Type | Description |
|----|-----------|-------------|
| BL-075 | Vitest | ClipFormModal: render, validation, submit, error display. DeleteConfirmation for clips. clipStore async actions. ProjectDetails integration with CRUD controls. |
| BL-075 | Vitest | API client functions: createClip, updateClip, deleteClip (mock fetch). |
| BL-070 | Vitest | DirectoryBrowser component: render, navigation, selection. ScanModal integration with browse button. |
| BL-070 | pytest | Backend directory listing endpoint: valid path, invalid path, security (allowed_scan_roots rejection), non-directory path. |
| BL-071 | Manual | Verify `.env.example` contains all 11 Settings fields with correct STOAT_ prefix. |
| BL-076 | Manual | Verify IMPACT_ASSESSMENT.md format is consumable by auto-dev Task 003. |
| BL-019 | Manual | Verify AGENTS.md Windows section renders correctly. |

### Existing Tests Affected

- **BL-075**: `gui/src/components/__tests__/ProjectDetails.test.tsx` — needs update to account for new CRUD buttons/modals in the component.
- **BL-070**: `gui/src/components/__tests__/ScanModal.test.tsx` — needs update to test browse button interaction.
- **BL-070**: If new backend endpoint, existing API test patterns in `tests/` apply.

## Documentation Updates

| BL | Document | Update Required |
|----|----------|----------------|
| BL-075 | `docs/design/08-gui-architecture.md` | Add clip CRUD controls to Project Manager section |
| BL-075 | `docs/C4-Documentation/c4-component-web-gui.md` | Add POST/PATCH/DELETE clip endpoints |
| BL-075 | `docs/C4-Documentation/c4-code-gui-components.md` | Add new component entries |
| BL-070 | `docs/design/08-gui-architecture.md` | Update ScanModal description |
| BL-070 | `docs/design/05-api-specification.md` | Add directory listing endpoint (if backend approach) |
| BL-070 | `docs/manual/06_gui-guide.md` | Update scanning section |
| BL-071 | `docs/setup/02_development-setup.md` | Add `.env.example` copy step |
| BL-071 | `docs/manual/01_getting-started.md` | Reference `.env.example` |
| BL-071 | `docs/setup/04_configuration.md` | Add 2 missing variables |

All 14 documentation impacts from Task 003 are accounted for above.

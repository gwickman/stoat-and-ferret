# Validation Details - v011

## 1. Content Completeness Check

### Method
Compared all 14 file pairs between Task 007 drafts (`comms/outbox/exploration/design-v011-007-drafts/drafts/`) and persisted inbox documents (`comms/inbox/versions/execution/v011/`).

### Results

| # | Document | Verdict | Notes |
|---|----------|---------|-------|
| 1 | VERSION_DESIGN.md | MISMATCH (expected) | Reformatted by `design_version` MCP tool. Semantic content preserved. Draft's "Key Design Decisions" table and "Design Artifacts" listing dropped. |
| 2 | THEME_INDEX.md | MISMATCH (expected) | Reformatted by `design_version` MCP tool. Added `## Execution Order`, `## Notes` sections. Feature descriptions gained trailing periods. |
| 3 | scan-and-clip-ux/THEME_DESIGN.md | MATCH | Trivial: missing trailing newline |
| 4 | browse-directory/requirements.md | MATCH | Trivial: missing trailing newline |
| 5 | browse-directory/implementation-plan.md | MATCH | Trivial: table separator dash count, missing trailing newline |
| 6 | clip-crud-controls/requirements.md | MATCH | Trivial: missing trailing newline |
| 7 | clip-crud-controls/implementation-plan.md | MATCH | Trivial: table separator dash count, missing trailing newline |
| 8 | developer-onboarding/THEME_DESIGN.md | MATCH | Trivial: missing trailing newline |
| 9 | env-example/requirements.md | MATCH | Trivial: missing trailing newline |
| 10 | env-example/implementation-plan.md | MATCH | Trivial: table separator dash count, missing trailing newline |
| 11 | windows-dev-guidance/requirements.md | MATCH | Trivial: missing trailing newline |
| 12 | windows-dev-guidance/implementation-plan.md | MATCH | Trivial: table separator dash count, missing trailing newline |
| 13 | impact-assessment/requirements.md | MATCH | Trivial: missing trailing newline |
| 14 | impact-assessment/implementation-plan.md | MATCH | Trivial: table separator dash count, missing trailing newline |

**Summary:** 12/14 content-identical. 2/14 reformatted by MCP tool (expected). 0 truncated.

## 2. Reference Resolution

### Design Artifact Store Verification

All referenced paths under `comms/outbox/versions/design/v011/` verified:

| Path | Status |
|------|--------|
| `006-critical-thinking/` (directory) | EXISTS |
| `006-critical-thinking/risk-assessment.md` | EXISTS |
| `006-critical-thinking/investigation-log.md` | EXISTS |
| `004-research/external-research.md` | EXISTS |
| `004-research/codebase-patterns.md` | EXISTS |
| `004-research/evidence-log.md` | EXISTS |

Design artifact store contains 23 files across 6 subdirectories (001-environment through 006-critical-thinking).

## 3. Notes Propagation

| Backlog Item | Key Note | Propagated To | Status |
|-------------|----------|---------------|--------|
| BL-075 | AC3 "label" field does not exist | clip-crud-controls requirements.md, implementation-plan.md, THEME_DESIGN.md, VERSION_DESIGN.md | Propagated |
| BL-070 | showDirectoryPicker not viable | browse-directory requirements.md, THEME_DESIGN.md | Propagated |
| BL-070 | Empty allowed_scan_roots = all permitted (LRN-017) | browse-directory requirements.md, THEME_DESIGN.md | Propagated |
| BL-019 | .gitignore half already done | windows-dev-guidance requirements.md | Propagated |
| BL-071 | 2 missing config variables in docs | env-example implementation-plan.md | Propagated |
| BL-076 | Format validated for Task 003 consumption | impact-assessment requirements.md, THEME_DESIGN.md | Propagated |

## 4. validate_version_design Tool

```json
{
  "valid": true,
  "version": "v011",
  "themes_validated": 2,
  "features_validated": 5,
  "documents": {
    "found": 16,
    "missing": []
  },
  "consistency_errors": []
}
```

## 5. Backlog Alignment

### Backlog Item -> Feature Mapping

| BL Item | Title | Priority | Status | Feature | Mapped |
|---------|-------|----------|--------|---------|--------|
| BL-019 | Windows bash /dev/null guidance | P3 | open | 002-windows-dev-guidance | Yes |
| BL-070 | Browse button for scan directory | P2 | open | 001-browse-directory | Yes |
| BL-071 | .env.example file | P2 | open | 001-env-example | Yes |
| BL-075 | Clip management controls | P1 | open | 002-clip-crud-controls | Yes |
| BL-076 | IMPACT_ASSESSMENT.md | P1 | open | 003-impact-assessment | Yes |

**All 5 backlog items mapped. 0 deferred. 0 missing.**

### Acceptance Criteria Alignment

- **BL-019** (4 AC): All 4 AC match windows-dev-guidance requirements.
- **BL-070** (4 AC): All 4 AC match browse-directory requirements. AC2 adapted — "folder selection dialog" implemented as backend-assisted directory browser (showDirectoryPicker not viable).
- **BL-071** (4 AC): All 4 AC match env-example requirements.
- **BL-075** (6 AC): 5/6 AC match. AC3 references "label" field which does not exist — documented as AC drafting error, implementation uses `timeline_position` instead.
- **BL-076** (6 AC): All 6 AC match impact-assessment requirements.

## 6. File Paths Exist

### Files to Modify (13 files)

| File | Status |
|------|--------|
| src/stoat_ferret/api/app.py | EXISTS |
| gui/src/components/ScanModal.tsx | EXISTS |
| gui/src/components/__tests__/ScanModal.test.tsx | EXISTS |
| docs/design/05-api-specification.md | EXISTS |
| src/stoat_ferret/api/services/scan.py | EXISTS |
| gui/src/components/ProjectDetails.tsx | EXISTS |
| gui/src/hooks/useProjects.ts | EXISTS |
| gui/src/components/__tests__/ProjectDetails.test.tsx | EXISTS |
| docs/setup/02_development-setup.md | EXISTS |
| docs/manual/01_getting-started.md | EXISTS |
| docs/setup/04_configuration.md | EXISTS |
| AGENTS.md | EXISTS |
| src/stoat_ferret/api/settings.py | EXISTS |

### Existing Pattern References (2 files)

| File | Status |
|------|--------|
| gui/src/components/DeleteConfirmation.tsx | EXISTS |
| gui/src/components/CreateProjectModal.tsx | EXISTS |
| gui/src/stores/effectStackStore.ts | EXISTS |

### Parent Directories for New Files (8 directories)

| Directory | Status |
|-----------|--------|
| src/stoat_ferret/api/routers/ | EXISTS |
| src/stoat_ferret/api/schemas/ | EXISTS |
| gui/src/components/ | EXISTS |
| gui/src/stores/ | EXISTS |
| tests/test_api/ | EXISTS |
| gui/src/components/__tests__/ | EXISTS |
| gui/src/stores/__tests__/ | MISSING (parent exists — will be created) |
| docs/auto-dev/ | EXISTS |

## 7. Dependency Accuracy

- **Inter-theme:** None (VERSION_DESIGN.md: "No inter-theme dependencies — themes can execute in parallel")
- **Intra-theme (01):** No dependencies. Execution order 001->002 for pipeline validation, not blocking dependency.
- **Intra-theme (02):** 001-env-example before 003-impact-assessment (correct — impact check #2 verifies .env.example updates). 002-windows-dev-guidance is independent.
- **External:** v010 deployed (completed 2026-02-23). Backend clip CRUD endpoints already exist.
- **Circular dependencies:** None detected.

## 8. Mitigation Strategy

N/A — v011 does not fix bugs that affect its own execution. The BL-075 AC3 label field issue is handled by documenting it as an AC drafting error and scoping `label` out of the implementation.

## 9. Design Docs Committed

`git status comms/inbox/versions/execution/v011/` returned no output (no uncommitted changes). All 15 documents are committed and tracked.

## 10. Handover Document

STARTER_PROMPT.md verified at `comms/inbox/versions/execution/v011/STARTER_PROMPT.md`:
- References AGENTS.md
- Specifies THEME_INDEX.md as execution order source
- Describes per-feature process (read docs, implement, quality gates, output docs)
- Specifies STATUS.md tracking path
- Lists required output documents (completion-report.md, quality-gaps.md, handoff-to-next.md)
- Includes quality gate commands (ruff, mypy, pytest)

## 11. Impact Analysis Completeness

| Aspect | VERSION_DESIGN | THEME_DESIGN (01) | THEME_DESIGN (02) |
|--------|---------------|-------------------|-------------------|
| Dependencies identified | Yes (v010, no inter-theme) | Yes (v010, no inter-feature) | Yes (env-example before impact-assessment) |
| Dependents identified | N/A (no downstream versions depend on v011 yet) | N/A | N/A |
| Breaking changes documented | Yes (BL-075 AC3 label caveat) | Yes (risk table) | Yes (risk table) |
| Test impact assessed | Yes (features list test files) | Yes (per-feature test plan) | Yes (manual verification for docs features) |

## 12. Naming Convention Validation

### Theme Folders (pattern: `^\d{2}-[a-z][a-z0-9-]*[a-z0-9]$`)

| Folder | Status |
|--------|--------|
| 01-scan-and-clip-ux | PASS |
| 02-developer-onboarding | PASS |

### Feature Folders (pattern: `^\d{3}-[a-z][a-z0-9-]*[a-z0-9]$`)

| Folder | Status |
|--------|--------|
| 001-browse-directory | PASS |
| 002-clip-crud-controls | PASS |
| 001-env-example | PASS |
| 002-windows-dev-guidance | PASS |
| 003-impact-assessment | PASS |

### THEME_INDEX Feature Lines (pattern: `^- \d{3}-[a-z][a-z0-9-]*[a-z0-9]: .+$`)

All 5 feature lines: PASS

### Double-Numbering Check

No double-numbered prefixes detected. Date strings (2026-02-23) matched the grep pattern but are not folder names.

## 13. Cross-Reference Consistency

### THEME_INDEX vs Folders

| Source | Themes | Features (01) | Features (02) |
|--------|--------|---------------|---------------|
| THEME_INDEX | 01-scan-and-clip-ux, 02-developer-onboarding | 001-browse-directory, 002-clip-crud-controls | 001-env-example, 002-windows-dev-guidance, 003-impact-assessment |
| Disk | 01-scan-and-clip-ux, 02-developer-onboarding | 001-browse-directory, 002-clip-crud-controls | 001-env-example, 002-windows-dev-guidance, 003-impact-assessment |

**Exact match.** No mismatches detected.

## 14. No MCP Tool References

Scanned all 10 feature documents (5 requirements.md + 5 implementation-plan.md) for MCP tool function names:
- `save_learning`, `add_backlog_item`, `query_cli_sessions`, `search_learnings`, `list_learnings`, `update_learning`, `delete_learning`, `explore_project`, `start_exploration`, `complete_theme`, `halt_theme`, `design_theme`, `design_version`, `validate_version_design`, `run_quality_gates`, `generate_completion_report`, `extract_learnings`, `git_write`, `git_read`, `check_usage`

**0 matches found.** Feature docs reference only file-level tools (Read/Write/Edit/Bash).

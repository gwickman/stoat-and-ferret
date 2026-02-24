# Discrepancies - v011

## Non-Blocking Discrepancies (Warnings)

### 1. THEME_INDEX.md Cosmetic Formatting

**Issue:** Missing blank line before `### Theme 02` heading in THEME_INDEX.md (line 16 follows directly after the Theme 01 feature list without a blank separator line).

**Impact:** None — markdown renderers handle this gracefully. Does not affect execution parsing.

**Remediation:** Not required. Cosmetic only.

### 2. VERSION_DESIGN.md and THEME_INDEX.md Reformatted During Persistence

**Issue:** The `design_version` MCP tool reformatted these two top-level files when persisting (Task 008). The draft VERSION_DESIGN.md included a "Key Design Decisions" table (6 decisions with rationale) and a "Design Artifacts" directory listing that were dropped in the persisted version.

**Impact:** Low — the dropped content is informational and available in the design artifact store (`comms/outbox/versions/design/v011/`). The core semantic content (themes, goals, constraints, assumptions, backlog items) is fully preserved.

**Remediation:** Not required. This is expected MCP tool behavior.

### 3. BL-075 AC3 "Label" Field Drafting Error

**Issue:** BL-075 acceptance criterion 3 reads: "Edit button opens an inline or modal form pre-populated with current clip properties (in/out points, label)". No `label` field exists in the clip data model (confirmed by `006-critical-thinking/investigation-log.md`).

**Impact:** None on execution — the implementation plan explicitly marks `label` as out of scope and uses `timeline_position` instead. This is documented in VERSION_DESIGN.md constraints, THEME_DESIGN.md risks, and both feature documents.

**Remediation:** Consider updating BL-075 AC3 to remove the "label" reference after v011 execution. This is a backlog maintenance task, not a blocking issue.

### 4. Missing `gui/src/stores/__tests__/` Directory

**Issue:** The clip-crud-controls implementation plan references creating `gui/src/stores/__tests__/clipStore.test.ts`, but the `__tests__` subdirectory does not currently exist under `gui/src/stores/`.

**Impact:** None — parent directory `gui/src/stores/` exists. The `__tests__` directory will be created during implementation (standard practice).

**Remediation:** Not required. Directory will be created as part of feature implementation.

## Blocking Discrepancies

None identified.

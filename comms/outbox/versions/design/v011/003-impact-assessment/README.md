# Task 003: Impact Assessment — v011

Impact assessment identified **14 impacts** across all 5 backlog items: **11 small** (sub-task scope), **3 substantial** (require explicit feature scoping), **0 cross-version**. No project-specific IMPACT_ASSESSMENT.md exists (BL-076 creates it).

## Generic Impacts

- **Documentation**: 10 impacts across design docs, user guides, setup guides, C4 docs, and AGENTS.md
- **Caller-adoption**: 2 impacts — one substantial (zero frontend callers of clip write API), one clean (BL-076 new file)
- **API specification**: 1 impact — potential new directory browsing endpoint for BL-070

Categories by backlog item:
- **BL-075** (clip CRUD GUI): 6 impacts (2 substantial, 4 small) — largest impact footprint
- **BL-070** (browse button): 3 impacts (1 substantial, 2 small)
- **BL-071** (.env.example): 3 impacts (all small)
- **BL-019** (Windows guidance): 1 impact (small — is the feature itself)
- **BL-076** (IMPACT_ASSESSMENT.md): 1 impact (small — no caller risk)

## Project-Specific Impacts

N/A — no IMPACT_ASSESSMENT.md exists. BL-076 will create this file for future versions.

## Work Items Generated

- **Small (11):** Documentation updates that are natural sub-tasks of their owning features. Most are doc section updates or cross-reference additions.
- **Substantial (3):**
  1. BL-075 must include GUI architecture spec update as an explicit deliverable (not afterthought)
  2. BL-075 must deliver frontend API client functions — the zero-caller gap is the core work
  3. BL-070 design must resolve the browse mechanism (browser API vs backend endpoint) to determine if backend API work is needed

## Recommendations

1. **BL-075 design must be detailed.** It has the largest impact footprint (6 impacts). The GUI architecture spec gap (no clip CRUD wireframe) means the implementation plan must either update the spec first or include it as a deliverable. This aligns with LRN-031 (detailed specs correlate with first-iteration success).

2. **BL-070 needs an architecture decision during logical design.** The browse mechanism (File System Access API vs backend directory listing) determines whether the feature is frontend-only or full-stack. This decision affects API spec, architecture docs, and implementation complexity.

3. **BL-071 doc updates are straightforward** but must cross-check against the Settings class (10 fields) not just the configuration docs (9 fields documented). Two fields (`log_backup_count`, `log_max_bytes`) appear undocumented in config docs.

4. **C4 doc updates for BL-075 should be small sub-tasks**, not a separate feature. The broader C4 refresh (2 versions behind) remains pre-existing tech debt outside v011 scope.

## Output Files

| File | Description |
|------|-------------|
| impact-table.md | 14-row impact table with area, classification, work items, and causing backlog item |
| impact-summary.md | Impacts grouped by classification (small/substantial/cross-version) with recommendations |
| README.md | This summary |

# v002 Version Closure Proposal

Generated: 2026-01-28

## Summary

This document proposes actions for completing v002 version closure. Items marked N/A are specific to auto-dev-mcp and don't apply to stoat-and-ferret.

---

## Checklist Status

| Item | Status | Action Needed |
|------|--------|---------------|
| 1. Review Retrospectives | ✅ Reviewed | Create backlog items |
| 2. Create Version Documentation | ❌ Missing | Create docs/versions/v002/ |
| 3. Update Changelog | ✅ Complete | None |
| 4. Update Capabilities Manifest | N/A | — |
| 5. Review and Apply Learnings | ⚠️ Pending | Create backlog items from tech debt |
| 5a. Golden Scenario Coverage | N/A | — |
| 5b. Contract Test Coverage | N/A | — |
| 5c. Parity Test Coverage | N/A | — |
| 6. Review and Update Skills | N/A | — |
| 7. Skill Drift Detection | N/A | — |
| 8. Update High-Level Documentation | ✅ OK | None (design docs current) |
| 9. Update Setup Documentation | N/A | — |
| 10. Verify State Consistency | ✅ Complete | None |
| 11. Update Plan | ❌ Outdated | Update docs/auto-dev/PLAN.md |
| 12. Archive Explorations | ⚠️ Pending | Archive SAC/WDAC explorations |
| 13. Verify C4 Documentation | N/A | — |
| 14. Final Git Cleanup | ❌ Stale branches | Delete 3 local + 4 remote branches |
| 15. YAGNI Review | ⚠️ Skipped | Optional - no issues flagged |
| 16. Final Commit | ⬜ Pending | After all changes |

---

## Proposed Actions

### Item 1: Review Retrospectives → Create Backlog Items

**Checked:** `comms/outbox/versions/execution/v002/retrospective.md`

**Findings:** Tech debt and process improvements identified that should become backlog items.

**Proposed Actions:**
- [ ] Create BL-013: "Add async repository implementation for FastAPI (aiosqlite)" - P2, v003
- [ ] Create BL-014: "Add Docker-based local testing option" - P2, process
- [ ] Create BL-015: "Add migration verification to CI (upgrade/downgrade/upgrade)" - P2, ci
- [ ] Create BL-016: "Unify InMemory vs FTS5 search behavior" - P3, cleanup

**Approval:** [ ] Approved by user

---

### Item 2: Create Version Documentation

**Checked:** `docs/versions/`

**Findings:** v001 has README.md, v002 directory does not exist.

**Proposed Actions:**
- [ ] Create `docs/versions/v002/README.md` with version summary from retrospective

**Approval:** [ ] Approved by user

---

### Item 11: Update Plan

**Checked:** `docs/auto-dev/PLAN.md`

**Findings:** PLAN.md shows v002 as "planned", needs update to reflect completion.

**Proposed Actions:**
- [ ] Update version table: change v002 status from `planned` to `complete`
- [ ] Add v002 to Completed Versions section with date 2026-01-27
- [ ] Update Change Log with v002 completion entry
- [ ] Remove v002 Backlog Items section (now complete)

**Approval:** [ ] Approved by user

---

### Item 12: Archive Explorations

**Checked:** `comms/outbox/exploration/`

**Findings:** 9 explorations exist. SAC/WDAC-related ones are no longer relevant (SAC disabled).

| Exploration | Status | Action |
|-------------|--------|--------|
| rust-python-hybrid | Valuable | Keep |
| recording-fake-pattern | Valuable | Keep |
| design-research-gaps | v002 context | Keep |
| stub-gen-cli-test | v002 context | Keep |
| sac-uv-workarounds | Obsolete (SAC disabled) | Delete |
| wdac-diagnosis | Obsolete | Delete |
| wdac-bypass-options | Obsolete | Delete |
| uv-blocked-workarounds | Obsolete | Delete |
| test-execution-config | Partial value | Keep (has WDAC fallback docs) |

**Proposed Actions:**
- [ ] Delete obsolete SAC/WDAC exploration folders (4 folders)
- [ ] Keep test-execution-config for reference

**Approval:** [ ] Approved by user

---

### Item 14: Final Git Cleanup

**Checked:** `git branch -a`

**Findings:** Stale branches from v001 and v002 development.

**Local branches to delete:**
- `at/pyo3-bindings-clean`
- `v001/02-timeline-math/003-range-arithmetic`
- `v001/03-command-builder/004-pyo3-bindings`

**Remote branches to delete:**
- `origin/feat/pyo3-bindings-clean`
- `origin/v001/02-timeline-math/003-range-arithmetic`
- `origin/v001/03-command-builder/004-pyo3-bindings`
- `origin/v002/01-rust-python-bindings/001-stub-regeneration`

**Proposed Actions:**
- [ ] Delete 3 local branches: `git branch -D <branch>`
- [ ] Delete 4 remote branches: `git push origin --delete <branch>`

**Approval:** [ ] Approved by user

---

### Item 16: Final Commit

**Proposed Actions:**
- [ ] Commit all closure changes with message: `chore(v002): version closure housekeeping`
- [ ] Push to main
- [ ] Call `complete_version(project="stoat-and-ferret", version_number=2)`

**Approval:** [ ] Approved by user

---

## Summary of Actions

| Category | Count |
|----------|-------|
| Backlog items to create | 4 |
| Documents to create/update | 2 (v002 README, PLAN.md update) |
| Explorations to delete | 4 |
| Git branches to delete | 7 (3 local + 4 remote) |
| Final commit | 1 |

**Ready for user approval.**

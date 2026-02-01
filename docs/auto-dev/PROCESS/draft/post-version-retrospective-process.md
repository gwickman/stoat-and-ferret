# Post-Version Retrospective Process

Autonomous procedure for completing a version after execution finishes. Run by Claude Code without user intervention.

## Prerequisites

- Version execution completed (all themes/features show status "completed")
- Claude Code has access to project repository
- Quality gate tools available (ruff, mypy, pytest)

---

## Stage 1: Pre-Restart Verification

Complete all checks before signaling user to restart Claude Desktop.

### 1.1 Git Status

```bash
# Verify clean state
git status  # Must show clean working directory
git branch --show-current  # Must be on main
git fetch origin
git status  # Must show "up to date with origin/main"
```

**If uncommitted changes exist:** Commit with message `chore(vXXX): version completion cleanup`

**If open PRs exist for this version:** Merge or document why they remain open.

### 1.2 Quality Gates

Run all quality checks:

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest -v
```

All must pass. If failures exist, fix before proceeding.

### 1.3 Documentation Verification

Verify these documents exist:

| Document | Location |
|----------|----------|
| Completion reports | `comms/outbox/vXXX/<theme>/<feature>/completion-report.md` |
| Theme summaries | `comms/outbox/vXXX/<theme>/summary.md` |
| Version state | `comms/outbox/vXXX/version-state.json` |

**For each missing document:** Generate from available information or note gap in retrospective.

### 1.4 Backlog Item Closure

1. Read `docs/auto-dev/PLAN.md` and locate the vXXX version section
2. Extract all backlog item references (BL-XXX patterns) listed for this version
3. For each referenced item, verify implementation status against completion reports
4. Update `docs/auto-dev/backlog.json`:
   - Change status from "open" to "completed"
   - Add `completed_in: vXXX/theme-name` reference
   - Add completion date

### 1.5 State Consistency

Verify `comms/outbox/vXXX/version-state.json`:
- Status is "completed" or ready to mark complete
- All themes listed with correct status
- All features accounted for

---

## Stage 2: Retrospective Generation

**Note:** If the version retrospective already exists (e.g., generated during version execution), verify it contains all required sections below rather than generating a new one.

Generate version retrospective at `comms/outbox/vXXX/retrospective.md`.

### Required Sections

```markdown
# vXXX Retrospective

## Summary

- **Goal:** [Version objective from VERSION_DESIGN.md]
- **Outcome:** [Achieved/Partial/Failed]
- **Themes completed:** X/Y
- **Features completed:** X/Y
- **Duration:** [Start time] to [End time]

## Themes

### Theme 1: [name]
- Features: [list]
- Notable outcomes: [brief]
- Issues encountered: [if any]

[Repeat for each theme]

## Metrics

| Metric | Value |
|--------|-------|
| Total features | X |
| First-pass success | X |
| Required iterations | X |
| Quality gate status | Pass/Fail |

## Learnings

### What Went Well
- [Pattern or decision that helped]

### What Could Improve
- [Bottleneck or issue encountered]

### Technical Debt Introduced
- [Any shortcuts taken, note backlog item needed if applicable]

## Architecture Alignment

Compare implemented changes against project architecture documentation:

- [ ] Changes align with documented architecture
- [ ] New components documented (or note backlog item needed)
- [ ] Removed/deprecated components noted
- [ ] If architecture drift detected, note backlog item needed for documentation update

## Action Items

| Item | Type | Priority |
|------|------|----------|
| [Description] | Backlog needed/Doc update/Process change | P1/P2/P3 |
```

### Learning Extraction

For significant learnings, create entry in `docs/auto-dev/LEARNINGS/`:

**Include in learnings:**
- Transferable patterns
- Failure modes and avoidance strategies
- Decision frameworks that worked
- Design rationale (why, not just what)
- Rejected alternatives and why they didn't work

**Exclude from learnings:**
- Implementation details (code, file paths)
- Version-specific context that won't generalize

---

## Stage 3: Version Closure

### 3.1 Documentation Cleanup

Update project documentation to reflect completed version:

| Document | Action |
|----------|--------|
| `docs/auto-dev/PLAN.md` | Mark vXXX as completed, update "Current Version" section |
| `CHANGELOG.md` | Add version entry (see format below) |
| `README.md` | Update if new capabilities affect usage |
| API documentation | Update if endpoints changed |

**CHANGELOG entry format:**

```markdown
## vXXX - YYYY-MM-DD

### Added
- [New feature descriptions]

### Changed
- [Modified behavior]

### Fixed
- [Bug fixes]
```

### 3.2 Repository Cleanup

```bash
# List and delete merged feature branches (local)
git branch --merged main | grep -E "feature/vXXX" | xargs -r git branch -d

# Delete remote feature branches (if applicable)
git push origin --delete $(git branch -r --merged origin/main | grep -E "feature/vXXX" | sed 's/origin\///')

# Verify no stale PRs for this version
gh pr list --state open --search "vXXX"

# Create release tag (if using semantic versioning)
git tag -a vX.Y.Z -m "Release vXXX: [brief description]"
git push origin vX.Y.Z
```

### 3.3 Code Quality Final Check

Run comprehensive quality verification:

```bash
# Linting
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/

# Type checking
uv run mypy src/

# Full test suite
uv run pytest -v

# Coverage verification (adjust threshold per project)
uv run pytest --cov=src --cov-report=term-missing --cov-fail-under=80

# CI pipeline status
gh run list --limit 5  # Verify recent runs are green
```

All checks must pass before proceeding.

### 3.4 Architecture Maintenance

Review and update architecture documentation:

| Check | Action if Needed |
|-------|------------------|
| C4 documentation current | Check `docs/auto-dev/backlog.json` for existing open C4/architecture item. If none exists, note that a backlog item needs to be created. |
| New components documented | Add to appropriate C4 level, or note backlog item needed |
| Deprecated components | Mark for removal in architecture docs |
| README.md architecture section | Update if structure changed |

**If significant architecture changes occurred:**
1. Check `docs/auto-dev/backlog.json` for existing open architecture documentation items
2. If no relevant open item exists, note in retrospective that a backlog item needs to be created
3. Update README.md timestamp if any architecture docs were updated
4. Commit with message `docs: update architecture for vXXX`

### 3.5 Final Commit

Commit all closure changes:

```bash
git add -A
git status  # Review changes

# Commit with standardized message
git commit -m "chore(vXXX): version closure housekeeping

- Updated CHANGELOG.md
- Marked backlog items complete
- Generated retrospective
- Cleaned feature branches
- [Other closure actions taken]"

git push origin main
```

---

## Stage 4: State Finalization

### 4.1 Update Version State

Edit `comms/outbox/vXXX/version-state.json`:

```json
{
  "version": "vXXX",
  "status": "completed",
  "completed_at": "YYYY-MM-DDTHH:MM:SSZ",
  "themes_completed": N,
  "features_completed": N,
  "retrospective_path": "comms/outbox/vXXX/retrospective.md"
}
```

### 4.2 Update Plan Document

In `docs/auto-dev/PLAN.md`, update the version entry:

```markdown
## vXXX - [Title]

**Status:** ✅ Completed (YYYY-MM-DD)
**Retrospective:** [link to retrospective.md]

[Existing content...]
```

### 4.3 Final Verification

```bash
# Verify clean state
git status  # Must be clean
git log -1  # Verify closure commit is latest
git push --dry-run  # Verify nothing to push

# Verify key files exist
ls comms/outbox/vXXX/retrospective.md
ls comms/outbox/vXXX/version-state.json
```

---

## Stage 5: Handoff

Signal completion:

1. Verify `version-state.json` shows `"status": "completed"`
2. Verify retrospective exists at `comms/outbox/vXXX/retrospective.md`
3. Verify git status is clean and pushed
4. Verify CI pipeline is green

**Output:** Version vXXX closure complete. Ready for next version planning.

---

## Error Handling

### Quality Gate Failures
- Fix issues in-place
- Re-run quality gates
- Commit fixes with message `fix(vXXX): quality gate remediation`

### Missing Completion Reports
- Generate summary from git history and PR descriptions
- Note incompleteness in retrospective

### Backlog Item Not Found
- Log warning, continue with closure
- Note discrepancy in retrospective action items

### Git Conflicts
- Halt and report to user
- Do not force-push or override

### CI Pipeline Red
- Investigate failure
- Fix if related to version changes
- If unrelated, note in retrospective and continue

---

## Checklist Summary

### Stage 1: Pre-Restart Verification
```
[ ] Git clean, on main, up to date
[ ] Quality gates pass (ruff, mypy, pytest)
[ ] Completion reports exist for all features
[ ] Backlog items identified from PLAN.md
[ ] Backlog items closed in backlog.json
[ ] version-state.json consistent
```

### Stage 2: Retrospective
```
[ ] Retrospective generated with all required sections
[ ] Architecture alignment checked
[ ] Learnings extracted and documented
[ ] Action items captured (including any backlog items needed)
```

### Stage 3: Version Closure
```
[ ] PLAN.md updated (version marked complete)
[ ] CHANGELOG.md updated
[ ] README.md updated (if needed)
[ ] Feature branches deleted
[ ] Release tag created (if applicable)
[ ] Quality gates pass (final check)
[ ] Architecture docs checked (existing backlog item or note needed)
[ ] Closure changes committed
```

### Stage 4: State Finalization
```
[ ] version-state.json status set to "completed"
[ ] PLAN.md version entry updated
[ ] Final verification passed
```

### Stage 5: Handoff
```
[ ] All state files in place
[ ] Git clean and pushed
[ ] CI green
[ ] Ready for next version
```

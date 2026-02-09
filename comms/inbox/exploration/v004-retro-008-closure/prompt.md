Read AGENTS.md first and follow all instructions there.

## Objective

Execute mandatory version closure tasks for stoat-and-ferret version v004: plan updates, CHANGELOG verification, README review, and repository cleanup.

## Tasks

### 1. Update PLAN.md
Read `docs/auto-dev/PLAN.md` (or `docs/auto-dev/plan.md`) and make these changes:
- Mark v004 as completed in the version list
- Update "Current Version" section to reflect the next planned version
- Move completed items from "Planned" to "Completed" section

If PLAN.md does not exist, document this in the output.

### 2. Verify CHANGELOG.md
Read `docs/CHANGELOG.md` and verify:
- v004 section exists with date
- Section contains categorized entries (Added, Changed, Fixed)
- Entries match actual changes (cross-reference with theme retrospectives in comms/outbox/versions/execution/v004/)

If entries are missing or incorrect, add/fix them.

### 3. Review README.md
Read the project root README.md and check:
- Do any new capabilities from v004 need to be reflected?
- Are any described features now removed or changed?
- Is the project description still accurate?

If README needs updates: make the specific changes. If no changes needed: document why.

### 4. Repository Cleanup
Verify repository state:
- Check for open PRs related to v004
- Check for stale branches from v004
- Check working tree is clean

Document findings.

## Output Requirements

Save outputs to comms/outbox/exploration/v004-retro-008-closure/:

### README.md (required)
First paragraph: Closure summary (X items completed, Y documents updated).

Then:
- **Plan.md**: Updated/not found/no changes needed
- **CHANGELOG**: Verified complete / entries added
- **README**: Updated / no changes needed
- **Repository**: Clean / stale branches found

### closure-report.md
Detailed report of all changes made with exact diffs.

Do NOT commit — the calling prompt handles commits. Results folder: v004-retro-008-closure.
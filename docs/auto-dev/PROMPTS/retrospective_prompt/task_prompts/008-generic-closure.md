# Task 008: Generic Closure

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Execute mandatory version closure tasks that apply to all auto-dev-mcp managed projects: plan updates, CHANGELOG verification, README review, and repository cleanup.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. These closure tasks are required for every version regardless of project.

## Tasks

### 1. Update plan.md

Read `docs/auto-dev/plan.md` and make these changes (the file is lowercase `plan.md`, not `PLAN.md`):
- Mark `${VERSION}` as completed in the version list
- Update "Current Version" section to reflect the next planned version
- Move completed items from "Planned" to "Completed" section

If `plan.md` does not exist, document this in the output.

### 2. Verify CHANGELOG.md

Read `docs/CHANGELOG.md` and verify:
- `${VERSION}` section exists with date
- Section contains categorized entries (Added, Changed, Fixed)
- Entries match the actual changes made (cross-reference with theme retrospectives)

If entries are missing or incorrect, add/fix them.

### 3. Review README.md

Read the project root `README.md` and check:
- Do any new capabilities from `${VERSION}` need to be reflected?
- Are any described features now removed or changed?
- Is the project description still accurate?

If README needs updates: make the specific changes. If no changes needed: document "README current, no updates required."

### 4. Repository Cleanup

Verify repository state:

```python
git_read(project="${PROJECT}", operation="prs", state="open")
# All version-related PRs should be merged

git_read(project="${PROJECT}", operation="stale_branches")
# No stale feature branches from this version

git_read(project="${PROJECT}", operation="status")
# Working tree clean
```

If stale branches exist, document them for cleanup.

<!-- Documentation review moved to design-phase impact assessment (003-impact-assessment.md).
     See docs/auto-dev/IMPACT_ASSESSMENT.md for project-specific checks. -->

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/008-closure/`:

### README.md (required)

First paragraph: Closure summary (X items completed, Y documents updated).

Then:
- **Plan.md**: Updated/not found/no changes needed
- **CHANGELOG**: Verified complete / entries added
- **README**: Updated / no changes needed
- **Repository**: Clean / stale branches found

### closure-report.md

Detailed report of all changes made:
- Exact diffs for plan.md changes
- Exact diffs for CHANGELOG changes
- Exact diffs for README changes
- Repository cleanup actions taken

## Allowed MCP Tools

- `read_document`
- `git_read`
- `list_product_requests`
- `get_product_request`
- `add_product_request`
- `update_product_request`
- `upvote_item`

## Guidelines

- Make changes directly — do not propose and wait for approval
- For documentation review, check every document that could be affected, not just an obvious subset
- If a document needs substantial rewriting, make the changes — do not create a backlog item
- Do NOT commit — the master prompt handles commits

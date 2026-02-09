Read AGENTS.md first and follow all instructions there.

## Objective

Verify the environment is ready for retrospective execution for stoat-and-ferret version v005.

## Tasks

### 1. Health Check
Run `health_check()` and verify MCP server is running. Document the result.

### 2. Git Status
Run `git_read(project="stoat-and-ferret", operation="status")` and verify:
- Working tree is clean (no uncommitted changes)
- On `main` branch
- Up to date with remote

If working tree is dirty, document all uncommitted files.

### 3. PR Status
Run `git_read(project="stoat-and-ferret", operation="prs", state="open")` and verify no open PRs related to v005 remain. Document any open PRs.

### 4. Version Execution Status
Run `get_version_status(project="stoat-and-ferret", version_number=5)`. Verify version status is "completed" or all themes show completed status. Document the version state summary.

### 5. Branch Verification
Run `git_read(project="stoat-and-ferret", operation="branches")` and verify no stale feature branches from v005 remain.

## Output Requirements

Save outputs to comms/outbox/exploration/v005-retro-001-environment/

### README.md (required)
First paragraph: Environment status summary (ready/blocked) with key findings.

Then:
- **Health Check**: Pass/fail with details
- **Git Status**: Branch, working tree state, remote sync
- **Open PRs**: List or "none"
- **Version Status**: Execution state summary
- **Stale Branches**: List or "none"
- **Blockers**: Any issues preventing retrospective continuation

### environment-report.md
Detailed results from all checks, including raw outputs.

Commit the results in v005-retro-001-environment with message "docs(v005): retrospective task 001 - environment verification".
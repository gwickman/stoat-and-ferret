# Task 001: Environment Verification

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Verify the environment is ready for retrospective execution: MCP server healthy, git clean, PRs merged, version execution complete.

## Context

This is the first step in the post-version retrospective for `${PROJECT}` version `${VERSION}`. All outputs go to the centralized retrospective deliverables store.

## Tasks

### 1. Health Check

Run `health_check()` and verify:
- MCP server is running (`success: true`)
- No critical errors reported

Document the health check result.

### 2. Git Status

Run `git_read(project="${PROJECT}", operation="status")` and verify:
- Working tree is clean (no uncommitted changes)
- On `main` branch
- Up to date with remote

If working tree is dirty, document all uncommitted files.

### 3. PR Status

Run `git_read(project="${PROJECT}", operation="prs", state="open")` and verify:
- No open PRs related to `${VERSION}` remain
- If open PRs exist: document them as blockers

### 4. Version Execution Status

Run `get_version_status(project="${PROJECT}", version_number=<N>)` where N is extracted from `${VERSION}`.

Verify:
- Version status is "completed" or all themes show completed status
- All features within each theme have completion reports

Document the version state summary.

### 5. Branch Verification

Run `git_read(project="${PROJECT}", operation="branches")` and verify:
- No stale feature branches from `${VERSION}` remain
- Document any branches that should have been deleted

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/001-environment/`:

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

## Allowed MCP Tools

- `health_check`
- `get_project_info`
- `get_version_status`
- `git_read`
- `read_document`
- `list_product_requests`
- `get_product_request`
- `add_product_request`
- `update_product_request`
- `upvote_item`

## Guidelines

- If any check reveals a blocker, document it clearly — the master prompt will halt
- Do NOT attempt to fix issues — only report them
- Do NOT commit — the master prompt handles commits

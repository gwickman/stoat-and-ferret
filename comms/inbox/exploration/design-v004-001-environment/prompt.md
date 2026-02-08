You are performing Task 001: Environment Verification for stoat-and-ferret version v004.

Read AGENTS.md first and follow all instructions there.

PROJECT=stoat-and-ferret
VERSION=v004

## Objective

Verify the design environment is ready and gather essential context about the project and version scope.

## Tasks

### 1. Environment Health Check

Run `health_check()` and verify:
- MCP server is running (success: true)
- Claude Code is configured and available
- No critical errors reported

Document any issues found.

### 2. Project Configuration Check

Run `get_project_info(project="stoat-and-ferret")` and verify:
- Project exists and is properly configured
- Note any active themes or execution state

### 3. Git Status Check

Run `git_read(project="stoat-and-ferret", operation="status")` and verify:
- Working tree is clean (or document why uncommitted changes are acceptable)
- Current branch noted
- Remote tracking configured

### 4. C4 Architecture Review

Check for C4 documentation:
- Read `docs/C4-Documentation/README.md` if it exists
- Note timestamp and currency
- Scan relevant component diagrams
- Document any architectural context relevant to version planning

### 5. Gather Version Context from PLAN.md

Read `docs/auto-dev/PLAN.md` to understand:
- The version description and goals for v004
- All backlog items referenced for this version
- Any deferred items from previous versions
- Constraints or assumptions documented

## Output Requirements

Create findings in comms/outbox/exploration/design-v004-001-environment/:

### README.md (required)

First paragraph: Summary of environment status (ready/blocked) and key context.

Then:
- **Environment Status**: Health check results, any issues
- **Project Status**: Current state, active work
- **Git Status**: Branch, working tree state
- **Architecture Context**: C4 docs status, key architectural patterns
- **Version Scope**: Backlog items, goals, constraints from PLAN.md

### environment-checks.md

Detailed results from all health and status checks.

### version-context.md

Complete context from PLAN.md including:
- Version goals and description
- All referenced backlog items (IDs only, full details in Task 002)
- Constraints and assumptions
- Deferred items to be aware of

## Guidelines

- Keep documents focused and under 200 lines each
- If environment checks fail, clearly document blockers
- Do not fetch full backlog item details here (that's Task 002)

## When Complete

After writing all output files to comms/outbox/exploration/design-v004-001-environment/, also COPY the README.md, environment-checks.md, and version-context.md to comms/outbox/versions/design/v004/001-environment/ so they are in the design artifact store.

git add comms/outbox/exploration/design-v004-001-environment/
git commit -m "exploration: design-v004-001-environment - environment verification complete"

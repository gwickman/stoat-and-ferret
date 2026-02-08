# Task 002: Documentation Completeness

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Verify all required documentation artifacts exist for every theme and feature in `${VERSION}`.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. This task checks that the version execution produced all required documentation.

## Tasks

### 1. Identify Version Structure

Read `comms/inbox/versions/execution/${VERSION}/THEME_INDEX.md` to determine:
- All themes in this version
- All features within each theme

### 2. Check Feature Completion Reports

For each feature in each theme, verify this file exists:
- `comms/outbox/versions/execution/${VERSION}/<theme>/<feature>/completion-report.md`

Record: feature path, exists (yes/no), status from report if exists.

### 3. Check Theme Retrospectives

For each theme, verify this file exists:
- `comms/outbox/versions/execution/${VERSION}/<theme>/retrospective.md`

Record: theme name, exists (yes/no).

### 4. Check Version Retrospective

Verify this file exists:
- `comms/outbox/versions/execution/${VERSION}/retrospective.md`

### 5. Check CHANGELOG.md

Read `docs/CHANGELOG.md` and verify:
- A section for `${VERSION}` exists
- Section contains at least one entry

### 6. Check version-state.json

Verify `comms/state/version-state.json` or the version execution state file exists and contains:
- Correct version identifier
- Status field

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/002-documentation/`:

### README.md (required)

First paragraph: Documentation completeness summary (X/Y artifacts present).

Then:
- **Completion Reports**: Table of feature → status
- **Theme Retrospectives**: Table of theme → status
- **Version Retrospective**: Present/missing
- **CHANGELOG**: Present/missing, has version section
- **Version State**: Present/missing, status value
- **Missing Artifacts**: List of all missing documents with full paths

### completeness-report.md

Detailed table:

```markdown
| Artifact Type | Path | Exists | Notes |
|---------------|------|--------|-------|
| Completion Report | comms/outbox/.../completion-report.md | Yes | status: complete |
```

## Allowed MCP Tools

- `read_document`
- `get_version_status`
- `get_theme_status`

## Guidelines

- Check every feature — do not sample
- Record the exact path for missing artifacts (the proposals task needs these)
- Do NOT create missing documents — only report gaps
- Do NOT commit — the master prompt handles commits

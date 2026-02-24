# Requirements: impact-assessment

## Goal

Create IMPACT_ASSESSMENT.md with 4 project-specific design-time checks that catch recurring issue patterns before they reach implementation.

## Background

Backlog Item: BL-076 — Create IMPACT_ASSESSMENT.md with project-specific design checks.

stoat-and-ferret has no IMPACT_ASSESSMENT.md, so the auto-dev design phase (Task 003) runs no project-specific checks. RCA analysis identified four recurring issue patterns: (1) blocking subprocess calls in async context (the ffprobe event-loop freeze), (2) Settings fields added without .env.example updates (9 versions without .env.example), (3) features consuming prior-version backends without verifying they work, (4) GUI features with text-only input where richer mechanisms are standard.

## Functional Requirements

**FR-001: File location**
- `docs/auto-dev/IMPACT_ASSESSMENT.md` exists at the expected path for auto-dev Task 003 consumption
- Acceptance: File exists and Task 003 can read it

**FR-002: Async safety check**
- Check section flags features that introduce or modify `subprocess.run`, `subprocess.call`, `subprocess.check_output`, or `time.sleep` inside files containing `async def`
- Includes what to look for (grep patterns), why it matters, and a concrete example (ffprobe blocking bug from v009)
- Acceptance: Check section present with all three subsections

**FR-003: Settings documentation check**
- Check section flags versions that add or modify Settings fields without updating `.env.example`
- Includes what to look for, why it matters, and a concrete example (9 versions without .env.example)
- Acceptance: Check section present with all three subsections

**FR-004: Cross-version wiring check**
- Check section flags features that depend on behavior from prior versions, requiring explicit assumption listing
- Includes what to look for, why it matters, and a concrete example (progress bar assuming v004 progress worked)
- Acceptance: Check section present with all three subsections

**FR-005: GUI input mechanism check**
- Check section flags GUI features accepting user input where appropriate input mechanisms should be verified
- Includes what to look for, why it matters, and a concrete example (scan directory path with no browse button)
- Acceptance: Check section present with all three subsections

**FR-006: Structured format**
- Each check section uses consistent format: check name heading, "What to look for", "Why it matters", "Concrete example" subsections
- Acceptance: All 4 checks follow the same structure

## Non-Functional Requirements

**NFR-001: Machine readability**
- Format must be interpretable by the Claude Code agent running auto-dev Task 003
- Metric: Agent can identify and execute each check from the markdown structure

## Handler Pattern

Not applicable for v011 — no new handlers introduced.

## Out of Scope

- Automated execution of checks (Task 003 handles this)
- Checks beyond the 4 specified in BL-076
- Integration testing of IMPACT_ASSESSMENT.md with auto-dev pipeline (manual verification only)

## Test Requirements

**Manual verification:**
- IMPACT_ASSESSMENT.md has all 4 required check sections
- Each check section has "What to look for", "Why it matters", and "Concrete example" subsections
- File format is consistent and readable
- Auto-dev Task 003 can read and process the file (consumption verification)

## Reference

See `comms/outbox/versions/design/v011/004-research/` for supporting evidence:
- `external-research.md` — auto-dev framework format expectations
- `codebase-patterns.md` — Task 003 consumption pathway
- `006-critical-thinking/risk-assessment.md` — format confirmed appropriate by investigation
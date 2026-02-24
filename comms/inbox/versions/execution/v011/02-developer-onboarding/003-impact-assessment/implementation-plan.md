# Implementation Plan: impact-assessment

## Overview

Create `docs/auto-dev/IMPACT_ASSESSMENT.md` with 4 project-specific design-time checks. Each check includes what to look for, why it matters, and a concrete project-history example. The file is consumed by auto-dev Task 003 during version design.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `docs/auto-dev/IMPACT_ASSESSMENT.md` | Create | Project-specific design-time impact assessment checks |

## Test Files

None — manual verification only.

## Implementation Stages

### Stage 1: Create IMPACT_ASSESSMENT.md

1. Create `docs/auto-dev/IMPACT_ASSESSMENT.md` with the following structure:

**Check 1: Async Safety**
- What to look for: Features that introduce or modify `subprocess.run`, `subprocess.call`, `subprocess.check_output`, or `time.sleep` inside files containing `async def`. Grep patterns: `subprocess\.(run|call|check_output)` and `time\.sleep` in files with `async def`.
- Why it matters: Blocking calls in async context freeze the event loop, preventing concurrent request handling.
- Concrete example: v009 ffprobe used `subprocess.run()` in an async endpoint, blocking all WebSocket heartbeats and concurrent API requests. Fixed in v010 by switching to `asyncio.create_subprocess_exec()`.

**Check 2: Settings Documentation**
- What to look for: Versions that add or modify fields in `src/stoat_ferret/api/settings.py` (the Pydantic BaseSettings class). If fields change, verify `.env.example` is updated.
- Why it matters: Missing .env.example entries cause confusing startup failures for new developers who don't know which variables to configure.
- Concrete example: The project had 11 Settings fields across 9 versions without any .env.example file. New developers had to read settings.py source code to discover configuration.

**Check 3: Cross-Version Wiring Assumptions**
- What to look for: Features that depend on behavior from prior versions — especially features that consume endpoints, WebSocket messages, or state structures introduced in earlier versions. When identified, list assumptions explicitly.
- Why it matters: Prior-version features may have bugs, incomplete implementations, or different behavior than assumed. Unverified assumptions cause runtime failures.
- Concrete example: v010 progress bar feature assumed v004's per-file progress reporting worked correctly. It didn't — the progress data structure was incomplete. The progress bar displayed incorrect data until the underlying reporting was fixed.

**Check 4: GUI Input Mechanisms**
- What to look for: GUI features that accept user input — particularly paths, IDs, or other structured data. Verify the design specifies an appropriate input mechanism (browse dialog, dropdown, autocomplete) rather than defaulting to a plain text input.
- Why it matters: Text-only inputs for structured data are error-prone and create poor UX. Users must know exact values and type them correctly.
- Concrete example: The scan directory feature (v005-v010) used a plain text input for directory paths. Users had to type full paths manually. v011 adds a browse button — this could have been caught at design time if an input mechanism check existed.

**Verification:**
```bash
# Verify file exists
test -f docs/auto-dev/IMPACT_ASSESSMENT.md && echo "exists"
# Verify all 4 check sections
grep -c "^## " docs/auto-dev/IMPACT_ASSESSMENT.md  # Should be >= 4
```

## Test Infrastructure Updates

None — no automated tests for this feature.

## Quality Gates

No code changes — quality gates not applicable.

## Risks

- Format not consumable by Task 003 agent — mitigated by investigation confirming markdown heading format is appropriate (see risk-assessment.md)
- See `comms/outbox/versions/design/v011/006-critical-thinking/risk-assessment.md`

## Commit Message

```
feat: add IMPACT_ASSESSMENT.md with 4 design-time checks (BL-076)
```
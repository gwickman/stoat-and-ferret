# Implementation Plan: windows-dev-guidance

## Overview

Add a "Windows (Git Bash)" section to AGENTS.md documenting the /dev/null vs nul pitfall, with correct and incorrect usage examples. Single file modification.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `AGENTS.md` | Modify | Add Windows (Git Bash) section with /dev/null guidance |

## Test Files

None — manual verification only.

## Implementation Stages

### Stage 1: Add Windows section to AGENTS.md

1. Add a "Windows (Git Bash)" section after the Commands section (after line 46, before Type Stubs):
   - Heading: `## Windows (Git Bash)`
   - Explain that `/dev/null` is correct in Git Bash — MSYS translates it to the Windows null device
   - Warn that bare `nul` creates a literal file named `nul` because MSYS/Git Bash interprets it as a filename
   - Include correct example: `command > /dev/null 2>&1`
   - Include incorrect example: `command > nul` (creates a literal file)
   - Note that `.gitignore` already has a `nul` entry as a safety net

**Verification:**
```bash
# Verify section exists
grep -c "Windows (Git Bash)" AGENTS.md  # Should output 1
# Verify content includes both /dev/null and nul
grep "/dev/null" AGENTS.md
grep "nul" AGENTS.md
```

## Test Infrastructure Updates

None — documentation-only change.

## Quality Gates

No code changes — quality gates not applicable.

## Risks

None — low-risk documentation addition.

## Commit Message

```
docs: add Windows Git Bash /dev/null guidance to AGENTS.md (BL-019)
```
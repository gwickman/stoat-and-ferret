# Process Documentation Amendment

## Change Summary

Added a clarifying note to the Post-Version Retrospective Process documentation to handle cases where the retrospective may already exist.

## File Modified

`docs/auto-dev/PROCESS/draft/post-version-retrospective-process.md`

## Change Details

**Location:** Stage 2: Retrospective Generation (line 77)

**Addition:** Added the following note after the section heading:

> **Note:** If the version retrospective already exists (e.g., generated during version execution), verify it contains all required sections below rather than generating a new one.

## Rationale

This clarification addresses the scenario where a version retrospective might be generated during version execution rather than during the post-version retrospective process. The note instructs Claude Code to verify existing retrospectives against required sections rather than unconditionally generating a new one, preventing duplicate work and ensuring existing documentation is leveraged appropriately.

## Impact

- **Low impact change:** Adds clarification without changing the core process
- **Improves process flexibility:** Handles both fresh generation and verification scenarios
- **Prevents duplication:** Avoids unnecessary regeneration of existing retrospectives

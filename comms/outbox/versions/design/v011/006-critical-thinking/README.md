# 006 Critical Thinking: v011

Reviewed all 7 risks from Task 005's logical design. Investigated 6 via codebase queries, resolving 5 conclusively with evidence. The design is robust — no structural changes required. Key findings: path traversal security is already well-implemented (`Path.resolve()` + `relative_to()` + comprehensive test suite), the `label` field definitively does not exist in any clip data model, and existing frontend patterns provide clear implementation paths for video selection dropdowns and async state management.

## Risks Investigated
- **7 total** from Task 005
- 5 categorized as "Investigate now" — all resolved with evidence
- 2 categorized as "Accept with mitigation" — mitigations documented

## Resolutions
- **Path traversal security (high):** Existing `validate_scan_path()` is robust with 3 layers of protection and thorough test coverage. New endpoint reuses it directly.
- **Label field (medium):** Confirmed non-existent across all data layers (Pydantic, SQLAlchemy, Alembic, Rust). AC drafting error — design correctly drops it.
- **Video selection UX (medium):** 3 existing `<select>` dropdown patterns + `useVideos` hook make simple dropdown straightforward. No scope creep.
- **Empty allowlist (medium):** Definitively resolved — empty = all allowed, documented in code, settings, tests, and LRN-017.
- **IMPACT_ASSESSMENT format (low):** Task 003 agent reads markdown flexibly, gracefully handles absence. Format appropriate.

## Design Changes
- Minor refinements only — no structural changes from Task 005:
  - Corrected `os.path.realpath()` → `Path.resolve()` to match codebase convention
  - Added initial browse path guidance for empty allowlist scenario
  - Documented `<select>` dropdown pattern for video selection
  - Documented `isLoading` guard as race condition mitigation

## Remaining TBDs
- None. All risks resolved or accepted with documented mitigations.

## Confidence Assessment
**High confidence.** All risks investigated to conclusion. The design builds on verified, existing patterns (security validation, Zustand stores, dropdown components, async handlers). No blocking issues found. The v011 scope is well-bounded — 2 new frontend features wiring existing backend functionality plus 3 documentation features. No persistence concerns (no Task 004 persistence-analysis.md, and no new persistent state introduced).

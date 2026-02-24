# Theme: workshop-and-docs-polish

## Goal

Close remaining polish gaps by wiring the transition API into the Effect Workshop GUI and correcting API specification documentation that shows misleading example values. These items address frontend and documentation gaps independently of Theme 01's binding cleanup work.

## Design Artifacts

See `comms/outbox/versions/design/v012/006-critical-thinking/` for full risk analysis.

## Features

| # | Feature | Backlog | Goal |
|---|---------|---------|------|
| 001 | transition-gui | BL-066 | Wire transition effects into the Effect Workshop GUI via the existing backend endpoint |
| 002 | api-spec-corrections | BL-079 | Fix 5 documentation inconsistencies in API spec and manual for job status examples |

## Dependencies

- No cross-theme dependencies with Theme 01
- Feature 001 depends on the existing transition backend endpoint (already functional since v007)
- Feature 002 has no dependencies — documentation-only change
- Features 001 and 002 are fully independent of each other

## Technical Approach

Feature 001 follows existing Effect Workshop patterns: Zustand store for state management, schema-driven parameter forms, and API integration via hooks. The ClipSelector component is extended with optional pair-mode props rather than creating a separate component.

Feature 002 is a documentation-only change updating 5 example values across 2 files to match actual code behavior.

See `comms/outbox/versions/design/v012/004-research/` for codebase patterns and evidence.

## Risks

| Risk | Mitigation |
|------|------------|
| ClipSelector pair-mode UX complexity | Extension adds ~30-40 lines with clear prop API; backend validates adjacency. See 006-critical-thinking/risk-assessment.md |
| Architecture drift from C4 exclusion | Accepted — v012 changes primarily removals; C4 update tracked as BL-069 |
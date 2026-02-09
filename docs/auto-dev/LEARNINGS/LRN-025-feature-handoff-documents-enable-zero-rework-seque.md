## Context

When features within a theme depend on each other, the implementing agent needs to understand integration points, API contracts, and patterns established by previous features.

## Learning

Feature-to-feature handoff documents that explicitly communicate integration points, hook APIs, layout patterns, and component conventions enable subsequent features to plug in without rework. When combined with correct theme sequencing (infrastructure before consumers), this produces zero-rework feature chains.

## Evidence

- v005 Theme 01: Infrastructure → WebSocket → Settings ordering meant each feature built on the previous without rework
- v005 Theme 03: Application shell handoff document communicated WebSocket hook API, layout patterns, and page component conventions to downstream features (dashboard, library, projects)
- v005 Theme 04: Playwright setup handoff document communicated test infrastructure to the E2E test suite feature
- v005 version retrospective: "All 11 features passed quality gates on first iteration" — zero rework across the entire version
- All 58/58 acceptance criteria passed with 0 failures

## Application

- Any multi-feature theme where features have dependencies
- Handoff documents should include: API contracts, integration points, component patterns, naming conventions, and test infrastructure setup
- Combine with correct feature sequencing (foundation → consumers) for maximum effect
- This reinforces LRN-019 (Build Infrastructure First) at the feature level within themes
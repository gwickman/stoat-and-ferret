# Retrospective Insights: v010 → v011

## What Worked Well (Continue in v011)

### Layered Bug-Fix Approach
v010 Theme 01 addressed the async blocking bug with three layers: immediate fix, static analysis gate, runtime regression test. This defense-in-depth pattern should be applied when BL-076 (IMPACT_ASSESSMENT.md) defines design-time checks — the assessment document itself is a prevention layer analogous to the CI gate.

### Protocol-First Design
Updating the Protocol, production implementation, and test double together in each feature kept type checking effective. v011's BL-075 (clip CRUD GUI) will consume existing backend APIs — the design should verify the API contracts match what the frontend expects before implementation begins.

### Full-Stack Feature Delivery
v010 Feature 002 (job cancellation) shipped changes from queue data model through to React frontend cancel button with Vitest coverage. This proves the pipeline can deliver end-to-end features, which is directly relevant to BL-075 (clip CRUD) — another full-stack feature touching API client, React components, and state management.

### Python 3.10 Compatibility Awareness
Using project memory to catch `asyncio.TimeoutError` vs `builtins.TimeoutError` differences early avoided cross-platform CI failures. v011 is primarily GUI and documentation work, but any async code must maintain this awareness.

## What Didn't Work (Avoid in v011)

### Deferred Wiring Creates Compounding Gaps
BL-075 (clip CRUD) was deferred from v005 — 5 versions ago. The backend API has been implemented and tested for months but the frontend never wired up the write endpoints. v011 should not defer any frontend wiring; if a backend endpoint exists, the GUI feature should consume it in the same version.

### Missing .env.example for 9 Versions
BL-071 addresses a gap that existed since v002. Each version that added Settings fields without documenting them in a template compounded the onboarding problem. BL-076's settings documentation check is designed to prevent this pattern from recurring.

### GUI Text-Only Input Where Browse Was Standard
The scan directory feature shipped with text input only (now BL-070). BL-076's GUI input mechanism check addresses this class of UX gap at design time.

## Tech Debt Addressed vs Deferred

### Addressed in v010
- P0 async blocking in ffprobe_video() — fully fixed with async subprocess
- No async CI guardrail — added Ruff ASYNC rules (ASYNC210/221/230)
- No event-loop regression test — added integration test

### Deferred (Relevant to v011)
- **20 pre-existing test skips** — tests requiring ffprobe/ffmpeg binaries; not addressed, carried forward
- **InMemoryJobQueue no-op surface** — test double accumulating stub methods; flagged but not resolved
- **Health check inconsistency** — uses `asyncio.to_thread(subprocess.run)` vs `create_subprocess_exec()` used elsewhere
- **C4 documentation 2 versions behind** — last updated at v008

## Architectural Decisions Informing v011

1. **Backend API completeness** — Clip CRUD endpoints exist and are integration-tested. BL-075 design should reference existing endpoint signatures directly rather than specifying new backend work.
2. **Zustand independent stores** (LRN-037) — New GUI components should follow the established pattern of independent feature stores with clean composition interfaces.
3. **Schema-driven UI** (LRN-032) — BL-075 forms can potentially derive field definitions from backend Pydantic models, maintaining consistency.
4. **Cooperative async patterns** — v010 established `asyncio.Event` for cancellation and `asyncio.create_subprocess_exec` for subprocesses. Any new async code in v011 should follow these patterns.

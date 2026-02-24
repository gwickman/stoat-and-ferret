# Task 003: Impact Assessment — v012

24 impacts identified across all 5 backlog items: 21 small (sub-task scope), 3 substantial (feature scope), 0 cross-version. No impacts require deferral to a future version.

## Generic Impacts

**Documentation review** found 16 impacts across 5 categories:
- **C4 architecture docs** (5 impacts): C4 code and component docs reference execute_command, TimeRange operations, and v006 binding functions that may be removed
- **Stubs and exports** (4 impacts): Both stub files and __init__.py exports must be updated after binding trimming in BL-067 and BL-068
- **Test files** (3 impacts): ~88 parity tests in test_pyo3_bindings.py exercise bindings targeted for removal; benchmarks also affected
- **Design docs** (3 impacts): Security audit, performance benchmarks, and CHANGELOG reference bindings being audited
- **API docs** (2 impacts): API spec and manual both show misleading progress: null for running jobs (BL-079)

## Project-Specific Impacts

Executed all 4 checks from `docs/auto-dev/IMPACT_ASSESSMENT.md`:

- **Async Safety** (1 impact, substantial): execute_command uses blocking subprocess.run via FFmpegExecutor.run(). If BL-061 wires this into an async render workflow, the event loop will block. Requires asyncio.to_thread wrapper or async subprocess replacement.
- **Settings Documentation** (0 impacts): No Settings field changes in v012 scope. .env.example unaffected.
- **Cross-Version Wiring** (2 impacts, small): BL-061 decision affects BL-067/BL-068 scope; BL-066 depends on v007 transition endpoint.
- **GUI Input Mechanisms** (1 impact, substantial): BL-066 transition GUI requires clip-pair selection — current single-clip ClipSelector is insufficient.

## Caller Impact Analysis

- **BL-067/BL-068**: All 11 binding functions (5 from v001, 6 from v006) have zero production callers in src/. Only consumers are parity tests and benchmarks. No caller-adoption risk for removal.
- **BL-061**: execute_command has zero production callers. If wiring, a render/export code path must be identified and updated to call it — otherwise the wiring is ineffective.

## Work Items Generated

- **Small**: 21 items — mostly sub-tasks within BL-067, BL-068, and BL-079 features (stub regeneration, test cleanup, doc updates)
- **Substantial**: 3 items — async safety design for BL-061, clip-pair selector for BL-066, caller wiring for BL-061
- **Cross-version**: 0 items

## Recommendations

1. **BL-061 ordering is critical**: The wire-vs-remove decision must complete before BL-067/BL-068 begin, as it affects what counts as "used." Document the decision rationale explicitly.
2. **BL-061 async safety**: If wiring, design the async integration upfront. Reference the v009 ffprobe incident (IMPACT_ASSESSMENT.md) as precedent.
3. **BL-067/BL-068 stub and test cleanup**: Plan stub regeneration and parity test removal as explicit sub-tasks within each feature — not afterthoughts.
4. **BL-066 clip-pair selection**: Design the transition UX as a distinct mode in the Effect Workshop, with adjacency validation built into the selector component.
5. **BL-079 manual sync**: The API reference manual mirrors the API spec examples — update both together.
6. **C4 drift acknowledgment**: v012 will introduce new C4 architecture drift (removed bindings, new GUI component). This is acceptable given BL-069 is excluded from v012 scope, but should be tracked.

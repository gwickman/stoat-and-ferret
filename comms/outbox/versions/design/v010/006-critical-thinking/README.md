# 006 Critical Thinking — v010 Async Pipeline & Job Controls

Investigated all 7 risks and unknowns from Task 005's logical design. 4 were resolvable via codebase queries and confirmed Task 005's assumptions. 2 are accepted with documented mitigations. 1 is future tech debt (not a v010 concern). The investigation produced one actionable design refinement: Protocol and test double updates must be included in BL-073/BL-074 implementation.

## Risks Investigated

- **7 total risks** from Task 005
- **4 "Investigate now"** — all resolved with empirical evidence
- **2 "Accept with mitigation"** — mitigations documented
- **1 "Future tech debt"** — documented, no v010 action needed

## Resolutions

- **ASYNC violations confirmed**: Only `health.py:96` triggers beyond BL-072 target. Zero ASYNC210/ASYNC230 violations. The "UNVERIFIED" tag from Task 005 is now resolved.
- **asyncio.Event safety confirmed**: `_AsyncJobEntry` only created inside `async def submit()` — event loop always running. Safe for Python 3.10+.
- **InMemoryJobQueue drift resolved**: 8+ test files use `InMemoryJobQueue`. Protocol must be updated; no-op stubs needed on the test double.
- **No additional ASYNC violations**: Full scan of `src/` found zero blocking HTTP or file I/O in async files.

## Design Changes

1. **Added**: `AsyncJobQueue` Protocol updates for `set_progress()` and `cancel()` — explicit requirement in BL-073/BL-074
2. **Added**: `InMemoryJobQueue` no-op stubs for new Protocol methods — prevents test double drift
3. **Added**: Keyword-only parameter specification for `scan_directory()` new parameters
4. **Added**: CI timing mitigation documentation for BL-078's 2-second threshold
5. **Upgraded**: 4 "UNVERIFIED" assumptions from Task 005 → "VERIFIED" with evidence

## Remaining TBDs

- **CI runner timing** (BL-078): 2-second threshold should be generous for in-process ASGI but may need tuning after first CI run. Mitigation: increase to 5 seconds if flaky.
- **executor.py blocking** (future): `subprocess.run()` in executor will need async conversion when render pipeline goes async. Not a v010 concern.

## Confidence Assessment

**HIGH** — All investigable risks resolved with empirical evidence. No design-breaking issues found. The logical design from Task 005 is structurally sound. The only refinement is adding Protocol/test-double updates as explicit implementation steps (a completeness improvement, not a structural change). All 5 backlog items remain fully covered with no deferrals.

## Artifacts

| Document | Description |
|----------|-------------|
| `risk-assessment.md` | Per-risk analysis with investigation, findings, and resolutions |
| `refined-logical-design.md` | Updated logical design incorporating all findings |
| `investigation-log.md` | Detailed log of all codebase queries and evidence |

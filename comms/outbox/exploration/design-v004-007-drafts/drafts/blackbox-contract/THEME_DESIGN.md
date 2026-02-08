# THEME DESIGN — 02: Black Box & Contract Testing

## Goal

Implement end-to-end black box tests, verified fakes for FFmpeg executors, and unified search behavior for test consistency.

## Design Artifacts

- Refined logical design: `comms/outbox/versions/design/v004/006-critical-thinking/refined-logical-design.md` (Theme 02 section)
- Codebase patterns: `comms/outbox/versions/design/v004/004-research/codebase-patterns.md` (FFmpeg Executor, Search Behavior sections)
- External research: `comms/outbox/versions/design/v004/004-research/external-research.md` (§2 Black Box Testing, §4 FFmpeg Contract Testing)
- Test strategy: `comms/outbox/versions/design/v004/005-logical-design/test-strategy.md` (Theme 02 section)
- Risk assessment: `comms/outbox/versions/design/v004/006-critical-thinking/risk-assessment.md` (R3, U3)

## Features

| # | Feature | Backlog | Dependencies |
|---|---------|---------|-------------|
| 1 | blackbox-test-catalog | BL-023 | Theme 01 complete |
| 2 | ffmpeg-contract-tests | BL-024 | Theme 01 complete |
| 3 | search-unification | BL-016 | None |

## Dependencies

- **Upstream**: Theme 01 (fixture factory for blackbox tests, DI for TestClient wiring).
- **Internal**: Features are independent of each other within this theme.
- **External**: BL-024 requires FFmpeg binary for real executor tests (marked `@pytest.mark.requires_ffmpeg`).

## Technical Approach

1. **Black box test catalog** (BL-023): Create `tests/test_blackbox/` directory with `@pytest.mark.blackbox` marker. Tests exercise scan → project → clips through REST API using recording/fake executors. Full DI wiring via `create_app()` with test doubles.
2. **FFmpeg contract tests** (BL-024): Parametrized fixture across Real, Recording, and Fake executors. Add optional `strict=True` parameter to FakeFFmpegExecutor for args verification (U3 resolved). At least 5 representative commands tested.
3. **Search unification** (BL-016): Change InMemory search from substring (`in`) to per-token `startswith` matching. Document 3 known behavioral differences: (a) prefix vs substring, (b) multi-word phrase handling, (c) field scope. Add parity tests.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| R3: FTS5 emulation fidelity | Low (resolved) | Per-token startswith closes primary gap; document known differences |
| U3: FakeFFmpegExecutor args verification | Resolved | Optional strict mode for contract tests |
| FFmpeg not available in CI | Low | `@pytest.mark.requires_ffmpeg` marker; fake executor tests always run |

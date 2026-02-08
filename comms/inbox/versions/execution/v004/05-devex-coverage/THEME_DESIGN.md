# THEME DESIGN — 05: Developer Experience & Coverage

## Goal

Improve developer tooling, testing processes, and coverage infrastructure.

## Design Artifacts

- Refined logical design: `comms/outbox/versions/design/v004/006-critical-thinking/refined-logical-design.md` (Theme 05 section)
- Codebase patterns: `comms/outbox/versions/design/v004/004-research/codebase-patterns.md` (Coverage Exclusions, CI Workflow sections)
- External research: `comms/outbox/versions/design/v004/004-research/external-research.md` (§3 Property-Based Testing)
- Test strategy: `comms/outbox/versions/design/v004/005-logical-design/test-strategy.md` (Theme 05 section)
- Risk assessment: `comms/outbox/versions/design/v004/006-critical-thinking/risk-assessment.md` (R6, R7, R8, U4, U5)

## Features

| # | Feature | Backlog | Dependencies |
|---|---------|---------|-------------|
| 1 | property-test-guidance | BL-009 | None |
| 2 | rust-coverage | BL-010 | None |
| 3 | coverage-gap-fixes | BL-012 | None |
| 4 | docker-testing | BL-014 | None |

## Dependencies

- **Upstream**: None. All features are independent.
- **Internal**: Features are independent of each other.
- **External**: BL-009 requires adding `hypothesis` dev dependency. BL-010 requires `cargo-llvm-cov` tool. BL-014 requires Docker.

## Technical Approach

1. **Property test guidance** (BL-009): Add property test section to feature design templates. Include invariant-first guidance with `hypothesis` examples. Add `hypothesis` to dev dependencies in `pyproject.toml`.
2. **Rust coverage** (BL-010): Configure `cargo-llvm-cov` for Rust workspace. Add CI step on ubuntu-latest + Python 3.12 only. Upload lcov report as artifact. Set threshold (90% target, progressive if baseline < 90%).
3. **Coverage gap fixes** (BL-012): Audit all `pragma: no cover` and `type: ignore` comments. Test or document ImportError fallback code. Review 30+ `type: ignore` comments in stub assignments.
4. **Docker testing** (BL-014): Create multi-stage Dockerfile (Stage 1: Rust toolchain + maturin, Stage 2: Python runtime). Create `docker-compose.yml` for containerized testing. Document Docker-based workflow.

## Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| R6: Rust coverage baseline unknown | Low (resolved) | ~160 tests, likely 75-90%. Progressive threshold if < 90% |
| R7: Docker image complexity | Low | Multi-stage builds; cache Rust compilation layer |
| R8: Hypothesis dependency | Low | Dev dependency only; version pin in pyproject.toml |
| U4: Docker base image selection | TBD | Start with python:3.12-slim + rustup |
| U5: llvm-cov CI integration | Resolved | Standard cargo-llvm-cov pattern on single matrix combo |
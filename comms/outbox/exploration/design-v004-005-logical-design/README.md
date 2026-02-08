# Logical Design — v004: Testing Infrastructure & Quality Verification

Proposed structure for v004: 5 themes containing 15 features total, covering all 13 mandatory backlog items with no deferrals. The design follows a foundation-first execution strategy where the P1 critical path (test doubles → DI → fixture factory) executes sequentially as Theme 01, then remaining themes execute in dependency-aware order. Estimated 85–125 new tests bringing the total from 395 to approximately 500.

## Theme Overview

| # | Theme | Goal | Features | Key Backlog Items |
|---|-------|------|----------|------------------|
| 01 | `01-test-foundation` | Test doubles, DI, fixture factory — the foundation everything else needs | 3 | BL-020, BL-021, BL-022 |
| 02 | `02-blackbox-contract` | End-to-end black box tests, FFmpeg verified fakes, search unification | 3 | BL-023, BL-024, BL-016 |
| 03 | `03-async-scan` | Replace synchronous scan with async job queue pattern | 3 | BL-027 |
| 04 | `04-security-performance` | Rust security audit and hybrid architecture performance benchmarks | 2 | BL-025, BL-026 |
| 05 | `05-devex-coverage` | Property test guidance, Rust coverage, coverage gaps, Docker testing | 4 | BL-009, BL-010, BL-012, BL-014 |

## Key Decisions

1. **BL-027 split into 3 features**: The async scan backlog item is large (new protocol, endpoint changes, doc updates) and split across infrastructure, endpoint, and documentation features within a dedicated theme.

2. **BL-016 grouped with testing, not data layer**: Search unification is primarily a testing consistency concern (InMemory behavior must match FTS5 for test fidelity), so it sits in Theme 02 alongside contract tests rather than being isolated.

3. **Theme 04 has no dependencies on Theme 01**: Security audit and benchmarks are independent verification activities that can execute any time after the foundation. This allows parallel execution.

4. **Theme 05 is all independent features**: DevEx and coverage items have no internal dependencies and no dependencies on other themes. They can fill gaps in the execution schedule.

5. **BL-020 scope reduced**: Research confirmed AsyncInMemoryProjectRepository already exists. Feature scope is deepcopy isolation + seed helpers + InMemoryJobQueue creation (not a full repository implementation).

## Dependencies

**Critical path**: Theme 01 must execute first and in strict order (010→020→030).

```
Theme 01: BL-020 → BL-021 → BL-022 (strict chain)
Theme 02: Requires Theme 01 complete (BL-023 needs BL-022)
Theme 03: Requires Theme 01 feature 010 (BL-027 needs BL-020's InMemoryJobQueue)
Theme 04: No dependencies (can run anytime)
Theme 05: No dependencies (can run anytime)
```

**Recommended execution**: Theme 01 → Theme 02 feature 010 → Theme 03 → remaining Theme 02 → Theme 04 → Theme 05.

**Rationale**: Foundation first, then highest-value consumer (black box tests), then the only API breaking change (async scan), then independent work.

## Risks and Unknowns

Items requiring investigation in Task 006:

| ID | Type | Severity | Summary |
|----|------|----------|---------|
| R1 | Risk | High | Scan API breaking change — confirm no external consumers |
| R2 | Risk | Medium | Deepcopy isolation may slow tests — profile overhead |
| R3 | Risk | Medium | FTS5 emulation fidelity — enumerate non-replicable behaviors |
| R4 | Risk | Medium | Security audit may reveal unbounded remediation work |
| R5 | Risk | Medium | DI migration touches core test conftest — backwards compatibility |
| R6 | Risk | Low | Rust coverage baseline unknown — may be far below 90% target |
| U1 | Unknown | — | Job queue timeout values — need runtime testing |
| U2 | Unknown | — | Benchmark operations — need profiling to select |
| U3 | Unknown | — | FakeFFmpegExecutor args verification design |
| U4 | Unknown | — | Docker base image selection |
| U5 | Unknown | — | llvm-cov CI integration method |

See `risks-and-unknowns.md` for full details with investigation needs and current best guesses.

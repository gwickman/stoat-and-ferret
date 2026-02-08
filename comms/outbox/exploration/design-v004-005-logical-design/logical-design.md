# Logical Design — v004: Testing Infrastructure & Quality Verification

## Version Overview

**Version**: v004
**Goal**: Build comprehensive testing and quality verification infrastructure covering black box testing, recording test doubles, contract tests, and quality verification suite (milestones M1.8–M1.9).
**Scope**: 13 backlog items (4 P1, 5 P2, 4 P3) organized into 5 themes with 15 features.
**Baseline**: v003 completed with 395 tests, 93% Python coverage, 4 themes, 15 features.
**Estimated new tests**: 85–130 (target ~500 total).

## Theme Breakdown

### Theme 01: Test Foundation (`01-test-foundation`)

**Goal**: Establish the core testing infrastructure — test doubles, dependency injection, and fixture factories — that all other themes depend on.

**Rationale**: BL-020→BL-021→BL-022 form the critical dependency chain. Every testing theme requires these primitives. Building them first ensures stable ground for consumers.

| # | Feature | Backlog | Goal | Dependencies |
|---|---------|---------|------|-------------|
| 1 | `010-inmemory-test-doubles` | BL-020 | Add deepcopy isolation and seed helpers to AsyncInMemoryProjectRepository; create InMemoryJobQueue from scratch | None |
| 2 | `020-dependency-injection` | BL-021 | Add optional injectable parameters to create_app() replacing dependency_overrides pattern | 010 |
| 3 | `030-fixture-factory` | BL-022 | Build builder-pattern fixture factory with build() and create_via_api() methods | 020 |

**Key decisions**:
- AsyncInMemoryProjectRepository already exists (codebase-patterns.md) — scope is deepcopy isolation + seed helpers, not a full rewrite
- InMemoryJobQueue is net-new, created alongside BL-020 since BL-027 depends on it
- create_app() gets optional params defaulting to None; production behavior unchanged
- 4 dependency_overrides in conftest.py migrated to create_app() params

### Theme 02: Black Box & Contract Testing (`02-blackbox-contract`)

**Goal**: Implement end-to-end black box test scenarios and verified fakes for FFmpeg executors, plus unify search behavior for test consistency.

**Rationale**: BL-023 consumes the fixture factory (BL-022). BL-024 verifies FFmpeg test doubles used by black box tests. BL-016 ensures InMemory search matches FTS5, critical for test fidelity. All three are testing correctness concerns.

| # | Feature | Backlog | Goal | Dependencies |
|---|---------|---------|------|-------------|
| 1 | `010-blackbox-test-catalog` | BL-023 | Implement core workflow and error handling tests through REST API using test doubles | Theme 01 complete |
| 2 | `020-ffmpeg-contract-tests` | BL-024 | Parametrized tests running same commands against Real, Recording, and Fake executors | None (can run after Theme 01) |
| 3 | `030-search-unification` | BL-016 | Align InMemory search with FTS5 prefix-match semantics for consistent test/prod behavior | None |

**Key decisions**:
- Black box tests go in `tests/test_blackbox/` with `@pytest.mark.blackbox` marker
- Contract tests use verified fakes pattern: parametrized fixture across Real/Recording/Fake
- Search unification uses per-token `startswith` matching to approximate FTS5 without full emulation
- BL-024 tests marked `@pytest.mark.requires_ffmpeg` for CI environments without FFmpeg

### Theme 03: Async Scan Infrastructure (`03-async-scan`)

**Goal**: Replace synchronous blocking scan with async job queue pattern, enabling progress tracking and non-blocking API behavior.

**Rationale**: BL-027 is a structural API change that creates a new endpoint, modifies the scan endpoint contract, and integrates with the lifespan context manager. It depends on InMemoryJobQueue from BL-020 (Theme 01) and is isolated enough to warrant its own theme. The API breaking change needs focused attention.

| # | Feature | Backlog | Goal | Dependencies |
|---|---------|---------|------|-------------|
| 1 | `010-job-queue-infrastructure` | BL-027 (part 1) | Create AsyncJobQueue protocol, asyncio.Queue implementation, and lifespan integration | Theme 01 feature 010 (InMemoryJobQueue) |
| 2 | `020-async-scan-endpoint` | BL-027 (part 2) | Refactor scan endpoint to return job ID, add GET /jobs/{id} status endpoint | 010 |
| 3 | `030-scan-doc-updates` | BL-027 (part 3) | Update API spec, prototype design, architecture, and tech stack docs for async scan | 020 |

**Key decisions**:
- Uses `asyncio.Queue` producer-consumer pattern (not Redis/arq) per research findings
- InMemoryJobQueue executes synchronously for deterministic tests
- Job worker starts/stops in lifespan context manager
- API breaking change: POST /videos/scan returns `{"job_id": "..."}` instead of ScanResponse
- Documentation updates are a separate feature to keep implementation focused

### Theme 04: Security & Performance Verification (`04-security-performance`)

**Goal**: Complete M1.9 quality verification requirements — security audit of Rust sanitization and performance benchmarks validating the hybrid architecture.

**Rationale**: BL-025 and BL-026 are independent verification activities that don't depend on the test infrastructure chain. They produce audit/benchmark artifacts rather than test infrastructure. Grouping them reflects their shared M1.9 origin.

| # | Feature | Backlog | Goal | Dependencies |
|---|---------|---------|------|-------------|
| 1 | `010-security-audit` | BL-025 | Audit Rust path validation, input sanitization, and escape_filter_text for security gaps | None |
| 2 | `020-performance-benchmark` | BL-026 | Benchmark Rust vs Python for 3+ representative operations with documented speedup ratios | None |

**Key decisions**:
- Security audit focuses on known gaps: validate_path lacks path traversal/symlink checks (deferred to Python per code comment at sanitize/mod.rs:206)
- Audit may produce code fixes in Rust or Python — scope includes remediation
- Benchmark creates `benchmarks/` directory with runnable scripts
- Both features produce documentation artifacts in docs/

### Theme 05: Developer Experience & Coverage (`05-devex-coverage`)

**Goal**: Improve developer tooling, testing processes, and coverage infrastructure.

**Rationale**: BL-009, BL-010, BL-012, and BL-014 are independent improvements to developer experience and coverage. None have hard dependencies on the test infrastructure chain. Grouping them avoids polluting the critical path.

| # | Feature | Backlog | Goal | Dependencies |
|---|---------|---------|------|-------------|
| 1 | `010-property-test-guidance` | BL-009 | Add property test section to feature design templates with invariant-first guidance | None |
| 2 | `020-rust-coverage` | BL-010 | Configure llvm-cov for Rust workspace with CI integration and threshold enforcement | None |
| 3 | `030-coverage-gap-fixes` | BL-012 | Review and fix coverage exclusions for ImportError fallback code | None |
| 4 | `040-docker-testing` | BL-014 | Create Dockerfile and docker-compose.yml for containerized testing | None |

**Key decisions**:
- BL-009 adds `hypothesis` to dev dependencies
- BL-010 targets 90% Rust coverage per AGENTS.md but initial baseline is unknown
- BL-012 reviews 30+ `type: ignore` comments and `pragma: no cover` on ImportError
- BL-014 creates Docker environment bypassing Windows Application Control restrictions

## Execution Order

### Phase 1: Foundation (Theme 01)
Execute strictly in order due to dependency chain:
1. `01-test-foundation/010-inmemory-test-doubles` (BL-020)
2. `01-test-foundation/020-dependency-injection` (BL-021)
3. `01-test-foundation/030-fixture-factory` (BL-022)

**Rationale**: Critical path. Every subsequent theme depends on at least one of these.

### Phase 2: Consumers & Independent Work (Themes 02–05)
After Theme 01 completes, remaining themes can execute in parallel or interleaved:

**Recommended order**:
4. `02-blackbox-contract/010-blackbox-test-catalog` (BL-023) — highest-value consumer of Theme 01
5. `03-async-scan/010-job-queue-infrastructure` (BL-027 part 1) — structural foundation for async
6. `03-async-scan/020-async-scan-endpoint` (BL-027 part 2) — depends on 5
7. `03-async-scan/030-scan-doc-updates` (BL-027 part 3) — depends on 6
8. `02-blackbox-contract/020-ffmpeg-contract-tests` (BL-024) — independent
9. `02-blackbox-contract/030-search-unification` (BL-016) — independent
10. `04-security-performance/010-security-audit` (BL-025) — independent
11. `04-security-performance/020-performance-benchmark` (BL-026) — independent
12. `05-devex-coverage/010-property-test-guidance` (BL-009) — independent
13. `05-devex-coverage/020-rust-coverage` (BL-010) — independent
14. `05-devex-coverage/030-coverage-gap-fixes` (BL-012) — independent
15. `05-devex-coverage/040-docker-testing` (BL-014) — independent

**Rationale**: Black box tests (BL-023) are the highest-value deliverable after the foundation — they validate v005 readiness. Async scan (BL-027) is the only API breaking change and benefits from early execution to stabilize the new endpoint. Security, benchmarks, and DevEx are independent and lower risk.

## Backlog Coverage Verification

| Backlog ID | Priority | Theme | Feature |
|------------|----------|-------|---------|
| BL-020 | P1 | 01-test-foundation | 010-inmemory-test-doubles |
| BL-021 | P1 | 01-test-foundation | 020-dependency-injection |
| BL-022 | P1 | 01-test-foundation | 030-fixture-factory |
| BL-023 | P1 | 02-blackbox-contract | 010-blackbox-test-catalog |
| BL-024 | P2 | 02-blackbox-contract | 020-ffmpeg-contract-tests |
| BL-025 | P2 | 04-security-performance | 010-security-audit |
| BL-026 | P3 | 04-security-performance | 020-performance-benchmark |
| BL-027 | P2 | 03-async-scan | 010/020/030 (3 features) |
| BL-009 | P2 | 05-devex-coverage | 010-property-test-guidance |
| BL-010 | P3 | 05-devex-coverage | 020-rust-coverage |
| BL-012 | P3 | 05-devex-coverage | 030-coverage-gap-fixes |
| BL-014 | P2 | 05-devex-coverage | 040-docker-testing |
| BL-016 | P3 | 02-blackbox-contract | 030-search-unification |

All 13 backlog items mapped. No deferrals.

## Research Sources Adopted

| Research Finding | Source | Applied To |
|-----------------|--------|-----------|
| create_app() optional params over dependency_overrides | external-research.md §1 | Theme 01, BL-021 |
| Black box test directory structure with markers | external-research.md §2 | Theme 02, BL-023 |
| Verified fakes pattern for contract testing | external-research.md §4 | Theme 02, BL-024 |
| Invariant-first property testing with Hypothesis | external-research.md §3 | Theme 05, BL-009 |
| asyncio.Queue producer-consumer pattern | external-research.md §5 | Theme 03, BL-027 |
| AsyncInMemoryProjectRepository already exists | codebase-patterns.md §Existing InMemory | Theme 01, BL-020 scope reduction |
| FakeFFmpegExecutor replays by index (contract gap) | codebase-patterns.md §FFmpeg Executor | Theme 02, BL-024 |
| FTS5 vs substring search semantic gap | codebase-patterns.md §Search Behavior | Theme 02, BL-016 |
| validate_path defers traversal to Python | codebase-patterns.md §Rust Sanitization | Theme 04, BL-025 |
| 4 dependency override points in conftest | evidence-log.md §Override Points | Theme 01, BL-021 |
| hypothesis not in dev dependencies | evidence-log.md §Missing Dependencies | Theme 05, BL-009 |

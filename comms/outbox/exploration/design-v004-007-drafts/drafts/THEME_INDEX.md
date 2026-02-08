# THEME INDEX — v004: Testing Infrastructure & Quality Verification

## Theme 01: test-foundation

**Goal:** Establish core testing infrastructure — test doubles, dependency injection, and fixture factories.

**Features:**

- 001-inmemory-test-doubles: Add deepcopy isolation and seed helpers to AsyncInMemoryProjectRepository; create InMemoryJobQueue
- 002-dependency-injection: Add optional injectable parameters to create_app() replacing dependency_overrides pattern
- 003-fixture-factory: Build builder-pattern fixture factory with build() and create_via_api() methods

## Theme 02: blackbox-contract

**Goal:** Implement end-to-end black box tests, verified fakes for FFmpeg executors, and unified search behavior.

**Features:**

- 001-blackbox-test-catalog: Core workflow and error handling tests through REST API using test doubles
- 002-ffmpeg-contract-tests: Parametrized tests across Real, Recording, and Fake executors with args verification
- 003-search-unification: Align InMemory search with FTS5 prefix-match semantics for consistent test/prod behavior

## Theme 03: async-scan

**Goal:** Replace synchronous blocking scan with async job queue pattern.

**Features:**

- 001-job-queue-infrastructure: AsyncJobQueue protocol, asyncio.Queue implementation, and lifespan integration
- 002-async-scan-endpoint: Refactor scan endpoint to return job ID, add GET /jobs/{id} status endpoint
- 003-scan-doc-updates: Update API spec and design docs for async scan pattern

## Theme 04: security-performance

**Goal:** Complete M1.9 quality verification — security audit and performance benchmarks.

**Features:**

- 001-security-audit: Audit Rust path validation, input sanitization, and escape_filter_text for security gaps
- 002-performance-benchmark: Benchmark Rust vs Python for 3+ representative operations with documented speedup ratios

## Theme 05: devex-coverage

**Goal:** Improve developer tooling, testing processes, and coverage infrastructure.

**Features:**

- 001-property-test-guidance: Add property test section to feature design templates with invariant-first guidance
- 002-rust-coverage: Configure llvm-cov for Rust workspace with CI integration and threshold enforcement
- 003-coverage-gap-fixes: Review and fix coverage exclusions for ImportError fallback code
- 004-docker-testing: Create Dockerfile and docker-compose.yml for containerized testing

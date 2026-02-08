# Backlog Details — v004

## Quality Assessment Key

- **Desc**: Description depth (OK = 50+ words with context, THIN = under 50 words)
- **AC**: Acceptance criteria testability (OK = action verbs, WEAK = noun phrases only)
- **UC**: Use case authenticity (FIXED = was formulaic, now updated; OK = authentic)

| ID | Title | Priority | Desc | AC | UC |
|----|-------|----------|------|----|----|
| BL-020 | InMemory test doubles for Projects and Jobs | P1 | OK | OK | FIXED |
| BL-021 | Dependency injection to create_app() | P1 | OK | OK | FIXED |
| BL-022 | Fixture factory with builder pattern | P1 | OK | OK | FIXED |
| BL-023 | Black box test scenario catalog | P1 | OK | OK | FIXED |
| BL-024 | Contract tests with real FFmpeg | P2 | OK | OK | FIXED |
| BL-025 | Security audit of Rust path validation | P2 | OK | OK | FIXED |
| BL-026 | Rust vs Python performance benchmark | P3 | OK | OK | FIXED |
| BL-027 | Async job queue for scan operations | P2 | OK | OK | FIXED |
| BL-009 | Property test guidance in design template | P2 | OK | OK | FIXED |
| BL-010 | Rust code coverage with llvm-cov | P3 | OK | OK | FIXED |
| BL-012 | Fix coverage reporting gaps (ImportError) | P3 | OK | OK | FIXED |
| BL-014 | Docker-based local testing option | P2 | OK | OK | FIXED |
| BL-016 | Unify InMemory vs FTS5 search behavior | P3 | OK | OK | FIXED |

---

## P1 Items (Test Infrastructure Core)

### BL-020 — Implement InMemory test doubles for Projects and Jobs
- **Priority**: P1 | **Size**: L | **Tags**: v004, testing, test-doubles

> The RecordingFFmpegExecutor test double exists from v002, but InMemoryProjectStorage and InMemoryJobQueue are missing. The 07-quality-architecture.md spec requires these test doubles for black box testing (M1.8), but only InMemoryVideoRepository has been implemented. Without these doubles, integration tests cannot run in isolation from real storage and must use the actual database, making tests slow and non-deterministic.

**Acceptance Criteria:**
1. InMemoryProjectStorage implements AsyncProjectRepository protocol with deepcopy isolation
2. InMemoryJobQueue provides synchronous deterministic execution with configurable outcomes
3. Both doubles include seed helpers for populating test data
4. Contract tests verify InMemory behavior matches real SQLite implementations

### BL-021 — Add dependency injection to create_app() for test wiring
- **Priority**: P1 | **Size**: M | **Tags**: v004, testing, dependency-injection

> The `create_app()` factory exists but does not accept injectable dependencies as specified in 07-quality-architecture.md. Tests currently cannot swap in recording or in-memory fakes at the application level. This blocks black box testing (M1.8) because there is no way to wire test doubles into the running FastAPI app without monkey-patching.

**Acceptance Criteria:**
1. create_app() accepts optional executor, repository, and job queue parameters
2. Default behavior unchanged — production uses real implementations when None passed
3. Test mode injects recording/in-memory fakes through the same interface
4. At least one integration test demonstrates the test wiring end-to-end

### BL-022 — Build fixture factory with builder pattern for test data
- **Priority**: P1 | **Size**: M | **Tags**: v004, testing, fixtures

> No builder-pattern fixture factory exists for creating test data. Tests currently construct project and clip objects inline with repetitive setup code. The 07-quality-architecture.md spec requires `with_clip()`, `with_text_overlay()`, `build()`, and `create_via_api()` methods. Without a fixture factory, tests are verbose, inconsistent, and fragile when data models change.

**Acceptance Criteria:**
1. Builder creates test projects with configurable clips and effects via chained methods
2. build() returns domain objects directly for unit tests without HTTP
3. create_via_api() exercises the full HTTP path for black box tests
4. Pytest fixtures use the factory, replacing inline test data construction

### BL-023 — Implement black box test scenario catalog
- **Priority**: P1 | **Size**: M | **Tags**: v004, testing, black-box

> No black box integration tests exist despite the API being stable since v003. The 07-quality-architecture.md spec requires tests that exercise complete workflows through the REST API using real Rust core plus recording fakes. Without these tests, regressions in end-to-end flows (scan -> project -> clips) go undetected until manual testing.

**Acceptance Criteria:**
1. Core workflow test covers scan -> project -> clips flow through REST API
2. Error handling tests cover validation errors and FFmpeg failure scenarios
3. All tests use recording test doubles and never mock the Rust core directly
4. Tests run in CI without FFmpeg installed
5. pytest markers separate black box tests from unit tests

---

## P2 Items (Quality, Security, Async, Process, DevEx)

### BL-024 — Contract tests with real FFmpeg for executor fidelity
- **Priority**: P2 | **Size**: M | **Tags**: v004, testing, ffmpeg, contract

> RecordingFFmpegExecutor and FakeFFmpegExecutor exist from v001-v002, but no tests verify they produce behavior identical to RealFFmpegExecutor. This was explicitly deferred from v001 and is required by M1.9 (quality verification). Without contract tests, recording fakes may silently diverge from real FFmpeg behavior, undermining the validity of all integration tests that rely on them.

**Acceptance Criteria:**
1. Parametrized tests run the same commands against Real, Recording, and Fake executors
2. At least 5 representative FFmpeg commands tested across executor implementations
3. Tests marked with @pytest.mark.requires_ffmpeg for CI environments without FFmpeg
4. Contract violations between fake and real executor fail the test suite

### BL-025 — Security audit of Rust path validation and input sanitization
- **Priority**: P2 | **Size**: M | **Tags**: v004, security, audit

> M1.9 specifies a security review of Rust sanitization covering path traversal, null bytes, and shell injection vectors. The Rust core handles user-provided file paths and filter text (via `escape_filter_text()`), but no formal audit artifact documents what has been reviewed, what attack vectors are covered, and where gaps remain. Without this audit, security coverage is implicit and unverifiable.

**Acceptance Criteria:**
1. Review covers path traversal, null byte injection, and shell injection vectors in Rust core
2. Audit document published in docs/ with findings and coverage assessment
3. Any identified gaps addressed with new tests or code fixes

### BL-027 — Async job queue for scan operations
- **Priority**: P2 | **Size**: M | **Tags**: v004, async, scan

> The scan endpoint blocks the HTTP request until the entire directory scan completes. This was identified as tech debt in the v003 retrospective. For large media directories, scan can take significant time, leaving the client with no progress feedback. The black box test scenario catalog (M1.8) also requires async scan behavior to test job progress workflows.

**Acceptance Criteria:**
1. Scan endpoint returns job ID immediately instead of blocking
2. Job status queryable via GET endpoint with progress information
3. InMemoryJobQueue supports synchronous test execution for deterministic tests
4. Existing scan tests updated to use the async pattern

### BL-009 — Add property test guidance to feature design template
- **Priority**: P2 | **Size**: M | **Tags**: process, testing, proptest, v004

> v001 retrospective suggested writing proptest invariants before implementation as executable specifications. Add guidance to feature design templates encouraging this pattern, along with tracking expected test counts.

**Acceptance Criteria:**
1. Feature design template includes property test section
2. Guidance on writing proptest invariants before implementation
3. Example showing invariant-first design approach
4. Documentation on expected test count tracking

### BL-014 — Add Docker-based local testing option
- **Priority**: P2 | **Size**: S | **Tags**: tooling, docker, process, developer-experience, v004

> v002 retrospective identified that Windows Application Control policies can block local Python testing. A Docker-based option would bypass these restrictions and provide consistent dev environments.

**Acceptance Criteria:**
1. docker-compose.yml with Python + Rust build environment
2. README documents Docker-based testing workflow
3. Tests can run inside container bypassing host restrictions

---

## P3 Items (Benchmarks, Coverage, Cleanup)

### BL-026 — Rust vs Python performance benchmark for core operations
- **Priority**: P3 | **Size**: M | **Tags**: v004, benchmarking, rust

> M1.9 requires benchmarking Rust core operations against pure-Python equivalents to validate the performance justification for the hybrid architecture. No benchmark infrastructure exists. Without measured speedup ratios, the decision to use Rust for timeline math and filter generation lacks empirical backing.

**Acceptance Criteria:**
1. Benchmark script compares Rust vs Python for at least 3 representative operations
2. Results documented with speedup ratios for each operation
3. Benchmark runnable via uv run python benchmarks/ command

### BL-010 — Configure Rust code coverage with llvm-cov
- **Priority**: P3 | **Size**: M | **Tags**: testing, coverage, rust, ci, v004

> v001 retrospective noted Rust code coverage is not tracked. Configure llvm-cov to measure and report Rust test coverage alongside Python coverage.

**Acceptance Criteria:**
1. llvm-cov configured for Rust workspace
2. Coverage reports generated during CI
3. Coverage threshold enforced (e.g., 80%)
4. Coverage visible in CI artifacts or dashboard

### BL-012 — Fix coverage reporting gaps for ImportError fallback
- **Priority**: P3 | **Size**: M | **Tags**: testing, coverage, cleanup, v004

> v001 retrospective noted ImportError fallback code is excluded from coverage. Review all coverage exclusions and ensure they are intentional and documented.

**Acceptance Criteria:**
1. Identify all coverage exclusions in Python code
2. Remove or justify each exclusion
3. ImportError fallback properly tested or documented as intentional exclusion
4. Coverage threshold maintained

### BL-016 — Unify InMemory vs FTS5 search behavior
- **Priority**: P3 | **Size**: S | **Tags**: database, cleanup, testing, consistency, v004

> v002 retrospective noted that InMemoryVideoRepository uses substring match while SQLiteVideoRepository uses FTS5 full-text search. Consider unifying search behavior for consistent testing.

**Acceptance Criteria:**
1. InMemoryVideoRepository uses same search semantics as SQLite FTS5
2. Tests verify consistent behavior across implementations
3. Documentation explains search behavior

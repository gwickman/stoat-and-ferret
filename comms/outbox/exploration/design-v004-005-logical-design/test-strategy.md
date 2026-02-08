# Test Strategy — v004

## Overview

v004 is a testing infrastructure version. Most features produce tests as their primary deliverable. The test strategy organizes requirements by type: unit tests, contract tests, black box (integration) tests, parity tests, and documentation/process tests.

**Baseline**: 395 tests, 93% Python coverage, no Rust coverage tracked.
**Target**: ~500+ tests, maintain 80%+ Python coverage, establish Rust coverage baseline.

## Test Requirements by Feature

### Theme 01: Test Foundation

#### 010-inmemory-test-doubles (BL-020)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Unit | InMemoryJobQueue: submit, status, completion, failure, configurable outcomes | 8–10 |
| Unit | AsyncInMemoryProjectRepository: deepcopy isolation (mutate returned object, verify store unchanged) | 3–5 |
| Unit | Seed helpers: populate test data, verify retrieval | 3–5 |
| Contract | InMemory vs SQLite parity: same operations produce same observable results | 5–8 |

**Key concern**: Deepcopy isolation tests must prove that modifying a returned domain object does not affect the store. This is the primary correctness property for in-memory doubles.

#### 020-dependency-injection (BL-021)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Unit | create_app() with None params uses production defaults | 1–2 |
| Unit | create_app() with injected repos uses provided instances | 2–3 |
| Integration | End-to-end test wiring: create_app(repository=InMemoryRepo()) → TestClient → API call → verify InMemory state | 2–3 |
| Regression | Existing API tests pass unchanged after migration from dependency_overrides | (existing) |

**Key concern**: Backwards compatibility. All existing tests must pass after conftest migration.

#### 030-fixture-factory (BL-022)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Unit | Builder chaining: with_clip(), with_text_overlay(), build() returns correct domain object | 5–8 |
| Unit | build() returns domain objects without HTTP | 2–3 |
| Integration | create_via_api() exercises full HTTP path via TestClient | 2–3 |
| Regression | Existing tests migrated to factory maintain same assertions | (existing) |

**Key concern**: Factory must produce objects that satisfy all existing test assertions. Migration is incremental — old inline patterns continue working.

### Theme 02: Black Box & Contract Testing

#### 010-blackbox-test-catalog (BL-023)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Black box | Core workflow: scan → project → clips through REST API | 3–5 |
| Black box | Error handling: validation errors, FFmpeg failure scenarios | 3–5 |
| Black box | Edge cases: empty scan, duplicate project names, concurrent requests | 3–5 |
| Infrastructure | Pytest marker registration, conftest with full DI wiring | (config) |

**Key concern**: Tests must use recording test doubles and never mock Rust core directly. Tests must run in CI without FFmpeg installed (use recording/fake executors).

**Markers**: `@pytest.mark.blackbox` — all black box tests.

#### 020-ffmpeg-contract-tests (BL-024)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Contract | Parametrized: same 5+ FFmpeg commands against Real, Recording, Fake | 5–8 |
| Contract | Arg verification: Fake replays match recorded args, not just index | 2–3 |
| Contract | Error behavior: all executors handle invalid input consistently | 2–3 |

**Key concern**: Current FakeFFmpegExecutor replays by index without arg verification. Contract tests must expose and fix this gap.

**Markers**: `@pytest.mark.requires_ffmpeg` — tests requiring real FFmpeg binary. `@pytest.mark.contract` — all contract tests.

**Representative commands** (minimum 5 per AC):
1. Version check: `ffmpeg -version`
2. Probe metadata: `ffprobe -v quiet -print_format json -show_streams input.mp4`
3. Trim clip: `ffmpeg -i input.mp4 -ss 0 -t 1 -c copy output.mp4`
4. Scale video: `ffmpeg -i input.mp4 -vf scale=640:480 output.mp4`
5. Apply audio filter: `ffmpeg -i input.mp4 -af volume=0.5 output.mp4`

#### 030-search-unification (BL-016)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Parity | Same search queries against InMemory and SQLite produce same results | 5–8 |
| Unit | InMemory prefix-match: "test" matches "testing" but "est" does not match "testing" | 3–5 |
| Regression | Existing search tests pass with unified behavior | (existing) |

**Key concern**: Changing InMemory from substring to prefix-match may break existing tests that relied on substring behavior. Audit all search-related tests before modifying.

### Theme 03: Async Scan Infrastructure

#### 010-job-queue-infrastructure (BL-027 part 1)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Unit | AsyncJobQueue: submit, poll status, completion, failure, timeout | 5–8 |
| Unit | InMemoryJobQueue: synchronous execution, deterministic results | 3–5 |
| Unit | Lifespan integration: worker starts on startup, cancels on shutdown | 2–3 |

#### 020-async-scan-endpoint (BL-027 part 2)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Integration | POST /videos/scan returns job ID (not ScanResponse) | 1–2 |
| Integration | GET /jobs/{id} returns status, progress, and result when complete | 2–3 |
| Integration | Job failure returns error status with message | 1–2 |
| Black box | Full async workflow: scan → poll → complete | 2–3 |
| Regression | Existing scan tests updated to async pattern | (modified) |

**Key concern**: API breaking change. All existing scan tests must be migrated. New tests verify both happy path and failure modes.

#### 030-scan-doc-updates (BL-027 part 3)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| (none) | Documentation-only feature — no new tests | 0 |

### Theme 04: Security & Performance Verification

#### 010-security-audit (BL-025)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Security | Path traversal: `../`, `..\\`, encoded variants against validate_path | 3–5 |
| Security | Null byte injection: `\x00` in paths and filter text | 2–3 |
| Security | Shell injection: backticks, $(), pipes in filter text | 2–3 |
| Security | Symlink following: path resolves through symlinks | 1–2 |
| Security | Whitelist bypass: invalid codec/preset/format values | 2–3 |

**Key concern**: validate_path currently only checks empty and null bytes. Audit must determine whether Python-layer validation is sufficient or Rust needs enhancement.

#### 020-performance-benchmark (BL-026)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Benchmark | Rust vs Python: at least 3 representative operations | 3–5 |
| (none) | Benchmark scripts are not pytest tests — runnable via `uv run python benchmarks/` | — |

**Representative operations** (TBD at implementation, candidates):
1. Timeline position arithmetic (frame-accurate math)
2. Filter string generation/escaping
3. Path validation/sanitization

### Theme 05: Developer Experience & Coverage

#### 010-property-test-guidance (BL-009)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Example | Property test example in template showing invariant-first approach | 1–2 |
| (none) | Primarily a documentation/template feature | — |

**Dependency**: `hypothesis` must be added to dev dependencies in pyproject.toml.

#### 020-rust-coverage (BL-010)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| CI | llvm-cov generates coverage report for Rust workspace | (CI config) |
| CI | Coverage threshold enforced (target 90% per AGENTS.md) | (CI config) |

**Key concern**: Initial Rust coverage baseline is unknown. May need to adjust threshold if starting significantly below 90%.

#### 030-coverage-gap-fixes (BL-012)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Unit | ImportError fallback path exercised (e.g., by mocking import failure) | 2–3 |
| Audit | Review all `pragma: no cover` and `type: ignore` for justification | (review) |

#### 040-docker-testing (BL-014)

| Test Type | Description | Est. Count |
|-----------|-------------|------------|
| Integration | docker-compose up runs test suite successfully | 1 (manual) |
| (none) | Docker configuration, not test code | — |

## Pytest Marker Summary

| Marker | Purpose | Registered |
|--------|---------|-----------|
| `slow` | Long-running tests | Yes (existing) |
| `api` | API-level tests | Yes (existing) |
| `contract` | Contract tests (executor parity) | Yes (existing) |
| `blackbox` | Black box end-to-end tests | No — add in BL-023 |
| `requires_ffmpeg` | Tests needing real FFmpeg | No — register in BL-024 |
| `benchmark` | Performance benchmarks | No — add in BL-026 |

## CI Impact

| Change | Feature | Description |
|--------|---------|-------------|
| New markers | BL-023, BL-024, BL-026 | Register in pyproject.toml |
| llvm-cov step | BL-010 | Add Rust coverage to CI workflow |
| Docker job | BL-014 | Optional Docker-based test job |
| Marker separation | BL-023 | Consider `pytest -m "not blackbox"` for fast CI, full run on PR |

## Estimated Test Count Summary

| Theme | New Tests | Modified Tests |
|-------|-----------|---------------|
| 01-test-foundation | 25–40 | 4+ (conftest migration) |
| 02-blackbox-contract | 20–35 | search tests |
| 03-async-scan | 15–25 | all scan tests |
| 04-security-performance | 15–20 | — |
| 05-devex-coverage | 3–5 | coverage exclusions |
| **Total** | **78–125** | **varies** |

**Projected total**: 395 + ~100 = ~495 tests.

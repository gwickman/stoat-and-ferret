# Risks and Unknowns — v004

This document feeds directly into Task 006 (Critical Thinking) for risk review.

## Risks

### R1: Scan API Breaking Change (BL-027)

- **Severity**: High
- **Description**: POST /videos/scan changes from synchronous ScanResponse to returning a job ID. This is the only API breaking change in v004 and affects all existing scan consumers and tests.
- **Impact**: All existing scan tests must be rewritten. Any external consumers of the scan endpoint break.
- **Mitigation**: v004 is pre-v1.0; this is expected API evolution. Document the change clearly. Migrate all tests in the same feature.
- **Investigation needed**: Confirm no external consumers exist beyond the test suite and future GUI (v005).

### R2: Deepcopy Isolation Performance (BL-020)

- **Severity**: Medium
- **Description**: Adding deepcopy to AsyncInMemoryProjectRepository for test isolation may slow test execution if project objects are large or deeply nested.
- **Impact**: Test suite performance degradation.
- **Mitigation**: Profile deepcopy overhead with realistic test data. Consider shallow copy or copy.copy if deep nesting is unnecessary.
- **Investigation needed**: Measure performance impact of deepcopy on project domain objects.

### R3: FTS5 Emulation Fidelity (BL-016)

- **Severity**: Medium
- **Description**: Replacing InMemory substring search with FTS5-like prefix matching requires a design decision — simple per-token `startswith` vs full FTS5 emulation. Imperfect emulation may still produce inconsistent test/prod behavior.
- **Impact**: Tests using InMemory search may not catch bugs that only appear with real FTS5.
- **Mitigation**: Use per-token `startswith` as a pragmatic approximation. Document known differences. Contract/parity tests catch remaining gaps.
- **Investigation needed**: Enumerate FTS5 behaviors that cannot be replicated in pure Python and assess whether they matter for test fidelity.
- **Current best guess**: Per-token `startswith` covers 90%+ of real usage patterns.

### R4: Security Audit Scope Creep (BL-025)

- **Severity**: Medium
- **Description**: Security audit may reveal gaps requiring code fixes in both Rust and Python. The audit is scoped as a review + document, but remediation work is unbounded.
- **Impact**: Feature may expand significantly if critical vulnerabilities are found.
- **Mitigation**: Audit produces findings document first. Critical fixes done in-feature. Non-critical gaps logged as new backlog items.
- **Investigation needed**: Pre-assess validate_path gap severity — is Python-layer path traversal protection currently adequate?
- **Current best guess**: Path traversal is partially handled by Python (API validates against configured root), but this needs verification.

### R5: Existing Test Breakage from DI Migration (BL-021)

- **Severity**: Medium
- **Description**: Migrating from `dependency_overrides` to `create_app()` parameters touches the core test conftest. All API tests depend on the `client` fixture.
- **Impact**: Incorrect migration breaks the entire API test suite.
- **Mitigation**: Migration must be backwards compatible. Test the conftest changes against all existing tests before proceeding.
- **Investigation needed**: None — well-understood from codebase-patterns.md. 4 override points clearly identified.
- **Current best guess**: Low risk if migration is careful. The 4 override points are well-documented.

### R6: Rust Coverage Baseline Unknown (BL-010)

- **Severity**: Low
- **Description**: AGENTS.md specifies 90% Rust coverage minimum, but no coverage is currently tracked. Initial baseline may be far below 90%.
- **Impact**: Either the threshold needs adjusting or additional Rust tests are needed (unscoped work).
- **Mitigation**: Measure baseline first. If significantly below 90%, document the gap and set a progressive threshold.
- **Investigation needed**: Run llvm-cov locally to determine current Rust test coverage.
- **Current best guess**: Rust code has good test coverage from v001–v003, likely 70–85% range.

### R7: Docker Image Complexity (BL-014)

- **Severity**: Low
- **Description**: A Docker image combining Python 3.10+, Rust toolchain, maturin, and FFmpeg may be large and slow to build.
- **Impact**: Developer experience improvement may be offset by long Docker build times.
- **Mitigation**: Use multi-stage builds. Cache Rust compilation layer. Consider pre-built base image.
- **Investigation needed**: Estimate build time and image size for the combined toolchain.
- **Current best guess**: 2–5 minute build, 2–4 GB image. Acceptable for a local testing option.

### R8: Hypothesis Dependency Addition (BL-009)

- **Severity**: Low
- **Description**: BL-009 requires adding `hypothesis` to dev dependencies. This is the first property testing library in the project.
- **Impact**: Minimal — dev dependency only, no production impact.
- **Mitigation**: Add as dev dependency with version pin.
- **Investigation needed**: None.

## Unknowns

### U1: Job Queue Timeout Values (BL-027)

- **Description**: Appropriate timeout values for scan jobs are unknown without runtime testing with real media directories.
- **Investigation needed**: Test with directories of varying sizes (10, 100, 1000 files) to determine reasonable defaults.
- **Current best guess**: 5-minute default timeout, configurable per-job.

### U2: Benchmark Baseline Operations (BL-026)

- **Description**: Which 3+ operations best demonstrate Rust vs Python performance differences needs to be determined at implementation time.
- **Investigation needed**: Profile candidate operations to identify those with measurable speedup.
- **Current best guess**: Timeline math (frame arithmetic), filter string escaping, path validation are good candidates.

### U3: FakeFFmpegExecutor Args Verification Design (BL-024)

- **Description**: Current FakeFFmpegExecutor replays by sequential index, ignoring command args. The contract test design needs to decide how to verify args match between recording and replay.
- **Investigation needed**: Determine whether to modify FakeFFmpegExecutor to verify args or to test arg matching externally in contract tests.
- **Current best guess**: Modify FakeFFmpegExecutor to optionally verify args match the recording, with a strict mode for contract tests.

### U4: Docker Base Image Selection (BL-014)

- **Description**: The exact Docker base image combining Python 3.10+ and Rust toolchain needs to be determined.
- **Investigation needed**: Evaluate `python:3.12-slim` + `rustup` vs pre-built Rust+Python images.
- **Current best guess**: `python:3.12-slim` with rustup install in Dockerfile is the most portable approach.

### U5: llvm-cov CI Integration Method (BL-010)

- **Description**: How llvm-cov integrates with the existing CI workflow (separate job vs existing test job, artifact storage) needs design.
- **Investigation needed**: Review GitHub Actions for llvm-cov integration patterns.
- **Current best guess**: Separate CI step in the existing test job, with coverage report uploaded as artifact.

## Summary for Task 006

| ID | Type | Severity | Needs Investigation |
|----|------|----------|-------------------|
| R1 | Risk | High | Confirm no external scan consumers |
| R2 | Risk | Medium | Profile deepcopy overhead |
| R3 | Risk | Medium | Enumerate FTS5 behaviors not replicable in Python |
| R4 | Risk | Medium | Pre-assess validate_path gap severity |
| R5 | Risk | Medium | None (well-understood) |
| R6 | Risk | Low | Run llvm-cov locally for baseline |
| R7 | Risk | Low | Estimate Docker build time |
| R8 | Risk | Low | None |
| U1 | Unknown | — | Runtime testing with real media dirs |
| U2 | Unknown | — | Profile candidate benchmark operations |
| U3 | Unknown | — | Design args verification approach |
| U4 | Unknown | — | Evaluate Docker base images |
| U5 | Unknown | — | Review llvm-cov CI patterns |

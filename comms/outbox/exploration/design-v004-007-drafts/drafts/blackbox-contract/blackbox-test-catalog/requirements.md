# Requirements — blackbox-test-catalog

## Goal

Implement core workflow and error handling tests through REST API using test doubles.

## Background

No black box integration tests exist despite the API being stable since v003. The `07-quality-architecture.md` spec requires tests exercising complete workflows through the REST API using real Rust core plus recording fakes. Without these tests, regressions in end-to-end flows go undetected until manual testing. Depends on Theme 01 (fixture factory for test data, DI for TestClient wiring).

## Functional Requirements

| ID | Requirement | Backlog |
|----|-------------|---------|
| FR-1 | Core workflow test covers scan → project → clips flow through REST API | BL-023 |
| FR-2 | Error handling tests cover validation errors and FFmpeg failure scenarios | BL-023 |
| FR-3 | All tests use recording test doubles and never mock the Rust core directly | BL-023 |
| FR-4 | Tests run in CI without FFmpeg installed (use recording/fake executors) | BL-023 |
| FR-5 | `@pytest.mark.blackbox` marker separates black box tests from unit tests | BL-023 |
| FR-6 | Edge case tests cover empty scan, duplicate project names, concurrent requests | BL-023 |

## Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-1 | Black box tests use TestClient with `create_app()` injecting test doubles |
| NFR-2 | No direct imports from internal modules — only REST API calls |
| NFR-3 | `blackbox` marker registered in `pyproject.toml` |

## Out of Scope

- Performance testing of black box scenarios — that's BL-026
- Testing with real FFmpeg — that's BL-024 contract tests
- GUI interaction testing — that's v005

## Test Requirements

| Type | Description | Est. Count |
|------|-------------|------------|
| Black box | Core workflow: scan → project → clips through REST API | 3–5 |
| Black box | Error handling: validation errors, FFmpeg failure scenarios | 3–5 |
| Black box | Edge cases: empty scan, duplicate project names, concurrent requests | 3–5 |
| Infrastructure | Pytest marker registration, conftest with full DI wiring | (config) |

# C4 Component Level: Test Infrastructure

## Overview
- **Name**: Test Infrastructure
- **Description**: Comprehensive Python test suite covering unit, integration, contract, black-box, security, property-based, and PyO3 binding parity testing
- **Type**: Library
- **Technology**: Python, pytest, pytest-asyncio, Hypothesis, FastAPI TestClient

## Purpose

The Test Infrastructure provides thorough validation of all Python backend components. It is organized into specialized test suites: root-level unit tests for repositories, models, FFmpeg, WebSocket, and Rust binding parity (including audio/transition builders); API endpoint tests using TestClient with in-memory doubles; black-box E2E tests exercising complete workflows through HTTP; contract tests ensuring test doubles faithfully match production implementations; security tests for input sanitization and path traversal; job queue lifecycle tests; test double validation; and property-based tests using Hypothesis.

In v008, the root test suite expanded to cover structured logging startup configuration (`test_logging_startup.py`), database initialization during application lifespan (`test_database_startup.py`), and verification that previously orphaned settings (`debug`, `ws_heartbeat_interval`) are now wired to their consumers (`test_orphaned_settings.py`). Audio builder parity (`test_audio_builders.py`) and transition builder parity (`test_transition_builders.py`) were added alongside the existing PyO3 binding tests.

The test infrastructure establishes key patterns used across all suites: contract testing parametrized over implementations, the recording/replay pattern for FFmpeg testing, fluent test data builders (factories), and dependency injection via `create_app()` kwargs.

## Software Features
- **Repository Contract Tests**: Parametrized tests ensuring SQLite and InMemory implementations behave identically
- **API Endpoint Tests**: 180 tests covering all REST endpoints including effects CRUD and transitions
- **Black-Box E2E Tests**: 60 tests exercising complete workflows through HTTP
- **FFmpeg Contract Tests**: Record/replay parity tests for Real/Recording/Fake executors
- **Security Tests**: 32 tests for shell injection, null bytes, path traversal, whitelist bypass
- **Job Queue Tests**: 14 tests for async job lifecycle, timeout, worker cancellation
- **Test Double Validation**: 29 tests for deepcopy isolation, seed helpers, configurable outcomes
- **PyO3 Binding Parity**: ~154 tests verifying all Rust types, plus ~42 audio builder and ~46 transition builder parity tests
- **Property-Based Tests**: Hypothesis-driven invariant testing for Video and Clip models
- **Import Fallback Tests**: Graceful degradation when Rust extension unavailable
- **Test Factories**: Fluent builders for Video, Project, and Clip test data
- **Startup Integration Tests**: Validate structured logging and database initialization during lifespan
- **Orphaned Settings Tests**: Verify `debug` and `ws_heartbeat_interval` settings are consumed by their intended components

## Code Elements

This component contains:
- [c4-code-tests.md](./c4-code-tests.md) -- Root tests: conftest, factories, repo contracts, models, FFmpeg, WebSocket, logging, PyO3 bindings, audio/transition parity, startup integration, orphaned settings (~532 tests)
- [c4-code-tests-test-api.md](./c4-code-tests-test-api.md) -- API endpoint tests with TestClient (180 tests)
- [c4-code-tests-test-blackbox.md](./c4-code-tests-test-blackbox.md) -- Black-box E2E workflow tests (60 tests)
- [c4-code-tests-test-contract.md](./c4-code-tests-test-contract.md) -- FFmpeg executor and repository parity tests (37 tests)
- [c4-code-tests-test-coverage.md](./c4-code-tests-test-coverage.md) -- Import fallback tests for Rust extension (6 tests)
- [c4-code-tests-test-jobs.md](./c4-code-tests-test-jobs.md) -- AsyncioJobQueue and worker lifecycle tests (14 tests)
- [c4-code-tests-test-doubles.md](./c4-code-tests-test-doubles.md) -- In-memory repository isolation and seed tests (29 tests)
- [c4-code-tests-test-security.md](./c4-code-tests-test-security.md) -- Input sanitization and path validation tests (32 tests)
- [c4-code-tests-examples.md](./c4-code-tests-examples.md) -- Hypothesis property-based test templates (4 tests)

## Interfaces

### Test Execution
- **Protocol**: pytest CLI
- **Operations**:
  - `uv run pytest` -- Run all tests
  - `uv run pytest -m blackbox` -- Black-box tests only
  - `uv run pytest -m contract` -- Contract tests only
  - `uv run pytest -m property` -- Property-based tests only

### Test Factories
- **Operations**:
  - `make_test_video(**kwargs) -> Video`
  - `ProjectFactory().with_clip().build()`
  - `ApiFactory(client, repo).project().with_clip().create()`

## Dependencies

### Components Used
- **API Gateway**: Tested via TestClient HTTP requests
- **Application Services**: Tested directly (scan, FFmpeg, jobs)
- **Data Access Layer**: Repository implementations tested with contract pattern
- **Python Bindings Layer**: PyO3 binding verification and fallback testing
- **Rust Core Engine**: Indirectly tested through Python bindings

### External Systems
- **pytest**: Test framework and runner
- **pytest-asyncio**: Async test support (asyncio_mode="auto")
- **Hypothesis**: Property-based testing strategies
- **FastAPI TestClient**: HTTP client for API testing

## Component Diagram

```mermaid
C4Component
    title Component Diagram for Test Infrastructure

    Container_Boundary(tests, "Test Infrastructure") {
        Component(root_tests, "Root Tests", "Python/pytest", "Repos, models, FFmpeg, WebSocket, bindings, audio/transition parity, startup, orphaned settings (~532)")
        Component(api_tests, "API Tests", "Python/pytest", "REST endpoint tests with TestClient (180)")
        Component(blackbox, "Black-Box Tests", "Python/pytest", "E2E workflow tests via HTTP (60)")
        Component(contract, "Contract Tests", "Python/pytest", "FFmpeg executor and repo parity (37)")
        Component(security, "Security Tests", "Python/pytest", "Sanitization, path traversal (32)")
        Component(jobs_tests, "Job Queue Tests", "Python/pytest", "Async queue lifecycle (14)")
        Component(doubles_tests, "Test Double Tests", "Python/pytest", "Isolation, seeds, outcomes (29)")
        Component(coverage_tests, "Fallback Tests", "Python/pytest", "Import fallback stubs (6)")
        Component(examples, "Property Tests", "Python/Hypothesis", "Invariant-driven templates (4)")
    }

    Rel(api_tests, root_tests, "uses factories from")
    Rel(blackbox, root_tests, "uses factories from")
    Rel(doubles_tests, root_tests, "validates test doubles used by")
```

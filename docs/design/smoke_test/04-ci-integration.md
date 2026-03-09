# Smoke Test CI Integration

## GitHub Actions Job Definition

Add the following job to `.github/workflows/ci.yml`:

```yaml
  smoke-tests:
    name: Smoke Tests
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.12"]  # Only latest Python for smoke tests
      fail-fast: false
    needs: []  # Runs in parallel with other jobs
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Set up FFmpeg
        uses: AnimMouse/setup-ffmpeg@v1

      - name: Set up Rust
        uses: dtolnay/rust-toolchain@stable

      - name: Install uv
        uses: astral-sh/setup-uv@v3

      - name: Install dependencies
        run: uv sync

      - name: Build Rust extension
        run: uv run maturin develop

      - name: Run smoke tests
        run: uv run pytest tests/smoke/ -v --timeout=120 --tb=short
        timeout-minutes: 5
```

## Quality Gate Ordering

Smoke tests run as a **separate job** in CI, not within the existing pytest invocation. The full quality gate ordering is:

```
1. ruff check + format       (Python lint)
2. mypy                      (Python types)
3. pytest tests/             (Python unit + integration, all Python versions)
4. pytest tests/smoke/       (smoke tests, Python 3.12 only)        ← NEW
5. cargo clippy + test       (Rust lint + tests)
6. tsc + vitest              (Frontend types + tests)
7. playwright                (browser E2E, Phase 2 — future)
8. ci-status                 (gate job, required for branch protection)
```

### Why a Separate Job

1. **Different test scope.** The existing `pytest tests/` job runs unit and integration tests with mocked dependencies (in-memory repositories, recording fakes). Smoke tests use real infrastructure — real SQLite, real Rust core, real video files.

2. **Reduced matrix.** Smoke tests only need Python 3.12. They test API behavior, not Python-version-specific logic. The unit test matrix already covers Python 3.10, 3.11, and 3.12.

3. **Independence.** During initial development, smoke test failures should not block the main test suite. Once stable, the `ci-status` gate job can be updated to depend on `smoke-tests`.

## Timeout Strategy

Three layers of timeout protection:

| Layer | Mechanism | Value | Purpose |
|-------|-----------|-------|---------|
| **Per-test** | `--timeout=120` (pytest-timeout) | 120 seconds | Catch hung individual tests |
| **Polling** | `poll_job_until_terminal(timeout=30)` | 30 seconds | Catch hung background jobs |
| **Job-level** | `timeout-minutes: 5` (GitHub Actions) | 5 minutes | Catch fixture-level hangs, CI infra issues |

The per-test timeout of 120 seconds is generous. Most tests complete in under 10 seconds. The scan operation on 6 small videos (~45 MB total) completes in 2-5 seconds. The generous timeout accounts for slow CI runners and filesystem contention.

## Flakiness Mitigation

### 1. No Shared State

Each test uses its own temporary SQLite database (via `tmp_path`) and creates its own data. No test reads or writes state created by another test. This eliminates the most common source of test flakiness — hidden inter-test dependencies.

### 2. Deterministic Polling

Tests use the `poll_job_until_terminal()` helper with a configurable timeout, not fixed `sleep()` calls. Tests complete as fast as the operation allows. Polling interval is 0.5 seconds by default — frequent enough for responsive tests, infrequent enough to avoid CPU waste.

### 3. Race Condition Handling (UC-12)

The cancel scan test (UC-12) explicitly handles the race between scan completion and cancellation:

- If the cancel arrives while the scan is running → 200 (cancelled)
- If the scan completed before the cancel → 409 (already terminal)

The test accepts either outcome. Both are valid, and neither indicates a bug.

### 4. No WebSocket Timing Dependencies

Phase 1 uses HTTP polling for all asynchronous operations. WebSocket events are timing-sensitive and would introduce flakiness if used for assertions. WebSocket testing is deferred to Phase 2 (Playwright), which has built-in support for waiting on WebSocket messages.

### 5. Retry Policy (Optional)

If flakiness is observed after deployment, add `pytest-rerunfailures`:

```yaml
run: uv run pytest tests/smoke/ -v --timeout=120 --tb=short --reruns 1
```

This is not recommended initially. Flaky tests should be investigated and fixed, not papered over with retries.

## Whether to Run in Same pytest Invocation

**Decision: No — separate job.**

Rationale:
- The existing `pytest tests/` invocation uses `--cov=src --cov-fail-under=80` for coverage enforcement. Smoke tests would pollute coverage numbers (they cover the full stack, inflating coverage for modules that should demonstrate unit-level coverage).
- Smoke tests require `maturin develop` and real video files. The unit test job may not have the Rust toolchain available on all matrix entries.
- Separate jobs allow independent failure modes. A smoke test failure is a different signal than a unit test failure.

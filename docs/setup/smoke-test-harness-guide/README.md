# Test Harness Design

**Project:** stoat-and-ferret — AI-driven video editor with hybrid Python/Rust architecture

## Overview

The test harness provides two layers of end-to-end testing:

1. **Smoke tests** (API-level) — Fast, in-process tests that exercise the full backend stack: FastAPI endpoints, Python services, Rust core (via PyO3), SQLite database, and real video files. They validate API contracts, request/response schemas, and end-to-end behaviour from HTTP request through to Rust-level processing. Sub-10 seconds for the full suite.

2. **UAT journeys** (browser-level) — Playwright-based Python scripts that drive a real browser against a live server, validating complete user workflows: navigating pages, clicking buttons, filling forms, and verifying GUI rendering. Each journey produces timestamped screenshot evidence and structured pass/fail reports.

**When to use which:**
- Run **smoke tests** as the fast inner loop during development and in CI. They catch API regressions, schema mismatches, and Rust core integration issues without needing a browser.
- Run **UAT journeys** as the outer end-to-end validation before releases, after major GUI changes, or to verify the full user experience. They catch rendering bugs, navigation issues, and data-testid/component breakage that API tests cannot detect.

For full UAT details (how to run, interpret results, troubleshoot failures), see [`docs/manual/uat-testing.md`](../../manual/uat-testing.md).

## Relationship to Existing Quality Gates

The project has comprehensive per-layer quality gates:

| Layer | Tool | What it covers |
|-------|------|----------------|
| Python lint/format | ruff | Code style, import ordering, common bugs |
| Python types | mypy | Static type checking across the Python layer |
| Python tests | pytest | Unit + integration tests with mocked dependencies |
| Frontend types | TypeScript (`tsc`) | Static type checking for React/TypeScript |
| Frontend tests | Vitest | Component and hook unit tests |
| Rust lint | clippy | Rust-specific linting |
| Rust tests | cargo test + proptest | Pure function testing, property-based testing |

**The gap:** None of these test the full stack together. A broken database migration, a misconfigured PyO3 binding, or a schema mismatch between API and Rust core would pass all existing tests but fail in production.

Smoke tests close this gap at the API level. UAT journeys extend coverage to the browser, verifying that the React GUI correctly renders data from the full backend stack.

## Testing Tiers

### Tier 1: Core API Smoke Tests — Implemented (v014)

- **Technology:** `httpx.AsyncClient` with `ASGITransport`, running in-process via pytest
- **Scope:** Core API endpoints exercised through 12 use cases (UC-01 to UC-12)
- **Speed:** Sub-10 seconds for the full suite
- **Dependencies:** Zero new dependencies (httpx and pytest-asyncio already installed)
- **Confidence:** Validates full backend stack including Rust core; does not test browser rendering
- **Test files:** 8 files covering scan, library, project CRUD, clip CRUD, effects, transitions, health

### Tier 2: Expanded API Coverage — Implemented (v018–v019)

- **Scope:** Timeline CRUD, composition layouts, audio mixing, batch operations, version management, filesystem browsing, video detail/thumbnail/delete, and negative-path validation
- **Test files:** 7 additional files (test_timeline.py, test_compose.py, test_audio.py, test_batch.py, test_versions.py, test_filesystem.py, test_negative_paths.py) plus extensions to existing test_library.py
- **Helpers:** New `create_adjacent_clips_timeline()` helper and `create_version_repo()` factory in conftest.py

### Tier 3: UAT Journeys (Playwright browser E2E) — Implemented (v022)

- **Technology:** Playwright for Python, driven by `uat_runner.py`
- **Scope:** 4 journey scripts (J201–J204) exercising the React GUI end-to-end
- **Mode:** Headed (visible browser for debugging) or headless (CI/quick validation)
- **Evidence:** Timestamped screenshots, structured JSON/Markdown reports, server logs
- **Dependencies:** `playwright` (optional `[uat]` dependency group), Chromium browser binary
- **Test files:** `scripts/uat_runner.py`, `scripts/uat_journey_201.py` through `uat_journey_204.py`, `scripts/seed_sample_project.py`

## Current Status

Tier 1 (core API smoke tests) is **implemented** as of v014. Tier 2 (expanded API coverage) is **implemented** as of v019. Tier 3 (UAT journeys) is **implemented** as of v022, with all 4 journeys (J201–J204) passing in both headed and headless modes.

## Files in This Folder

| File | Contents |
|------|----------|
| [01-background.md](./01-background.md) | Testing gap analysis, two-tier rationale, GUI state, video metadata |
| [02-infrastructure.md](./02-infrastructure.md) | Smoke test file layout, conftest.py design, fixtures, helpers; UAT runner architecture |
| [03-test-cases.md](./03-test-cases.md) | Smoke test case specifications; UAT journey summaries |
| [04-ci-integration.md](./04-ci-integration.md) | GitHub Actions jobs for smoke tests and UAT |
| [05-maintenance.md](./05-maintenance.md) | Trigger tables, sync strategy, impact assessment checks for both tiers |
| [06-phase2-playwright.md](./06-phase2-playwright.md) | Playwright UAT harness — design origin and realisation |

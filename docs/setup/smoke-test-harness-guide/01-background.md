# Test Harness Background

## The Testing Gap

stoat-and-ferret has comprehensive per-layer tests:

- **Rust core:** Pure function unit tests and property-based tests via `proptest`. Timeline math, clip validation, filter builders, and input sanitization all have deterministic test coverage.
- **Python backend:** Unit tests with mocked repositories (recording fakes, fixture factories). Integration tests verify API router wiring with in-memory test doubles.
- **React frontend:** Vitest component tests verify rendering, state management (Zustand stores), and hook behavior.

**What is not tested by unit/integration tests:** No existing test exercises the full request lifecycle:

```
HTTP Client → FastAPI Router → Service Layer → Rust Core (PyO3) → SQLite Database
```

A broken `maturin develop` build, a schema mismatch between Pydantic models and database columns, or a misconfigured PyO3 binding would pass every existing test but fail at runtime.

## Two-Tier Testing Approach

The project addresses this gap with two complementary tiers:

1. **Smoke tests (API-level, fast inner loop):** In-process `httpx` tests that exercise the full backend stack without a browser. They run in under 10 seconds, require no browser binaries, and catch API contract regressions, schema mismatches, and Rust core integration failures. These are the first line of defence — run on every CI push and during local development.

2. **UAT journeys (browser-level, outer validation):** Playwright-based Python scripts that drive a real Chromium browser against a live server instance. They validate complete user workflows — navigating between pages, triggering scans, creating projects, applying effects, and verifying timeline rendering. They catch GUI rendering bugs, navigation regressions, and data-testid breakage that API-level tests cannot detect. Run before releases and after major GUI changes.

The two tiers are complementary, not redundant. Smoke tests validate that the API behaves correctly; UAT journeys validate that the GUI presents the API's data correctly to users. A passing smoke test suite with a failing UAT journey indicates a frontend-only bug. A failing smoke test means the UAT journeys will likely also fail (the runner skips dependent journeys when prerequisites fail).

For full UAT documentation, see [`docs/manual/uat-testing.md`](../../manual/uat-testing.md).

## Current GUI State

The project is between Phase 1 and Phase 2 completion out of 6 planned roadmap phases. Four GUI pages are fully implemented:

| Page | Route | Features |
|------|-------|----------|
| Dashboard | `/gui/` | Health cards (DB, FFmpeg, Rust Core), metrics cards (request count, avg response time), real-time activity log via WebSocket |
| Library | `/gui/library` | Video grid with thumbnails, debounced search, sort controls, pagination, scan directory modal with progress tracking |
| Projects | `/gui/projects` | Project list, create/delete projects, inline project detail view, clip CRUD with add/edit/delete modals |
| Effects | `/gui/effects` | Effect catalog with search/filter, schema-driven parameter form, live FFmpeg filter preview, effect stack management, transitions tab |

Pages not yet implemented: Timeline (Phase 3), Preview Player (Phase 4), AI Theater Mode (Phase 4), Render Queue (Phase 5).

## Roadmap Phases — Implementation Status

| Phase | Description | Status |
|-------|-------------|--------|
| Phase 1 | Foundation + Rust Core | Implemented |
| Phase 2 | Effects Engine | Implemented |
| Phase 3 | Composition Engine (PIP, split-screen, visual timeline) | Implemented (v015–v017) |
| Phase 4 | Preview & Playback (proxy gen, preview server, Theater Mode) | Not started |
| Phase 5 | Export & Production (render coordinator, HW acceleration) | Not started |
| Phase 6 | Deployability & AI Integration | Not started |

## Test Harness Implementation Status

| Tier | Scope | Status |
|------|-------|--------|
| Smoke — Core API | 12 use cases across scan, library, project, clip, effects, transitions, health | Implemented (v014) |
| Smoke — Expanded API | Timeline CRUD, composition, audio, batch, versions, filesystem, video detail/thumbnail/delete, negative paths | Implemented (v018–v019) |
| UAT Journeys | 4 Playwright journey scripts (J201–J204) exercising the React GUI end-to-end | Implemented (v022) |

## Why API-Level Smoke Tests Are the Right Phase 1 Choice

1. **Zero new dependencies.** `httpx` and `pytest-asyncio` are already dev dependencies. No browser binaries, no Node.js required in the test environment.
2. **Fast execution.** In-process via `ASGITransport` — no port binding, no startup delay. The full 12-test suite runs in under 10 seconds.
3. **Covers the Rust core.** Every API call that touches clip validation, effect building, or filter generation exercises the real Rust core via PyO3. This is the highest-value coverage gap.
4. **Deterministic.** No browser rendering, no CSS layout, no JavaScript timing issues. Tests are fully deterministic.
5. **Consistent with project philosophy.** The Rust core is never mocked — it is always used as-is in tests, per the project's black-box testing philosophy.

## Why Playwright Was Chosen for UAT

1. **Already in the project plan.** Playwright was listed in the technical stack design documents from the outset.
2. **`data-testid` ready.** All React components include `data-testid` attributes, making test authoring straightforward.
3. **Python bindings.** The UAT harness uses Playwright for Python (`playwright` package), integrating naturally with the project's Python-first toolchain. No Node.js runtime needed for UAT.
4. **Screenshot evidence.** Playwright captures per-step screenshots, providing visual debugging evidence for failures.
5. **Headed and headless modes.** Developers can watch journeys execute in a visible browser or run headlessly in CI.

## Video Metadata Reference

The `/videos/` directory contains 6 test videos used by the smoke tests. All are H.264 High profile with AAC-LC stereo audio at 48 kHz.

| Filename | Duration (s) | Resolution | FPS | Frame Rate (rational) | Frames | File Size | Color Space |
|----------|-------------|------------|-----|----------------------|--------|-----------|-------------|
| `120449-720880553_medium.mp4` | 35.84 | 1280x720 | 29.97 | 30000/1001 | 1,074 | 13.2 MB | bt709 |
| `15748-266043652_medium.mp4` | 28.93 | 1280x720 | 25.00 | 25/1 | 723 | 9.5 MB | bt709 |
| `78888-568004778_medium.mp4` | 29.73 | 1280x720 | 60.00 | 60/1 | 1,784 | 6.8 MB | bt709 |
| `81872-577880797_medium.mp4` | 50.99 | 1280x720 | 60.00 | 60/1 | 3,059 | 7.7 MB | bt709 |
| `running1.mp4` | 29.60 | 960x540 | 30.00 | 30/1 | 888 | 3.3 MB | smpte170m |
| `running2.mp4` | 22.32 | 960x540 | 29.97 | 30000/1001 | 669 | 4.9 MB | smpte170m |

Key observations:
- Four "medium" files are 1280x720 (720p); two "running" files are 960x540 (qHD)
- Frame rates vary: 25, ~29.97, 30, and 60 fps
- Longest: `81872-577880797_medium.mp4` at ~51s; shortest: `running2.mp4` at ~22s
- Total: ~45.4 MB across all 6 files
- These are real video files committed to the repository, not synthetic test fixtures

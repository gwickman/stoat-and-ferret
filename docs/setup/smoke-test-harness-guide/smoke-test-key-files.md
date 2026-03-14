# Smoke Test Key Files

> **Read this file first, then read only the files relevant to your task. Do not read all files listed here unless necessary.**

## What is the Smoke Test Suite?

The smoke test suite is an API-level integration test suite that runs in-process using `httpx.ASGITransport` (no real HTTP server). It exercises the full application stack including the real Rust core (`stoat_ferret_core`). Tests verify API endpoint contracts, request/response schemas, and end-to-end behaviour from HTTP request through to Rust-level processing.

## Key Files

### Phase 1 — Core API Smoke Tests (v014)

| File | What it tells you |
|------|-------------------|
| `tests/smoke/conftest.py` | Shared fixtures, test video setup, ASGITransport client, helpers |
| `tests/smoke/test_scan_workflow.py` | UC-01 and UC-12: video scanning and job cancellation |
| `tests/smoke/test_library.py` | UC-02: library search; also video detail, thumbnail, and delete (v019) |
| `tests/smoke/test_project_workflow.py` | UC-03 and UC-09: project CRUD and deletion |
| `tests/smoke/test_clip_workflow.py` | UC-04 and UC-10: clip add and modify |
| `tests/smoke/test_effects.py` | UC-05, UC-06, UC-11: effects catalog, update/delete, speed and stacking |
| `tests/smoke/test_transitions.py` | UC-07: fade transition |
| `tests/smoke/test_health.py` | UC-08: health live and ready probes |

### Phase 2 — Expanded API Smoke Tests (v018–v019)

| File | What it tells you |
|------|-------------------|
| `tests/smoke/test_timeline.py` | Timeline CRUD: create tracks, add/patch/delete clips, transitions (v018) |
| `tests/smoke/test_compose.py` | Composition layout: list presets, apply preset, invalid preset (v018) |
| `tests/smoke/test_audio.py` | Audio mixing: configure mix, preview mix (v018) |
| `tests/smoke/test_batch.py` | Batch operations: submit batch and poll to completion (v018) |
| `tests/smoke/test_versions.py` | Version management: list, restore, not-found, nonexistent project (v019) |
| `tests/smoke/test_filesystem.py` | Filesystem: directory listing, not-found, hidden file exclusion (v019) |
| `tests/smoke/test_negative_paths.py` | Negative paths: invalid inputs across timeline, audio, batch, compose (v019) |

### Conftest Additions (v018–v019)

| Item | Purpose |
|------|---------|
| `create_adjacent_clips_timeline()` | Helper to set up two adjacent clips on a timeline track for transition tests |
| `create_version_repo()` | Factory to create `AsyncSQLiteVersionRepository` from the live ASGI transport DB |

### Reference Documents

| File | What it tells you |
|------|-------------------|
| `docs/setup/smoke-test-harness-guide/03-test-cases.md` | Canonical use case definitions |
| `docs/setup/smoke-test-harness-guide/02-infrastructure.md` | Harness architecture decisions |

# C4 Directory Manifest

## Metadata
- Mode: delta
- Total Directories: 39
- Directories to Process: 17
- Batch Count: 2
- Previous Version: v008
- Previous Commit: c09dbf681e49edb5c1ce204a1481fb5650a2a9bd
- Generated: 2026-02-24 09:18 UTC

## Batch 1
- gui/src/components
- gui/src/components/__tests__
- gui/src/hooks
- gui/src/pages
- gui/src/stores
- gui/src/stores/__tests__

## Batch 2
- src/stoat_ferret
- src/stoat_ferret/api
- src/stoat_ferret/api/routers
- src/stoat_ferret/api/schemas
- src/stoat_ferret/api/services
- src/stoat_ferret/db
- src/stoat_ferret/ffmpeg
- src/stoat_ferret/jobs
- tests
- tests/test_api
- tests/test_doubles
- tests/test_jobs

## Unchanged Directories (delta mode)
- alembic (existing: c4-code-python-api.md covers migrations context)
- alembic/versions (existing: c4-code-python-db.md covers schema migrations)
- benchmarks (no dedicated c4-code doc)
- gui (existing: c4-code-gui-src.md covers root config)
- gui/e2e (existing: c4-code-gui-e2e.md)
- gui/src (existing: c4-code-gui-src.md)
- gui/src/hooks/__tests__ (existing: c4-code-gui-hooks-tests.md)
- rust/stoat_ferret_core/src (existing: c4-code-rust-stoat-ferret-core-src.md)
- rust/stoat_ferret_core/src/bin (existing: c4-code-rust-stoat-ferret-core-bin.md)
- rust/stoat_ferret_core/src/clip (existing: c4-code-rust-stoat-ferret-core-clip.md)
- rust/stoat_ferret_core/src/ffmpeg (existing: c4-code-rust-stoat-ferret-core-ffmpeg.md)
- rust/stoat_ferret_core/src/sanitize (existing: c4-code-rust-stoat-ferret-core-sanitize.md)
- rust/stoat_ferret_core/src/timeline (existing: c4-code-rust-stoat-ferret-core-timeline.md)
- scripts (existing: c4-code-scripts.md)
- src/stoat_ferret/api/middleware (existing: c4-code-stoat-ferret-api-middleware.md)
- src/stoat_ferret/api/websocket (existing: c4-code-stoat-ferret-api-websocket.md)
- src/stoat_ferret/effects (existing: c4-code-python-effects.md)
- src/stoat_ferret_core (existing: c4-code-stoat-ferret-core.md)
- tests/examples (existing: c4-code-tests-examples.md)
- tests/test_blackbox (existing: c4-code-tests-test-blackbox.md)
- tests/test_contract (existing: c4-code-tests-test-contract.md)
- tests/test_coverage (existing: c4-code-tests-test-coverage.md)
- tests/test_security (existing: c4-code-tests-test-security.md)

## Changed Files (delta mode)
- gui/src/components/ClipFormModal.tsx (added)
- gui/src/components/DirectoryBrowser.tsx (added)
- gui/src/components/ProjectDetails.tsx (modified)
- gui/src/components/ScanModal.tsx (modified)
- gui/src/components/__tests__/ClipFormModal.test.tsx (added)
- gui/src/components/__tests__/DirectoryBrowser.test.tsx (added)
- gui/src/components/__tests__/ProjectDetails.test.tsx (modified)
- gui/src/components/__tests__/ScanModal.test.tsx (modified)
- gui/src/hooks/useProjects.ts (modified)
- gui/src/pages/ProjectsPage.tsx (modified)
- gui/src/stores/__tests__/clipStore.test.ts (added)
- gui/src/stores/clipStore.ts (added)
- gui/src/stores/projectStore.ts (modified)
- src/stoat_ferret/api/app.py (modified)
- src/stoat_ferret/api/routers/filesystem.py (added)
- src/stoat_ferret/api/routers/health.py (modified)
- src/stoat_ferret/api/routers/jobs.py (modified)
- src/stoat_ferret/api/routers/projects.py (modified)
- src/stoat_ferret/api/schemas/filesystem.py (added)
- src/stoat_ferret/api/services/scan.py (modified)
- src/stoat_ferret/api/settings.py (modified)
- src/stoat_ferret/db/project_repository.py (modified)
- src/stoat_ferret/ffmpeg/probe.py (modified)
- src/stoat_ferret/jobs/queue.py (modified)
- src/stoat_ferret/logging.py (modified)
- tests/test_api/test_di_wiring.py (modified)
- tests/test_api/test_filesystem.py (added)
- tests/test_api/test_jobs.py (modified)
- tests/test_api/test_projects.py (modified)
- tests/test_api/test_spa_routing.py (added)
- tests/test_api/test_videos.py (modified)
- tests/test_api/test_websocket_broadcasts.py (added)
- tests/test_audit_logging.py (modified)
- tests/test_doubles/test_inmemory_job_queue.py (modified)
- tests/test_event_loop_responsiveness.py (added)
- tests/test_ffmpeg_observability.py (added)
- tests/test_ffprobe.py (modified)
- tests/test_jobs/test_asyncio_queue.py (modified)
- tests/test_logging_startup.py (modified)
- tests/test_project_repository_contract.py (modified)

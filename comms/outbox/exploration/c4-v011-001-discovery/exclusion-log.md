# C4 Discovery Exclusion Log

## Legend
- INCLUDE-CHANGED: Directory contains changed files, will be reprocessed
- INCLUDE-UNCHANGED: Directory has source code but no changes since v008, existing C4 doc preserved
- EXCLUDE-CONFIG: Directory excluded by configuration rule
- EXCLUDE-NO-SOURCE: Directory contains no source code files

## Source Directories

| Directory | Decision | Reason |
|-----------|----------|--------|
| alembic | INCLUDE-UNCHANGED | No changes; covered by existing docs |
| alembic/versions | INCLUDE-UNCHANGED | No changes; covered by existing docs |
| benchmarks | INCLUDE-UNCHANGED | No changes since v008 |
| gui | INCLUDE-UNCHANGED | Root config files unchanged |
| gui/e2e | INCLUDE-UNCHANGED | No changes; existing c4-code-gui-e2e.md |
| gui/src | INCLUDE-UNCHANGED | No changes; existing c4-code-gui-src.md |
| gui/src/components | INCLUDE-CHANGED | 2 added, 2 modified files |
| gui/src/components/__tests__ | INCLUDE-CHANGED | 2 added, 2 modified test files |
| gui/src/hooks | INCLUDE-CHANGED | 1 modified file (useProjects.ts) |
| gui/src/hooks/__tests__ | INCLUDE-UNCHANGED | No changes; existing c4-code-gui-hooks-tests.md |
| gui/src/pages | INCLUDE-CHANGED | 1 modified file (ProjectsPage.tsx) |
| gui/src/stores | INCLUDE-CHANGED | 1 added, 1 modified file |
| gui/src/stores/__tests__ | INCLUDE-CHANGED | 1 added test file (clipStore.test.ts) |
| rust/stoat_ferret_core/src | INCLUDE-UNCHANGED | No changes; existing doc |
| rust/stoat_ferret_core/src/bin | INCLUDE-UNCHANGED | No changes; existing doc |
| rust/stoat_ferret_core/src/clip | INCLUDE-UNCHANGED | No changes; existing doc |
| rust/stoat_ferret_core/src/ffmpeg | INCLUDE-UNCHANGED | No changes; existing doc |
| rust/stoat_ferret_core/src/sanitize | INCLUDE-UNCHANGED | No changes; existing doc |
| rust/stoat_ferret_core/src/timeline | INCLUDE-UNCHANGED | No changes; existing doc |
| scripts | INCLUDE-UNCHANGED | No changes; existing c4-code-scripts.md |
| src/stoat_ferret | INCLUDE-CHANGED | 1 modified file (logging.py) |
| src/stoat_ferret/api | INCLUDE-CHANGED | 2 modified files (app.py, settings.py) |
| src/stoat_ferret/api/middleware | INCLUDE-UNCHANGED | No changes; existing doc |
| src/stoat_ferret/api/routers | INCLUDE-CHANGED | 1 added, 3 modified files |
| src/stoat_ferret/api/schemas | INCLUDE-CHANGED | 1 added file (filesystem.py) |
| src/stoat_ferret/api/services | INCLUDE-CHANGED | 1 modified file (scan.py) |
| src/stoat_ferret/api/websocket | INCLUDE-UNCHANGED | No changes; existing doc |
| src/stoat_ferret/db | INCLUDE-CHANGED | 1 modified file (project_repository.py) |
| src/stoat_ferret/effects | INCLUDE-UNCHANGED | No changes; existing doc |
| src/stoat_ferret/ffmpeg | INCLUDE-CHANGED | 1 modified file (probe.py) |
| src/stoat_ferret/jobs | INCLUDE-CHANGED | 1 modified file (queue.py) |
| src/stoat_ferret_core | INCLUDE-UNCHANGED | No changes; existing doc |
| tests | INCLUDE-CHANGED | 5 modified, 3 added root-level test files |
| tests/examples | INCLUDE-UNCHANGED | No changes; existing doc |
| tests/test_api | INCLUDE-CHANGED | 3 modified, 3 added test files |
| tests/test_blackbox | INCLUDE-UNCHANGED | No changes; existing doc |
| tests/test_contract | INCLUDE-UNCHANGED | No changes; existing doc |
| tests/test_coverage | INCLUDE-UNCHANGED | No changes; existing doc |
| tests/test_doubles | INCLUDE-CHANGED | 1 modified file |
| tests/test_jobs | INCLUDE-CHANGED | 1 modified file |
| tests/test_security | INCLUDE-UNCHANGED | No changes; existing doc |

## Excluded Directory Patterns

The following patterns were excluded from the directory walk:

| Pattern | Reason |
|---------|--------|
| node_modules | Third-party dependencies |
| .git | Version control internals |
| build, dist | Build output |
| __pycache__ | Python bytecode cache |
| .tox | Tox test environments |
| .mypy_cache | Mypy type checker cache |
| .pytest_cache | Pytest cache |
| .venv, venv, env, .env | Virtual environments |
| .eggs, *.egg-info | Python egg build artifacts |
| target/ | Rust build directory |
| C4-Documentation/ | Existing C4 output (not source) |
| comms/ | Auto-dev communication artifacts |
| docs/auto-dev/ | Auto-dev documentation |
| docs/ideation/ | Ideation documents |

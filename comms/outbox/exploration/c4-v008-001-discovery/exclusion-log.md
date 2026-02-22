# C4 Discovery Exclusion Log

## Legend
- INCLUDED: Directory contains source code and is part of the manifest
- EXCLUDED: Directory was filtered out (reason given)
- DELTA-SKIP: Directory is unchanged since v007 (preserved from previous C4 generation)

## Source Directories

| Directory | Status | Reason |
|-----------|--------|--------|
| gui | INCLUDED | Ancestor of changed directory gui/e2e |
| gui/e2e | INCLUDED | Contains changed file: project-creation.spec.ts |
| gui/src | DELTA-SKIP | No files changed since v007 |
| gui/src/components | DELTA-SKIP | No files changed since v007 |
| gui/src/components/__tests__ | DELTA-SKIP | No files changed since v007 |
| gui/src/hooks | DELTA-SKIP | No files changed since v007 |
| gui/src/hooks/__tests__ | DELTA-SKIP | No files changed since v007 |
| gui/src/pages | DELTA-SKIP | No files changed since v007 |
| gui/src/stores | DELTA-SKIP | No files changed since v007 |
| rust/stoat_ferret_core/src | DELTA-SKIP | No files changed since v007 |
| rust/stoat_ferret_core/src/bin | DELTA-SKIP | No files changed since v007 |
| rust/stoat_ferret_core/src/clip | DELTA-SKIP | No files changed since v007 |
| rust/stoat_ferret_core/src/ffmpeg | DELTA-SKIP | No files changed since v007 |
| rust/stoat_ferret_core/src/sanitize | DELTA-SKIP | No files changed since v007 |
| rust/stoat_ferret_core/src/timeline | DELTA-SKIP | No files changed since v007 |
| scripts | DELTA-SKIP | No files changed since v007 |
| src/stoat_ferret | INCLUDED | Contains changed file: logging.py |
| src/stoat_ferret/api | INCLUDED | Contains changed files: __main__.py, app.py |
| src/stoat_ferret/api/middleware | DELTA-SKIP | No files changed since v007 |
| src/stoat_ferret/api/routers | INCLUDED | Contains changed file: ws.py |
| src/stoat_ferret/api/schemas | DELTA-SKIP | No files changed since v007 |
| src/stoat_ferret/api/services | DELTA-SKIP | No files changed since v007 |
| src/stoat_ferret/api/websocket | DELTA-SKIP | No files changed since v007 |
| src/stoat_ferret/db | INCLUDED | Contains changed files: __init__.py, schema.py |
| src/stoat_ferret/effects | DELTA-SKIP | No files changed since v007 |
| src/stoat_ferret/ffmpeg | DELTA-SKIP | No files changed since v007 |
| src/stoat_ferret/jobs | DELTA-SKIP | No files changed since v007 |
| src/stoat_ferret_core | DELTA-SKIP | No files changed since v007 |
| stubs/stoat_ferret_core | DELTA-SKIP | No files changed since v007 |
| tests | INCLUDED | Contains 7 changed test files |
| tests/examples | DELTA-SKIP | No files changed since v007 |
| tests/test_api | DELTA-SKIP | No files changed since v007 |
| tests/test_blackbox | DELTA-SKIP | No files changed since v007 |
| tests/test_contract | DELTA-SKIP | No files changed since v007 |
| tests/test_coverage | DELTA-SKIP | No files changed since v007 |
| tests/test_doubles | DELTA-SKIP | No files changed since v007 |
| tests/test_jobs | DELTA-SKIP | No files changed since v007 |
| tests/test_security | DELTA-SKIP | No files changed since v007 |

## Excluded Non-Source Directories (pattern matches)

| Pattern | Directories Excluded |
|---------|---------------------|
| `node_modules` | gui/node_modules/ and all subdirectories |
| `dist` | gui/dist/ and subdirectories |
| `__pycache__` | Various bytecode cache directories under src/ and tests/ |
| `.mypy_cache` | .mypy_cache/ |
| `.pytest_cache` | .pytest_cache/ |
| `C4-Documentation` | docs/C4-Documentation/ |
| `comms/` | comms/ and all subdirectories |
| `docs/auto-dev/` | docs/auto-dev/ and subdirectories |
| `docs/ideation/` | No matching directories found |
| `.git` | .git/ |
| `.venv`, `venv`, `env`, `.env` | No matching directories found |
| `.tox`, `.eggs`, `*.egg-info` | No matching directories found |
| `build` | No matching directories found |

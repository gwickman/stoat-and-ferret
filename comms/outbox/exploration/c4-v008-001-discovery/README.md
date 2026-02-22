# C4 Discovery Results - v008

Delta-mode discovery found 35 total source directories across the project. Of these, 6 directories contain files changed since v007 (commit cd76384). With ancestor inclusion, 7 directories require reprocessing. The remaining 28 directories are unchanged and their existing C4 code-level docs are preserved. All changed directories fit in a single batch.

- **Mode:** delta
- **Total Source Directories Found:** 35
- **Directories to Process:** 7
- **Directories Unchanged (delta only):** 28
- **Batch Count:** 1
- **Previous C4 Commit:** cd7638402e32497c1c801a3204e52f7a06d4de20

## Exclusions Applied

The following exclusion patterns matched directories during discovery:

| Pattern | Effect |
|---------|--------|
| `node_modules` | Excluded gui/node_modules/ tree (thousands of directories) |
| `dist` | Excluded gui/dist/ |
| `__pycache__` | Excluded Python bytecode cache directories |
| `C4-Documentation` | Excluded docs/C4-Documentation/ |
| `comms/` | Excluded comms/ tree |
| `docs/auto-dev/` | Excluded auto-dev process documentation |
| `docs/ideation/` | Pattern present but no matching directories found |
| `.mypy_cache` | Excluded mypy cache directories |
| `.pytest_cache` | Excluded pytest cache directories |

## Changed Files Summary

14 files changed across 6 direct directories since v007:

| Directory | Files Changed |
|-----------|--------------|
| `gui/e2e` | 1 (project-creation.spec.ts) |
| `src/stoat_ferret` | 1 (logging.py) |
| `src/stoat_ferret/api` | 2 (__main__.py, app.py) |
| `src/stoat_ferret/api/routers` | 1 (ws.py) |
| `src/stoat_ferret/db` | 2 (__init__.py, schema.py) |
| `tests` | 7 (test_async_repository_contract.py, test_clip_repository_contract.py, test_database_startup.py, test_logging.py, test_logging_startup.py, test_orphaned_settings.py, test_project_repository_contract.py) |

## Existing C4 Code-Level Docs

42 existing c4-code-*.md files found in docs/C4-Documentation/. All are preserved for unchanged directories. Changed directories will have their corresponding docs regenerated.

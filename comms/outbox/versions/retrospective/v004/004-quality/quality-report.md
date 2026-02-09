# Quality Report - Full Output

## Run Environment

- Platform: Windows (win32)
- Python: 3.13.11
- Date: 2026-02-09

---

## Check 1: ruff check

**Command:** `uv run ruff check src/ tests/`
**Result:** PASS (return code 0)

```
All checks passed!
```

---

## Check 2: ruff format

**Command:** `uv run ruff format --check src/ tests/`
**Result:** PASS (return code 0)

```
93 files already formatted
```

---

## Check 3: mypy

**Command:** `uv run mypy src/`
**Result:** PASS (return code 0)

```
Success: no issues found in 39 source files
```

---

## Check 4: pytest

**Command:** `uv run pytest tests/ --tb=short`
**Result:** PASS (return code 0)

```
============================= test session starts =============================
platform win32 -- Python 3.13.11, pytest-9.0.2, pluggy-1.6.0
rootdir: C:\Users\grant\Documents\projects\stoat-and-ferret
configfile: pyproject.toml
plugins: anyio-4.12.1, hypothesis-6.151.5, asyncio-1.3.0, cov-7.0.0
asyncio: mode=Mode.AUTO, debug=False
collected 586 items

tests\examples\test_property_example.py ....                             [  0%]
tests\test_api\test_app.py .......                                       [  1%]
tests\test_api\test_clips.py .............                               [  4%]
tests\test_api\test_di_wiring.py .....                                   [  4%]
tests\test_api\test_factory_api.py .....                                 [  5%]
tests\test_api\test_health.py ......                                     [  6%]
tests\test_api\test_jobs.py .....                                        [  7%]
tests\test_api\test_middleware.py .........                              [  9%]
tests\test_api\test_projects.py ...........                              [ 11%]
tests\test_api\test_settings.py ...........                              [ 12%]
tests\test_api\test_videos.py ............................               [ 17%]
tests\test_async_repository_contract.py ................................ [ 23%]
............                                                             [ 25%]
tests\test_audit_logging.py .............                                [ 27%]
tests\test_blackbox\test_core_workflow.py .......                        [ 28%]
tests\test_blackbox\test_edge_cases.py ...........                       [ 30%]
tests\test_blackbox\test_error_handling.py ............                  [ 32%]
tests\test_clip_model.py .........                                       [ 34%]
tests\test_clip_repository_contract.py ....................              [ 37%]
tests\test_contract\test_ffmpeg_contract.py .....ssssss..........        [ 41%]
tests\test_contract\test_repository_parity.py ........                   [ 42%]
tests\test_contract\test_search_parity.py .......                        [ 43%]
tests\test_coverage\test_import_fallback.py ...                          [ 44%]
tests\test_db_schema.py ........                                         [ 45%]
tests\test_doubles\test_inmemory_isolation.py ..........                 [ 47%]
tests\test_doubles\test_inmemory_job_queue.py ...........                [ 49%]
tests\test_doubles\test_seed_helpers.py ........                         [ 50%]
tests\test_executor.py .....................sss....                      [ 55%]
tests\test_factories.py .............                                    [ 57%]
tests\test_ffprobe.py .....sss..ss..                                     [ 59%]
tests\test_integration.py .............                                  [ 62%]
tests\test_jobs\test_asyncio_queue.py ............                       [ 64%]
tests\test_jobs\test_worker.py ....                                      [ 64%]
tests\test_logging.py ....                                               [ 65%]
tests\test_observable.py ..................                              [ 68%]
tests\test_project_repository_contract.py ........................       [ 72%]
tests\test_pyo3_bindings.py ............................................ [ 80%]
.............................                                            [ 85%]
tests\test_repository_contract.py ...................................... [ 91%]
.........                                                                [ 93%]
tests\test_security\test_input_sanitization.py .......................   [ 97%]
tests\test_security\test_path_validation.py .......s.....                [ 99%]
tests\test_smoke.py ....                                                 [100%]

=============================== tests coverage ================================
______________ coverage: platform win32, python 3.13.11-final-0 _______________

Name                                             Stmts   Miss Branch BrPart  Cover   Missing
--------------------------------------------------------------------------------------------
src\stoat_ferret\__init__.py                         2      0      0      0   100%
src\stoat_ferret\api\__init__.py                     0      0      0      0   100%
src\stoat_ferret\api\__main__.py                    10     10      2      0     0%   6-32
src\stoat_ferret\api\app.py                         57     15      4      1    74%   51-73
src\stoat_ferret\api\middleware\__init__.py          0      0      0      0   100%
src\stoat_ferret\api\middleware\correlation.py      18      0      0      0   100%
src\stoat_ferret\api\middleware\metrics.py          19      0      0      0   100%
src\stoat_ferret\api\routers\__init__.py             0      0      0      0   100%
src\stoat_ferret\api\routers\health.py              50      3      8      0    95%   78-80
src\stoat_ferret\api\routers\jobs.py                12      0      0      0   100%
src\stoat_ferret\api\routers\projects.py           106      6     30      5    92%   47, 65, 83-85, 332, 340
src\stoat_ferret\api\routers\videos.py              53      1     12      1    97%   43
src\stoat_ferret\api\schemas\__init__.py             0      0      0      0   100%
src\stoat_ferret\api\schemas\clip.py                25      0      0      0   100%
src\stoat_ferret\api\schemas\job.py                 11      0      0      0   100%
src\stoat_ferret\api\schemas\project.py             20      0      0      0   100%
src\stoat_ferret\api\schemas\video.py               40      0      0      0   100%
src\stoat_ferret\api\services\__init__.py            0      0      0      0   100%
src\stoat_ferret\api\services\scan.py               57      1     14      1    97%   107
src\stoat_ferret\api\settings.py                    20      0      0      0   100%
src\stoat_ferret\db\__init__.py                      8      0      0      0   100%
src\stoat_ferret\db\async_repository.py            116      8     18      1    93%   38, 49, 60, 72, 84, 98, 109, 162
src\stoat_ferret\db\audit.py                        18      0      0      0   100%
src\stoat_ferret\db\clip_repository.py              75      5     10      0    94%   34, 45, 56, 70, 81
src\stoat_ferret\db\models.py                       87      0      2      0   100%
src\stoat_ferret\db\project_repository.py           75      5     10      0    94%   36, 47, 59, 73, 84
src\stoat_ferret\db\repository.py                  120      7     22      0    95%   35, 46, 57, 69, 81, 95, 106
src\stoat_ferret\db\schema.py                       34      0      0      0   100%
src\stoat_ferret\ffmpeg\__init__.py                  6      0      0      0   100%
src\stoat_ferret\ffmpeg\executor.py                 60      6      8      0    91%   58, 93-105
src\stoat_ferret\ffmpeg\integration.py              20      4      0      0    80%   76-83
src\stoat_ferret\ffmpeg\metrics.py                   4      0      0      0   100%
src\stoat_ferret\ffmpeg\observable.py               27      0      0      0   100%
src\stoat_ferret\ffmpeg\probe.py                    51     18      6      0    61%   82-94, 110-128
src\stoat_ferret\jobs\__init__.py                    2      0      0      0   100%
src\stoat_ferret\jobs\queue.py                     156      7     24      2    95%   69, 83, 97, 196-197, 219->227, 380-381
src\stoat_ferret\logging.py                         16      0      2      0   100%
src\stoat_ferret_core\__init__.py                   36      0      0      0   100%
--------------------------------------------------------------------------------------------
TOTAL                                             1411     96    172     11    93%
Required test coverage of 80.0% reached. Total coverage: 92.86%
================ 571 passed, 15 skipped, 12 warnings in 9.50s =================
```

### Warnings Detail

12 ResourceWarning instances for unclosed `sqlite3.Connection` objects in `tests/test_blackbox/test_core_workflow.py::TestProjectLifecycle::test_create_and_retrieve_project`. These are non-blocking warnings related to connection cleanup in test fixtures and do not indicate functional issues.

### Skipped Tests (15)

- `tests/test_contract/test_ffmpeg_contract.py`: 6 skipped (FFmpeg not available or platform-specific)
- `tests/test_executor.py`: 3 skipped (FFmpeg binary required)
- `tests/test_ffprobe.py`: 5 skipped (ffprobe binary required)
- `tests/test_security/test_path_validation.py`: 1 skipped (platform-specific)

---

## Diff of Fixes Applied

No fixes were applied. All checks passed on the initial run.

---

## Before/After Comparison

Not applicable. No changes were made to the codebase.

---

## Summary

All four quality gates (ruff check, ruff format, mypy, pytest) pass cleanly. The codebase is in good shape after v004 completion with 92.86% test coverage (well above the 80% threshold). No test failures, no lint issues, no type errors.

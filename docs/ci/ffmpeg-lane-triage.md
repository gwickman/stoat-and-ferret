# FFmpeg CI Lane — F1-F5 Triage

**Date:** 2026-07-06
**Suite:** `STOAT_TEST_FFMPEG=1 uv run pytest tests/ --no-cov --timeout=120 -x`
**Environment:** FFmpeg 8.0.1 (local, full build with rubberband support)
**Result:** Exit 0 — all gated assertions pass

## Regression Classification

| ID | Description | Status | Fixed by |
|----|-------------|--------|----------|
| F1 | `DeesserBuilder` emitted `m=` parameter unknown to FFmpeg 8 | `fixed` | BL-605 / PR #737 (v097) |
| F2 | `PanBuilder` emitted `aeval eval=frame` (wrong FFmpeg 8 API) + unescaped commas in multi-channel spec | `fixed` | eval=frame: BL-605 / PR #737 (v097); commas: BL-610 / PR #744 (v098) |
| F3 | `FreezeFrameBuilder` used wrong `freezeframes` filter arity | `fixed` | BL-605 / PR #737 (v097) — builder now uses `tpad` |
| F4 | `AevalsrcBuilder` used deprecated `expr` parameter | `fixed` | BL-605 / PR #737 (v097) |
| F5 | `RubberBandBuilder` (`arubberband`) filter signature mismatch | `fixed` | BL-605 / PR #737 (v097) |

## Vacuous Guards

Gated tests that asserted `STOAT_TEST_FFMPEG` was set but did not invoke FFmpeg:

| Status | Fixed by |
|--------|----------|
| `fixed` | BL-606 / PR #739 (v097) — 5 pass-body stubs removed |

## Additional Findings

| Test | Classification | Notes |
|------|---------------|-------|
| `tests/smoke/test_render_contract.py::test_multi_clip_render_output_file_exists` | `quarantined` | `poll_job_until_terminal` polls `/api/v1/jobs/{job_id}` (404); correct endpoint is `/api/v1/render/{job_id}`. Pre-existing bug in conftest.py. Test skips without a running server so local suite exits 0, but will fail in CI once smoke fixtures use the real server. Tracked under BL-553-AC-4 scope. |

## Triage Outcome

All F1-F5 regressions and vacuous guards were resolved in v097 (PR #737 BL-605, PR #739 BL-606) before this lane was created. The `ffmpeg-tests` lane will run clean against the merged codebase.

**NFR-001 compliance:** The `ffmpeg-tests` job is not added to `ci-status` needs during this triage window. Promotion to required is a follow-up PR after triage period closes.

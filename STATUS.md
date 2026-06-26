# Project Status — stoat-and-ferret

**Current version:** v088 (R3 Wave 2 — Multi-Clip Render Pipeline + Tooling Hygiene)
**Status:** Completed 2026-06-26

## v088 Summary

R3 Wave 2 delivers the multi-clip rendering pipeline (BL-505 Layers 1–3): EffectDefinition metadata, Rust `RenderGraphTranslator` tuple API, render worker wired to translator, and `ValueKind`/`emit_filter_value` dispatch. Includes smoke test coverage for multi-clip render, harness guide update, and four tooling hygiene items (UAT registry, Windows smoke docs, pip-licenses skip guard, C4 drift test upgrade).

### Delivered

| Theme | Feature | Status | PR |
|-------|---------|--------|----|
| render-pipeline-effects | effectdef-metadata-and-rust-translator | ✓ | #662 |
| render-pipeline-effects | wire-worker-to-translator | ✓ | #662 |
| render-pipeline-effects | value-kind-escape-dispatch | ✓ | #663 |
| smoke-test-coverage | smoke-update-multi-clip-effects | ✓ | #664 |
| smoke-test-coverage | update-smoke-harness-guide | ✓ | #665 |
| tooling-test-hygiene | register-uat-known-failures | ✓ | #666 |
| tooling-test-hygiene | document-windows-smoke-command | ✓ | #667 |
| tooling-test-hygiene | fix-dep-license-skip-guard | ✓ | #668 |
| tooling-test-hygiene | upgrade-c4-drift-test | ✓ | #669 |

### Test Results

- **Test count:** ≥3276 passed (3273 baseline + new tests from render pipeline + smoke coverage)
- **Regressions:** 0
- **FFmpeg-gated (deferred_post_merge):** BL-553-AC-4 (2-clip SSIM render), BL-505 full render path
- **UAT-gated (deferred_post_merge):** BL-558-AC-5 (headless UAT confirmation), BL-559-AC-3 (Windows sandbox)

### Key Capabilities Added

- **EffectDefinition metadata** — `label`, `description`, `category` fields populated for all 34 registered effects; `create_default_registry()` updated
- **RenderGraphTranslator tuple API** — `translate()` now returns `(filter_complex_str, input_paths: list[str])`; `_core.pyi` stub updated
- **Render worker wired to translator** — `build_command_for_job` multi-clip path fetches per-clip effects from DB, validates against registry, unpacks translator output into `-i` args
- **ValueKind enum** — 7 variants (`Expression`, `Path`, `KneeString`, `EnumLiteral`, `Numeric`, `Boolean`, `Text`) in `ffmpeg/video.rs`; `emit_filter_value` canonical dispatch; `BlurBuilder`, `OpacityBuilder`, `ScaleBuilder` migrated
- **Multi-clip smoke tests** — 5 new tests in `test_render_contract.py` (4 static, 1 FFmpeg-gated); `test_render_cancel` race fixed
- **UAT known-failures registry** — J502 and J504 registered in `baseline-uat-failures.json`; runner exits 0 for pre-existing HTTP 422 failures
- **Windows smoke command** — `UV_NO_CACHE=1` documented in `smoke-test-harness.md` and `AGENTS.md`
- **pip-licenses skip guard** — OR semantics across module entry point + console script shim; None guard in `check_dependency_licenses.py`
- **C4 drift test** — upgraded to `create_app().openapi()` live-spec comparison; catches app.py drift that stale JSON missed

### Deferred (FFmpeg/UAT-gated)

- BL-553-AC-4: POST 2-clip project with blur + render + SSIM > 0.99 check (requires `STOAT_TEST_FFMPEG=1`)
- BL-558-AC-5: Headless UAT confirmation after J502/J504 registry entries (requires live headed UAT run)
- BL-559-AC-3: Windows sandbox smoke command verification (requires restricted Windows environment)

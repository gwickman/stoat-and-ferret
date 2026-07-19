# Changelog

All notable changes to stoat-and-ferret will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## v109 — API/Router & Validation Refactors, DB/DSP Refactors, Named-Constant Dedup & Smoke-Test Verification (2026-07-19)

4 themes, 17 features, PRs #849–#863.

### Theme 1: API Router and Validation Refactors (7 features)

Extracted helper functions from four API route handlers and two validation layers, collapsing inlined per-case logic into parameterized helpers and reducing Sonar S3776 cyclomatic complexity across the effects, clips, assets, and health-readiness handlers.

- BL-656: Extracted `_resolve_effect_helper`, `_validate_params_helper`, `_flatten_automation_helper`, `_build_filter_helper` from four effects-router handlers; variant-preserving parameterization preserves per-handler thumbnail, preview, and error-list differences (PR #849)
- BL-663: Split `ClipCreate.validate_clip_type_fields` into `_validate_file_clip`, `_validate_generator_clip`, `_validate_image_clip` private methods; dispatcher becomes a 3-arm if/elif/elif; added image-clip `timeline_end ≤ timeline_start` coverage test (PR #850)
- BL-664: Extracted `_process_automation_parameter`, `_build_rust_keyframes`, `_validate_scalar_parameters` from `registry.validate_with_automation`; `_validate_scalar_parameters` deduplicated across `validate()` and `validate_with_automation()` (PR #851)
- BL-669: Extracted `_check_dedup`, `_validate_upload_size`, `_sniff_content` from `upload_asset`; added `_ASSET_NOT_FOUND_DETAIL` constant consolidating 4 inline occurrences across asset handlers (PR #852)
- BL-670: Extracted `_run_check` helper collapsing 7 identical `asyncio.wait_for`/`TimeoutError` blocks in the health-readiness endpoint; added `_CHECK_TIMEOUT_ERROR` constant and `_resolve_overall_status` helper; parametrized timeout test now covers all 7 checks (PR #853)
- BL-673: Extracted strip helpers and centralized the ffmpeg-flag constant in the waveform module (PR #854)
- BL-672: Extracted `_build_scan_progress_callback`, `_broadcast_scan_started`, `_broadcast_scan_completed` from `make_scan_handler`; extracted `_check_and_flag_stale_proxies`, `_queue_proxy_for_video` from `_auto_queue_proxies`; extracted `_scan_one_file` per-file try/except (PR #855)

### Theme 2: DB, Effects, and Signal-Processing Refactors (3 features)

Consolidated migration helpers, extracted waveform result lifecycle helpers, and replaced an 11-key if/else dispatch in the astats parser with a data-driven mapping table.

- BL-657: Consolidated migration helpers and centralized error constants in the migrations module (PR #856)
- BL-658: Extracted result lifecycle helpers from the waveform module (PR #857)
- BL-674: Replaced 11-key if/else chain in `parse_astats_output` with a data-driven key→field mapping table; eliminates repeated pattern (PR #858)

### Theme 3: Named Constants and Dedup Literals (5 features)

Replaced 5 sets of duplicated string/expression literals with named module-level constants, making each value single-source-of-truth.

- BL-665: Named zoompan centering expressions — replaced duplicated inline expressions with `_ZOOMPAN_CENTER_X` and `_ZOOMPAN_CENTER_Y` constants (PR #859)
- BL-671: Named marker-not-found error literal — `_MARKER_NOT_FOUND_MSG` constant replaces duplicate raise strings (PR #860)
- BL-676: Named migration-rollback event constant — `_MIGRATION_ROLLBACK_EVENT` replaces inline literal in migration service (PR #861)
- BL-677: Named loudnorm and FFmpeg null-sink constants — `_LOUDNORM_FILTER`, `_FFMPEG_NULL_SINK` replace duplicated inline literals in QC module (PR #862)
- BL-678: Named TTS format-mismatch message constant — `_TTS_FORMAT_MISMATCH_MSG` replaces duplicated inline string in TTS module (PR #863)

### Theme 4: Smoke-Test Coverage Verification (2 features)

Verified existing smoke-test coverage for the effects registry and the health endpoint; no code changes required.

- Verify-001: Confirmed all 40+ effects in the registry have at least one non-skipped smoke test entry covering core functionality (verification only, no code changes)
- Verify-002: Confirmed health endpoint smoke tests pass end-to-end via the live API stack (verification only, no code changes)

### PRs

#849, #850, #851, #852, #853, #854, #855, #856, #857, #858, #859, #860, #861, #862, #863

### Resolved

BL-656 (effects-router variant-preserving helper extraction), BL-663 (clip-type validation per-type split), BL-664 (automation-parameter processing extraction), BL-669 (upload-asset helper extraction + error literal consolidation), BL-670 (health-readiness timeout/check pattern collapse), BL-673 (waveform strip helpers + ffmpeg-flag constant), BL-672 (scan-handler broadcast and stale-proxy helpers), BL-657 (migration helpers consolidation), BL-658 (waveform result lifecycle helpers), BL-674 (data-driven astats parsing), BL-665 (zoompan centering expression constants), BL-671 (marker-not-found literal dedup), BL-676 (migration-rollback event constant), BL-677 (loudnorm and ffmpeg null-sink constants), BL-678 (TTS format-mismatch message constant)

---

## v108 — Worker Hotspot Deduplication & Render Service Decomposition & Security Correctness Residuals (2026-07-18)

4 themes, 10 features, 39 ACs, PRs #840–#847.

### Theme 1: Worker Hotspot Deduplication (2 features)

Extracted 3 helpers from `render/worker.py`, reducing `build_command_for_job`'s cognitive complexity (codebase's top hotspot, CC 214).

- BL-655: Extracted `_resolve_clip_source` and `_build_clip_render_effects` (plus `_LABEL_FINAL`/`_LABEL_AOUT`/`_LABEL_VOUT` constants) from `build_command_for_job`, eliminating duplicated inline clip-source/effect-building logic across multi-clip and single-clip branches (PR #840)
- BL-668: Extracted `_dispatch_and_wait_for_cues` and `_build_tts_audio_inputs` from `_run_tts_preflight` (PR #840)

### Theme 2: Render Service and Executor Extraction (3 features)

Extracted 4 helpers from `render/service.py` for job-completion and progress handling, plus 4 helpers from `render/executor.py`'s FFmpeg subprocess drain path.

- BL-660: Extracted `_load_delivery_profile_assertions` and `_run_completion_qc` from `_complete_job` (PR #841)
- BL-667: Extracted `_log_progress_milestones`, `_persist_evidence`, `_finalize_success`, `_finalize_failure` from `run_job` (PR #841)
- BL-666: Extracted `_drain_stderr_task`, `_join_stderr_drain`, `_read_stdout_with_progress`, `_log_ffmpeg_failure` from `_run_process` (PR #842)

### Theme 3: Render Endpoint and App Lifecycle (2 features)

Decomposed `create_render_job`'s validation pipeline and extracted shutdown helpers from `app.py`'s `lifespan`/`create_app`.

- BL-662: Extracted `_validate_and_translate_plan`, `_validate_encoder_compatibility`, `_resolve_delivery_profile`, `_apply_qc_gate` from `create_render_job` (PR #843)
- BL-661: Extracted shutdown helpers (`_cancel_task_with_timeout`, `_shutdown_synthetic_monitoring`, `_shutdown_render_services`, `_shutdown_preview`) and DI-override helpers (`_apply_di_overrides`, `_apply_injected_repositories`, `_mount_gui_routes`) from `app.py`'s `lifespan`/`create_app` (PR #844)

### Theme 4: Security Correctness Residuals (3 features)

Fixed a TOCTOU race in the scan endpoint and a concurrent-waiter notification-loss race in job completion, plus end-to-end smoke coverage for both.

- BL-699: Fixed a TOCTOU race in `/api/v1/videos/scan` — endpoint and worker now re-validate against the resolved path instead of the raw caller-supplied path, closing a symlink-retarget window between validation and use (PR #845)
- BL-700: Fixed a concurrent-waiter notification-loss race in job completion — the long-poll registry changed from a single `asyncio.Event` per job to a `set[asyncio.Event]`, so all concurrent waiters are notified on job completion instead of only the first (PR #846)
- Added HTTP smoke tests covering both fixes end-to-end via the live API stack (PR #847)

### PRs

#840, #841, #842, #843, #844, #845, #846, #847

### Resolved

BL-655 (worker.py clip-source/effect dedup), BL-668 (TTS preflight helper split), BL-660 (render-completion QC helper extraction), BL-667 (run_job helper extraction), BL-666 (run_process drain-path helper extraction), BL-662 (create_render_job validation-pipeline decomposition), BL-661 (app.py shutdown/DI helper extraction), BL-699 (scan endpoint TOCTOU fix), BL-700 (concurrent-waiter notification-loss fix)

---

## v107 — React Row Identity, GUI Simplification, Async Event-Loop Hygiene & Path-Confinement Residual (2026-07-18)

### Theme 1: React Row Identity and Lint (3 features)

- BL-643: Gave `BatchPanel` rows a stable id to prevent focus loss on delete (PR #829)
- BL-644: Gave `EffectStack` rows a stable `clientIds` client id across async delete/refetch transitions (PR #830)
- BL-647: Added `react/no-array-index-key` lint rule and suppressed 2 benign sites; AC-3 ("passes clean") deferred_post_merge — falsified by 27 pre-existing/unrelated eslint errors confirmed byte-identical to pre-feature baseline (PR #831)

### Theme 2: GUI and Simplification Cleanups (2 features)

- BL-648: Removed duplicate branches in `EffectParameterForm` and `render_repository` (PR #832)
- BL-659: Converted `setProgress` to an options object and de-nested 2 ternaries (PR #833)

### Theme 3: Async Event-Loop Hygiene (5 features)

- BL-651: Moved blocking TTS/ffmetadata/filter-route writes off the shared event loop (PR #834)
- BL-652: De-async'd 3 test methods with no `await` (PR #835)
- BL-653: Replaced a fixed Playwright wait with an observable batch-status wait (PR #836)
- BL-654: Rewrote job-completion wait to `asyncio.timeout()` with a Python 3.10 fallback; AC-3's literal regression command (`-k job_completion`) selects 0 tests, an AC-authoring/test-naming gap — actual coverage is `tests/test_api/test_long_poll.py` (12/12 passing) (PR #837)
- BL-675: Extracted `async_executor.run()` closures to instance methods (PR #838)

### Theme 4: Security-Scan Path-Confinement Residual (1 feature)

- BL-696: Reordered `/api/v1/videos/scan` to confine the path before filesystem access (PR #839)

### PRs

#829, #830, #831, #832, #833, #834, #835, #836, #837, #838, #839

### Resolved

BL-643 (BatchPanel row stable id), BL-644 (EffectStack row stable client id), BL-647 (react/no-array-index-key lint rule — AC-3 deferred_post_merge), BL-648 (duplicate-branch removal), BL-659 (setProgress options object), BL-651 (offload blocking writes off event loop), BL-652 (de-async no-await tests), BL-653 (observable Playwright wait), BL-654 (asyncio.timeout job-completion wait — AC-3 weakened), BL-675 (async_executor closure extraction), BL-696 (videos/scan path confinement reorder)

---

## v106 — Security Hardening & Functional Fixes (2026-07-17)

### Theme 1: Preview and Filesystem Confinement (3 features)

- BL-636: Confined preview session-dir paths against traversal and added `X-Content-Type-Options: nosniff` to HLS responses in `src/stoat_ferret/api/routers/preview.py` (SonarCloud S2083, S6549, S5131) (PR #816)
- BL-637: `/api/v1/filesystem/directories` and `/api/v1/videos/scan` now apply an exposure-conditional fail-closed pre-check — loopback binds with unset `allowed_scan_roots` keep today's allow-all behavior, non-loopback binds (e.g. shipped `0.0.0.0`) now return HTTP 403 directing the operator to set `allowed_scan_roots`, and malformed/null-byte paths return a structured 400 instead of an unhandled 500; AC-7 (SonarCloud S6549 disposition) deferred to operator action (PR #818)
- BL-638: Added a path-confinement development principle to AGENTS.md, codifying the `confine_child_path()` pattern established by BL-636 (docs only) (PR #819)

### Theme 2: Script Sink and SSRF Hardening (4 features)

- BL-639: Closed a tracked-symlink write-sink escape in `scripts/add_license_headers.py` (PR #820)
- BL-640: CWD-confined path arguments accepted by `scripts/check_dependency_licenses.py`'s CLI (PR #821)
- BL-641: Added SSRF host-allowlist validation to render-verification scripts (PR #822)
- BL-642: Suppressed a ReDoS false positive on `tests/test_license_stray.py`'s `PYTHON_PATTERN` regex with a justified `# NOSONAR` suppression (PR #823)

### Theme 3: Functional Fixes and Lint Guards (4 features)

- BL-645: Fixed an information-loss bug on the render observability path — QC failure reason is now preserved on `QC_FAILED` render transitions instead of being dropped (PR #824)
- BL-646: Replaced a tautological self-comparison assertion (`TransitionType.Fade == TransitionType.Fade`, SonarCloud S1764) in `tests/test_transition_builders.py` with a comparison of two independently constructed instances (PR #825)
- BL-650: Retained the reference to the fire-and-forget frame-capture task in `RenderService` instead of letting it be garbage-collected mid-flight (SonarCloud S7502) (PR #826)
- BL-649: Added `PLR0124` (self-comparison) and `RUF006` (unawaited asyncio task) to the ruff `[tool.ruff.lint] select` list to guard against regressions of BL-646 and BL-650 (PR #827)

### PRs

#816, #818, #819, #820, #821, #822, #823, #824, #825, #826, #827

(PR #817, "poll job-queue jobs at /api/v1/jobs, not /api/v1/render", BL-692, merged within this version's execution window but is a smoke-test-infrastructure prerequisite fix, not one of v106's 11 planned items.)

### Resolved

BL-636 (preview session-path confinement + HLS nosniff), BL-637 (fail-closed filesystem scan scope — AC-7 operator-gated), BL-638 (path-confinement dev principle), BL-639 (license-header write-sink symlink escape), BL-640 (dependency-license CLI CWD confinement), BL-641 (SSRF host-allowlist for verification scripts), BL-642 (ReDoS false-positive suppression), BL-645 (QC failure reason preservation), BL-646 (tautological assertion fix), BL-650 (frame-capture task retention), BL-649 (ruff lint guards for BL-646/BL-650)

---

## v105 — Process, Tooling & Test-Hygiene Tech-Debt (2026-07-12) — FINAL PLANNED VERSION

### Theme 1: Process and Tooling Guardrails (4 features)

- BL-619: Established `.scratch/` as canonical disposable-output location — 30 committed junk files untracked; `.gitignore` gaps closed for `working/`, `rust/stoat_ferret_core/data/`, `.quality_*.txt`, `j[0-9][0-9][0-9]_*.png`, `stoat_ferret.db*`; "Scratch Directory" section added to AGENTS.md (PR #801)
- BL-468: Added Behavioral AC Citation Policy to AGENTS.md — requires any AC describing existing implementation behavior to cite file:line; cites BL-402-AC-4 (v074 global counter misread) as canonical incident (PR #802)
- BL-474: Added executor completion-report routing guard to auto-dev-mcp feature executor template — prohibits `completion-report.md` routing to exploration outbox (auto-dev-mcp PR #1041)
- BL-562: Extended `_validate_grep_targets` in `build_source_ledger.py` to emit WARNING when non-empty `expected_grep_targets` pattern produces zero matches; two new unit tests (auto-dev-mcp PR #1042)

### Theme 2: CI and Build Infrastructure (4 features)

- BL-632: Confirmed maturin rebuild already present at 7 CI locations; added stale-.pyd smoke test `tests/test_smoke.py::test_maturin_pyd_is_current`; added AGENTS.md note that `maturin develop` must run from project root after every Rust merge (PR #803)
- BL-498: Added `scripts/check_pyi_append_only.py` — CI guard that blocks any PR reducing `__new__` constructor count in `src/stoat_ferret_core/_core.pyi` below base-branch count; CI step added to `.github/workflows/ci.yml` (PR #804)
- BL-466: Calibrated Windows CI timing constants — `test_frame_endpoint_timing` threshold 250ms (Windows) / 100ms (linux/mac); active-jobs poll deadline 4.0s (Windows) / 2.0s (linux/mac); `sys.platform == "win32"` detection; "Windows CI Timing" section added to AGENTS.md (PR #805)
- BL-612: Wired `ffmpeg-tests` job into `ci-status.needs` in `.github/workflows/ci.yml`; AC-1 (GitHub branch protection required check) requires operator action (PR #806)

### Theme 3: Test Correctness and Code Hygiene (7 features)

- BL-557: Aligned `__version__` to `importlib.metadata.version("stoat-ferret")` — all 5 version surfaces now consistent: `pyproject.toml`, `stoat_ferret.__version__`, FastAPI `app.version`, `/api/v1/version.app_version`, `/api/v1/source.version` (PR #807)
- BL-540: Removed dead dict-wrapper branch from `scripts/uat_runner.py:load_known_failures`; 5 dict-wrapper smoke tests removed; raises `ValueError` on non-list input (direct commit)
- BL-493: Replaced hardcoded `len(registry.list_all()) == 40` in effects test with `REQUIRED_EFFECT_TYPES` frozenset membership check — adding new effect types no longer requires test modification (direct commit)
- BL-504: Renamed 20 test functions to `_ffmpeg_contract` suffix across 12 test files; conformance test added to `tests/test_hygiene.py`; convention documented in `docs/setup/smoke-test-harness-guide/07-dsp-contract-tests.md` (direct commit)
- BL-564: Re-anchored `SQL_INTERPOLATION_ALLOWLIST` in `tests/security/test_audit.py` from `(file_path, line_number)` to `(file_path, enclosing_function_name)` via AST walk — 20 sites re-anchored; inserting new functions before existing allowlisted code no longer requires allowlist edits (direct commit)
- BL-566: Updated AGENTS.md frontend-tests section with canonical `cd gui && npx vitest run` invocation; note added to smoke-test-harness.md; CI grep guard step added to verify documented invocation stays in AGENTS.md (direct commit)
- BL-559: Verify-and-close — `UV_NO_CACHE=1 uv run pytest tests/smoke/` already documented in AGENTS.md and smoke-test-harness.md at HEAD; 3/3 ACs supported (direct commit)

### Theme 4: Runtime Fixes and FFmpeg Coverage (6 features)

- BL-630: Fixed J703 headless UAT locator — scoped `[data-testid='qc-status-fail']` to `.first()` in `j_qc_fail.py:41` to resolve Playwright strict-mode violation with 2+ matching elements in headless mode (PR #808)
- BL-629: Fixed `parse_spectral_report` in Rust to strip av_log bracket prefix (`[Parsed_ametadata_0 @ 0x...]`) before parsing `lavfi.aspectralstats.*` lines; Rust unit test added (PR #809)
- BL-631: Added `aformat=channel_layouts=stereo,aresample=48000` normalization to source-audio branch in `worker.py` amix segments — mono 44.1kHz source audio + TTS now produces stereo 48kHz output (PR #810)
- BL-608: Re-implemented `test_tts_mixing_energy_bands` with a non-pass body — renders fixture with source audio + TTS cue, calls ffprobe, asserts two distinct frequency energy bands present; gated on `STOAT_TEST_FFMPEG=1` (PR #811)
- BL-609: Re-implemented 4 stubbed subtitle FFmpeg contract tests — burned subtitles, SRT render, force_style escape, colon-escaped force_style; all gated on `STOAT_TEST_FFMPEG=1` (PR #812)
- BL-408: Extended `VideoResponse` with `subtitle_count` and `data_count` fields; `ffprobe_video()` now counts subtitle and data codec streams; AC-1/AC-2 deferred (fixture files required) (PR #813)

### Theme 5: Documentation and Compliance (2 features)

- BL-634: Ported 6 C4 documentation fixes from ARTIFACTS repo to MAIN repo `docs/C4-Documentation/` — BL-470 (api-schemas video), BL-486 (render QCService), BL-487 (effects automatable), BL-497 (generator-clip schema), BL-573 (assets router), BL-614 (render worker.py); all 7 grep targets verified in main repo (PR #814)
- BL-526: Verify-and-close — CLA compliance infrastructure verified at HEAD: `CONTRIBUTING.md`, `CLA.md`, `.github/PULL_REQUEST_TEMPLATE.md`, `.cla-assistant.json` all confirmed delivered by v083 PR #616; AC-6/9/10 deferred (CLA Assistant App install — operator UI action) (PR #815)

### PRs

#801, #802, #803, #804, #805, #806, #807, #808, #809, #810, #811, #812, #813, #814, #815

### Resolved

BL-619 (repo-root hygiene), BL-468 (AC citation policy), BL-474 (executor completion-report guard), BL-562 (ledger token-presence validation), BL-632 (maturin stale-.pyd documentation), BL-498 (_core.pyi append-only guard), BL-466 (Windows CI timing), BL-612 (ffmpeg-tests lane — AC-1/2 operator-gated), BL-557 (__version__ alignment), BL-540 (UAT dict-wrapper removal), BL-493 (effect count assertion invariant), BL-504 (FFmpeg contract test naming), BL-564 (SQL allowlist function anchor), BL-566 (vitest invocation documentation), BL-559 (Windows smoke command), BL-630 (J703 headless UAT locator fix), BL-629 (spectral bracket-prefix fix), BL-631 (TTS stereo fix), BL-608 (TTS energy-bands test), BL-609 (subtitle FFmpeg contract tests), BL-408 (video aux stream counts — AC-1/2 fixture-gated), BL-634 (C4 doc-drift port), BL-526 (CLA compliance — AC-6/9/10 operator-gated)

---

## v104 — C4 Documentation Drift Repair (2026-07-11)

### Theme 1: Python C4 Documentation

- BL-470: Added Video Schemas section to `c4-code-stoat-ferret-api-schemas.md` — documents VideoResponse (including subtitle_count/data_count added in v074), VideoListResponse, VideoSearchResponse, ScanRequest, ScanError, ScanResponse (ARTIFACTS PR #8)
- BL-486: Added QCService dependency to `c4-code-stoat-ferret-render.md` — Code Elements section, Mermaid classDiagram arrow, and Dependencies block now reflect the optional QCService injected into RenderService in v078; updated `c4-component-application-services.md` accordingly (ARTIFACTS PR #8)
- BL-487: Added EffectDefinition.automatable field and two new EffectRegistry methods (validate_with_automation, build_automation_filter_string) to `c4-code-python-effects.md` — Rust automation dependencies (Automation, Keyframe, compile_automation) added to External Dependencies block; component doc updated with automation-envelope path (ARTIFACTS PR #8)
- BL-497: Added generator-clip schema (clip_type, generator_params, nullable source_video_id) to `c4-code-rust-stoat-ferret-core-clip.md` and `c4-code-stoat-ferret-db.md` — references Alembic revision a8516edf859e; image-clip additions (BL-511) included (ARTIFACTS PR #9)
- BL-573: Added assets router section to `c4-code-stoat-ferret-api-routers.md` (five /api/v1/assets endpoints, AsyncSQLiteAssetRepository dependency injection) and Asset Repository section to `c4-code-stoat-ferret-db.md` (AssetRecord fields, repository methods); added AssetRead/AssetListResponse to api-schemas doc (ARTIFACTS PR #9)
- BL-614: Added worker.py module section to `c4-code-stoat-ferret-render.md` — documents multi-clip render orchestration and RenderGraphTranslator integration path added in v098 (ARTIFACTS PR #10)

### Theme 2: Rust C4 Documentation

- BL-496: Added spatial.rs module to `c4-code-rust-stoat-ferret-core-ffmpeg.md` (PanBuilder, ConvolutionReverbBuilder); added SubBassBuilder to audio.rs section and PitchShiftBuilder to voice_repair.rs section; updated `c4-component-rust-core-engine.md` with spatial-audio capability (PR #796)
- BL-613: Added translate.rs module section to `c4-code-rust-stoat-ferret-core-render.md` — documents RenderGraphTranslator, RenderEffect struct, and RenderEffectKind enum (including Custom variant and py_custom()) (PR #797)

### Theme 3: Source Corrections

- BL-467: Added DB Column Addition Checklist to AGENTS.md — enumerates the 9-file surface required when adding a DB column (models.py, repositories, schema.py, Alembic migration, test_audit.py, test_repository_parity.py, test_db_schema.py, GUI TypeScript fixture); cites BL-408/v074 as provenance (PR #798)
- BL-633: Fixed test_uc_cap_split_scenario — injected InMemoryAssetRepository in DI mode to prevent AttributeError on app.state.db when lifespan is skipped in chatbot scenario tests (PR #799)
- BL-491: AC-2/AC-3 supported — v079 source-intent-ledger target_tree corrected to api/schemas/render.py; design-phase drift query verification confirmed; AC-1 deferred pending user action (BL-489 description path correction)

### PRs

#796, #797, #798, #799 (main repo); ARTIFACTS #8, #9, #10 (Python C4 documentation)

### Resolved

BL-470 (api-schemas video.py section), BL-486 (render QCService C4 dependency), BL-487 (effects automatable/automation-registry C4), BL-497 (generator-clip schema C4), BL-573 (assets router/repository C4), BL-614 (render worker.py C4), BL-496 (Rust ffmpeg spatial.rs builders), BL-613 (Rust render translate.rs), BL-467 (DB column checklist), BL-633 (uc_cap_split AssetRepoDep DI fix)

---

## v103 — R2/R3 Effect-Umbrella Triage and Discharge (2026-07-10)

### Theme 1: Code Correctness Patches

- BL-494: Clamped tone synthesis frequency to [20, 20000] Hz — values outside the audible range no longer produce silent or FFmpeg-rejected output (PR #788)
- BL-495: Wired `Automation` type into tone generator frequency — animated tone frequency now accepted by the builder (PR #789)
- BL-563: Added `_escape_filter_option_path()` helper (variant-4 policy: single-quoted, drive-colon-escaped, apostrophe-rejected) to `definitions.py` — resolves LUT path colon escape for FFmpeg `lut3d` filter on Windows paths (PR #790)

### Theme 2: Mixer & TTS Discharge

- BL-517-AC-1: Confirmed multi-track mixer tests pass under STOAT_TEST_FFMPEG=1 (pure discharge, no code changes)
- BL-516-AC-4: Added `test_tts_renderer_routes_to_mixer_48khz_stereo` integration test — confirms TTS output routes into multi-track mixer at channels=2, sample_rate=48000 (PR #791)
- BL-631 (raised): TTS+source-audio amix silently downmixes to mono when source clip is mono — filed P2, carry-forward to v104

### Theme 3: Audio Effects Discharge

- BL-430-AC-2, BL-431-AC-2: Mastering discharge — 11/11 volume automation and multiband compressor tests pass under STOAT_TEST_FFMPEG=1 (pure discharge)
- BL-434-AC-1, BL-435-AC-3: Voice repair discharge — 7/7 de-esser and time-stretch tests pass under STOAT_TEST_FFMPEG=1 (pure discharge)
- BL-437 (AC-1 through AC-4): Pan discharge — 16/16 stereotools/pan tests pass under STOAT_TEST_FFMPEG=1 (pure discharge)
- BL-438 (AC-1 through AC-4): Reverb discharge — added `test_convolution_reverb_decay` for AC-2; 10/10 tests pass under STOAT_TEST_FFMPEG=1 (PR #792)

### Theme 4: Video Effects, Subtitle & Editing Discharge

- BL-450-AC-3: Color LUT FFmpeg contract — 24/24 LUT tests pass under STOAT_TEST_FFMPEG=1 after BL-563 path-escape fix (pure discharge)
- BL-446 (AC-1 through AC-4): Range effect discharge — 21/21 window tests pass under STOAT_TEST_FFMPEG=1 (pure discharge)
- BL-449 (AC-1 through AC-3): Freeze frame discharge — 24/24 freeze-frame tests pass under STOAT_TEST_FFMPEG=1 (pure discharge)
- BL-453-AC-3: Added `test_chromatic_aberration_ffmpeg_contract` to `tests/test_effects_optical_distortion.py` — `rgbashift` filter confirmed working under FFmpeg 8 (PR #793)
- BL-519 (AC-1 through AC-7), BL-520 (AC-1 through AC-6): Added `test_subtitle_burned_contract` and `test_subtitle_force_style_contract` to `tests/test_contract/test_subtitle.py` — burned subtitle and force_style contracts discharged (PR #794)
- BL-444 (AC-1/2/3): Reverse clip effect — existing headless tests pass; AC-4 GUI preview deferred
- BL-445 (AC-1/2/3): Clip split/razor — existing headless tests pass; AC-4 unverifiable (test_uc_cap_split_scenario AssetRepoDep regression, triage carry-forward)

### PRs

#788, #789, #790, #791, #792, #793, #794

### Resolved

BL-494 (frequency clamping), BL-495 (Automation type wiring), BL-563 (LUT path escape helper), BL-516-AC-4 (TTS→mixer routing test), BL-438-AC-2 (convolution reverb decay test), BL-430-AC-2 (volume automation discharge), BL-431-AC-2 (multiband compressor discharge), BL-434-AC-1 (de-esser discharge), BL-435-AC-3 (time-stretch discharge), BL-437 (pan discharge — all ACs), BL-438 (reverb discharge — all ACs), BL-450-AC-3 (color LUT FFmpeg contract), BL-446 (range effect — all ACs), BL-449 (freeze frame — all ACs), BL-453-AC-3 (chromatic aberration FFmpeg contract), BL-519 (subtitle — all 7 ACs), BL-520 (force_style — all 6 ACs)

---

## v102 — QC Gate Correctness & UAT Registry Cleanup (2026-07-09)

### Theme 1: QC Gate Correctness

- BL-623: Excluded null-pass (no-measurement) checks from `overall_verdict` aggregation — `overall_verdict` now reflects only checks that ran and produced a result; "always-fail" regression resolved (PR #778)
- BL-624: Added `ametadata=mode=print` to tone_presence FFmpeg command — tone detection now emits parseable `lavfi.astats` metadata; `check_tone_presence` returns a non-null `measured` value (PR #779)
- BL-625: Switched loudness_integrated tolerance check to bidirectional ±0.5 LU window per AC-MASTER-2 spec; updated golden fixture and compliant-render test (PRs #780, #781)
- BL-626: Fixed null-decode path in decode integrity check — `None` codec name no longer causes `AttributeError`; check returns a structured result in all paths (PR #782)
- BL-627: Completed OC-to-QC-check mapping table coverage — all outcome codes have a mapped `qc_check` entry; `test_oc_mapping_completeness` passes (PR #783)
- BL-628: `POST /qc/run` now resolves delivery profile targets via `DeliveryProfileRepository`; loudness and true-peak assertions are populated before `run_checks` is called (PR #784)

### Theme 2: Acceptance Harness Discharge

- BL-459: Fixed `_evaluate_oc_outcomes` semantics and aligned OC count assertion with actual OC-to-QC mapping; acceptance harness passes for all mapped outcome codes (PR #785)
- BL-457-AC-3: Discharged J703/J704 headed UAT — removed J703/J704 from UAT baseline failure registry (direct commit 4817fdad)

### Theme 3: UAT Registry Cleanup

- BL-536: Registered J204 in UAT baseline failure registry — baseline reflects J204 known failure (direct commit 38929883)
- BL-558: Registered J502 and J504 in UAT baseline failure registry — baseline reflects two additional known failures (direct commit d8902152)

### PRs

#778, #779, #780, #781, #782, #783, #784, #785

### Resolved

BL-623 (overall_verdict null-pass exclusion — AC-2/3/4 supported; AC-1 FFmpeg-gated deferred), BL-624 (tone_presence FFmpeg fix — ACs supported), BL-625 (bidirectional loudness tolerance — ACs supported), BL-626 (decode integrity null decode — AC-1/2/4 supported; AC-2/3 FFmpeg-gated deferred), BL-627 (OC mapping completeness — ACs supported), BL-628 (QC router profile resolution — ACs supported), BL-459 (acceptance harness _evaluate_oc_outcomes fix — ACs supported), BL-457-AC-3 (J703/J704 headed UAT discharge), BL-536 (J204 UAT baseline registration), BL-558 (J502/J504 UAT baseline registration)

---

## v101 — QC Completion (R2 P1 Cluster) (2026-07-09)

### Theme 1: QC Bug Fix Discharge

- BL-476: Switched `QCService._check_loudness_integrated` and `_check_true_peak` from `ebur128=framelog=verbose` to `loudnorm=print_format=json` measurement pass — Rust `parse_loudness_report` parser now receives JSON it can read; loudness_integrated.measured and true_peak.measured are non-null and numeric for the first time (PR #771)
- BL-477: Wired `QCService` invocation into `RenderWorkerLoop` post-completion step; `GET /render/{job_id}/qc` now returns 200 with a persisted `QCReport` for real-mode worker-path renders; QC_FAILED transition and WS event parity with the inline path (PR #772)
- BL-488: `render/service.py` `_handle_completion` now mirrors the inline submit path's `_build_assertions_from_profile` call — loudness_integrated.target and true_peak.target are non-null and pass is computed when a delivery profile is attached (PR #772)

### Theme 2: QC Build Discharge

- BL-423: Five Rust QC measurement parsers (loudnorm/ebur128, astats/volumedetect, silencedetect, aspectralstats, blackdetect/freezedetect) added to `rust/stoat_ferret_core/src/qc/mod.rs` with PyO3 bindings and proptest fuzz coverage — no panic on arbitrary input; all 5 discharged against real FFmpeg 8 in CI (PR #773)
- BL-424 (AC-5): Golden QC fixture determinism test confirms two back-to-back `QCService.run_checks` calls on the same 5s sine fixture produce identical `checks` dicts (PR #774)
- BL-427: `OC_TO_QC_CHECK` mapping dict and `OC_HUMAN_ONLY` list in `tests/qc/oc_mapping.py`; `TestOcAssertionsAgainstFixture` activated (no longer placeholder-skipped); `TestOcMapping` structural tests run in every CI build (direct commit on main via PR #773 session)
- BL-426: `generate_ffmetadata()` verified via ffprobe — chapter count equals section count, title embedded, `chapters_present` QC check passes (direct commit on main via PR #773 session)

### Theme 3: v100 Post-Orch Riders

- BL-620: `scripts/verify_render_output.py` default mode now fetches `GET /render/{job_id}` and asserts only `RenderJobResponse` fields (status, output_path, progress); eliminates permanent false FAIL from schema mismatch with `exit_code`/`output_size_bytes` (PR #775)
- BL-621: Multi-clip TTS amix source-audio detection expanded across all clip indices — source audio from a non-zero clip is no longer silently dropped when `audio_codec` is absent from clip 0 (PR #776)
- BL-622: `assemble_multi_track_mixer()` raises `ValueError` on duplicate track IDs; `TtsCueUpdate.start_s` gains `le=86400.0` upper bound matching `TtsCueCreate.start_s` (PR #777)

### PRs

#771, #772, #773, #774, #775, #776, #777

### Resolved

BL-476 (QC loudness/true-peak parser fix — all 4 ACs supported), BL-477 (worker-path QC wiring — 2/4 ACs supported; AC-1/2 pre-existing; AC-3 deferred_post_merge), BL-488 (delivery-profile assertions — 3/5 ACs; AC-1/2 pre-existing; AC-3 deferred_post_merge), BL-423 (Rust QC parsers — all 6 ACs supported), BL-424 AC-5 (golden fixture determinism), BL-427 (OC mapping layer — all 4 ACs supported), BL-426 (chapter/metadata discharge — all 4 ACs supported), BL-620 (verify script default mode — all 5 ACs supported), BL-621 (multi-clip TTS amix — 4/5 ACs; AC-5 deferred_post_merge), BL-622 (TTS validation gaps — 4/5 ACs; AC-1 weakened: case mismatch "duplicate" vs "Duplicate")

---

## v100 — Render Reliability, Evidence & Subtitle Hardening (2026-07-07)

### Theme 1: Render Command Correctness

- BL-618: Reordered subtitle `-i` inputs before the `-filter_complex`/`-map` output section — fixes all multi-clip soft-subtitle renders that were hard-failing with FFmpeg's `-map` rejection (PR #758)
- BL-578: Patched `RenderGraphTranslator` multi-clip and single-clip paths to amix source audio with TTS audio when `audio_codec` is present — eliminates silent source-audio data loss for TTS renders; in-version hotfix chain [#759, #761] (PR #759)
- BL-616: Mirrored multi-clip `windowed_custom` dispatch check in the single-clip effect loop — single-clip windowed T-capable effects now emit `enable='between(t,...)'`; in-version hotfix chain [#760, #761] (PR #760)
- Render smoke coverage: Three static smoke tests added to `tests/smoke/test_render_contract.py` covering each corrected render path end-to-end without FFmpeg (PR #761)

### Theme 2: Render Evidence and Isolation

- BL-554: Added `scripts/verify_render_output.py` for CLI render verification; `GET /render/{job_id}/evidence` endpoint added; `STOAT_RENDER_EVIDENCE_FULL_ACCESS` env var; config doc updated (PR #762)
- BL-403: Re-verified concurrent render output path isolation is intact at HEAD (v072 fix confirmed across 28 intermediate versions; no code changes required)

### Theme 3: Subtitle Filtergraph Hardening

- BL-586: Added real-FFmpeg round-trip test for `BurnedSubtitleBuilder` `force_style` — discharges the FFmpeg-gated AC-6 deferred in v094; no Rust source changes needed (existing `escape_force_style()` was already correct) (PR #763)
- BL-601: `SubtitleScriptBuilder` now emits `fontcolor='{}'` (single-quoted); `emit_filter_option_path()` Unix/relative branch returns single-quoted paths; `BackslashInUnixPath` error variant added; 7 stale test assertions updated (PR #764)

### Theme 4: Audio Builder Hardening

- BL-581: SQLite FK coverage test for `DuckingPair` — exercises `ON DELETE CASCADE` at the database layer (PR #765)
- BL-582: TTS audio mixer hardened with zero-track guard, duplicate `stream_idx` guard, `start_s ≤ 86400.0` bound validation, and CRUD tests (PR #766)
- BL-603: `ZoompanBuilder` now rejects bare `n` at construction time; `ken_burns()` factory added for common slow-zoom/pan presets (PR #767)

### Theme 5: Test Quality and Doc Hygiene

- BL-606: Fixed 7 vacuous tests — G2 boxblur assertion and G5 windowed probe converted to real `STOAT_TEST_FFMPEG`-gated tests; 5 pre-existing stubs resolved (PR #768)
- BL-617: Updated `docs/STATUS.md` with corrected test count (3629 → 3745), PR #755 status (not merged, UA-001 pending), and missing version sections for v083–v096 (PR #769)

### PRs

#758, #759, #760, #761, #762, #763, #764, #765, #766, #767, #768, #769

### In-version hotfixes

BL-578 hotfix chain: #759, #761 (TTS amix fix + smoke coverage)
BL-616 hotfix chain: #760, #761 (single-clip windowed dispatch + smoke coverage)

### Resolved

BL-618 (multi-clip subtitle `-i` ordering — 4/6 ACs; 2 FFmpeg-gated deferred), BL-578 (TTS source audio mix — 5/6 ACs; AC-5 FFmpeg-gated deferred), BL-616 (single-clip windowed dispatch — 4/5 ACs; AC-3 FFmpeg-gated deferred), BL-554 (render evidence script + endpoint — all 9 ACs supported), BL-586 (BurnedSubtitle force_style — all 6 ACs supported), BL-601 (subtitle seam durable fix — all 8 ACs supported), BL-582 (TTS audio mixer hardening — all 6 ACs supported), BL-603 (ZoompanBuilder validation + ken_burns — all 4 ACs supported), BL-606 (vacuous test fixes — 6/7 ACs; AC-5 FFmpeg-gated deferred), BL-617 (STATUS.md correction — all 4 ACs supported), BL-403 (concurrent render isolation — 3/4 ACs; AC-3 FFmpeg-gated deferred)

### Partially resolved

BL-581 (DuckingPair SQLite FK coverage — execution-confirmed 4/4 ACs; 6 design ACs in source-intent-ledger not in outcome-evidence ledger; delta carried to v101)

---

## v099 — Image/Generator Clip Types + Windowed Effects (2026-07-07)

### Theme 1: Render Worker Clip Coverage

- BL-615: `parameters_dict` now passed correctly to `build_fn` in render worker — fixes generator/image clips that received an empty params dict instead of the clip's stored parameters (PR #753)
- BL-511 / BL-604: Render worker updated to route `image` and `generator` clip types through their respective render paths; image clips dispatched via `deferred_ac` guard (render path discharge pending); generator clips call `build_generator_source_filter` dispatch (PR #754)

### Theme 2: Windowed Effects Integration

- BL-512: `windowed_custom()` factory added to effects router — stores window spec per effect in the database; `RenderGraphTranslator.translate()` extended with `enable=` expression injection for windowed effects; `translate.rs` `enable_expr` field wired through `filter_complex` assembly; `enable=` extension activated via the existing translate.rs extension point (PRs #756, #757)

### PRs

#753, #754, #756, #757

### Not yet merged

PR #755 (`feat(BL-604): R3 use-case E2E tests + discharge cross-links`) was created but NOT merged to main. BL-604-AC-3 (per-clip effects FFmpeg pixel-check test), AC-4 (E2E R3 UAT test), and AC-5 (deferred_ac guard removal + cross-links) remain absent from main; fate of PR #755 pending owner triage.

### Resolved

BL-511 (image clip render routing — all 7 ACs supported)

### Partially resolved

BL-615 (parameters dict fix — AC-1/2/3 supported; AC-4 deferred_na: stored-filter_string alternative path not adopted), BL-604 (R3 use-case acceptance — AC-1/2 supported; AC-3/4/5 absent pending PR #755 triage), BL-512 (windowed effects integration — AC-1/3/5 supported; AC-2 weakened; AC-4 unverifiable)

---

## v098 — FFmpeg-8 Correctness + STOAT_TEST_FFMPEG CI Lane + Multi-Clip Render Closure (2026-07-06)

### Theme 1: FFmpeg-8 Correctness

- BL-610: PanBuilder `aeval=exprs=` now wraps the expression in single quotes to prevent FFmpeg 8 filtergraph misparse on automation expressions containing commas (PR #744)
- BL-611: `test_opacity_geq.py::_mean_alpha` helper fixed — removed invalid `pix_fmt=rgba` on color source, added `format=rgba` before `extractplanes=a`, added `check=True` to surface FFmpeg errors (PR #745)
- BL-602: `RenderGraphTranslator` animated-alpha geq expression corrected from lowercase `t` to uppercase `T` for the FFmpeg geq timestamp variable (PR #746)

### Theme 2: STOAT_TEST_FFMPEG CI Lane

- BL-607: Dedicated `ffmpeg-tests` CI job on ubuntu-latest with FFmpeg 8 and `STOAT_TEST_FFMPEG=1`; pre-existing regressions triaged; lane documented in AGENTS.md and smoke-test-harness guide (PRs #747, #748)

### Theme 3: Render Pipeline Closure

- BL-555: `ValueKind` 7-variant enum and `emit_filter_value()` dispatch function added to `video.rs`; 4 builders (HueRotation, Curves, Vignette, BurnedSubtitle) migrated to typed dispatch; `value_kind_per_option` dict added to `definitions.py` (PR #749)
- BL-505 / BL-553: Multi-clip render pipeline fully wired — `worker.py` iterates all clips, builds per-clip `RenderEffect` list, calls `RenderGraphTranslator.translate()` for filter_complex; `RenderEffect.custom()` PyO3 method added; xfade `offset=` parameter fixed; SSIM integration tests with >0.99 threshold added (PR #750)

### PRs

#744, #745, #746, #747, #748, #749, #750

### Resolved

BL-610 (PanBuilder aeval comma escape), BL-611 (test_opacity_geq helper fix), BL-602 (animated-alpha geq uppercase T), BL-607 (ffmpeg-tests CI lane), BL-555 (ValueKind typed dispatch), BL-505 (multi-clip render pipeline), BL-553 (worker multi-clip integration)

---

## v097 — Test-truth keystone + FFmpeg-8 builder regression fixes (2026-07-06)

### Theme 1: Test Infrastructure Keystone

- BL-605: Per-effect DoD gated test coverage guard — `tests/test_coverage/test_dod_gated_coverage.py` enforces that each effect in the registry has at least one non-skipped unit test; CI blocks when coverage regresses (PR #737)
- BL-503: DoD policy doc + per-effect gated coverage guard test — `docs/design/dod-policy.md` codifies the coverage contract; gated coverage rule enforced in CI (PR #741)
- BL-506: Validate Output step-7 forward-pointer added to chatbot testing workflow doc; all BL-506 ACs discharged (PR #742)

### Theme 2: FFmpeg-8 Builder Regression Fixes

- BL-502: OPACITY_EFFECT automation template updated from `colorchannelmixer` to `geq` — fixes animated opacity on FFmpeg 8.x where `colorchannelmixer` expression syntax changed; BL-478/BL-479 (deesser/multiband normalization builder fixes) folded into this builder-fix pass (PR #738)
- BL-606: Vacuous and broken gated tests fixed — 5 pass-body stubs removed; gated test infrastructure corrected; BL-607 (FFmpeg CI lane with `STOAT_TEST_FFMPEG`) carried forward to v098 (PR #739)

### PRs

#737, #738, #739, #741, #742

### Resolved

BL-605 (per-effect DoD gated coverage guard), BL-503 (DoD policy doc + gated coverage test), BL-506 (Validate Output step-7 + all BL-506 ACs discharged), BL-502 (OPACITY_EFFECT colorchannelmixer→geq), BL-606 (vacuous/broken gated tests fixed)

### Carry-forward

BL-607 (FFmpeg CI lane — deferred to v098)

---

## v096 — Post-R3 Hygiene Bundle (2026-07-04)

### Fixed

- BL-599: `font_color` and `emit_filter_option_path` now reject values containing commas and semicolons — closes a filtergraph metacharacter injection path in the subtitle filter (PR #731)

### Added

- BL-599: Smoke tests for comma/semicolon `font_color` injection rejection; smoke harness guide updated to document coverage (PRs #732, #733)
- BL-600: Fence-post test at the argv-limit routing threshold (32,267 chars) — validates that filtergraphs at the exact character limit route to temp-file correctly (PR #734)

### Changed

- BL-598: `pytest-rerunfailures` installed; `test_render_cancel` unskipped and promoted from flaky to stable (PR #735)

### PRs

#731, #732, #733, #734, #735

### Resolved

BL-598 (pytest-rerunfailures + render cancel stability), BL-599 (comma/semicolon filtergraph metacharacter rejection), BL-600 (argv-limit fence-post test)

---

## v095 — Post-R3 Hygiene Bundle (2026-07-03)

### Fixed

- BL-595: `emit_filter_option_path` now rejects values containing colons at construction time, closing a filter-option injection path that bypassed the BL-586 force_style safety guard
- BL-596: `SubtitleScriptSpec.font_color` validated against colon injection at field construction
- BL-593: UNC path (`\\server\share`) subtitle file references correctly escaped for the `drawtext` filter on Windows
- BL-597: argv-limit guard hardened — overhead constant added, fence-post off-by-one fixed, write-failure cleanup added, and `_run_job` integration coverage expanded (PR #728)

### Added

- BL-591: Rust unit tests for `ParseError::WrongArity` in `procedural_parser.rs` — distinguishes argument-count mismatches from syntax errors (PR #726)
- BL-592: HTTP-layer tests for TTS PATCH synthesis-field reset contract (PR #727)
- Subtitle injection smoke tests and smoke harness guide (Theme 01 Features 004–005)

### Changed

- BL-590: Stale J502/J504 entries removed from `tests/fixtures/baseline-uat-failures.json`
- BL-545: `HTTP_422_UNPROCESSABLE_ENTITY` renamed to `HTTP_422_UNPROCESSABLE_CONTENT` across 4 router files (PR #729)
- BL-594: CI reliability — Docker image threshold raised to 474 MB, timing test bounds relaxed, `test_render_cancel` race annotated (PR #730)
- BL-565-AC-3: UAT baseline cleanup confirmed; J204/J501 entries removed in v093 PR #710; AC-3 runtime discharge complete

### PRs

#720, #721, #722, #723, #724, #725, #726, #727, #728, #729, #730

### Resolved

BL-590 (UAT baseline J502/J504 cleanup), BL-591 (WrongArity Rust tests), BL-592 (TTS PATCH reset HTTP tests), BL-545 (HTTP_422 constant rename), BL-565 (UAT J204/J501 discharge — AC-3 confirmed; AC-1/AC-2/AC-4 source_stale, completed v093), BL-593 (UNC path subtitle escaping), BL-594 (CI reliability), BL-595 (emit_filter_option_path colon rejection), BL-596 (font_color colon injection fix), BL-597 (argv-limit guard hardening)

---

## v094 — Subtitle Filter Remediation (2026-07-03)

### Fixed

- BL-585: `SubtitleScriptBuilder` font_file Windows path escaping — `font_file` now uses `emit_filter_option_path` semantics matching `BurnedSubtitleBuilder`; definitions.py metadata updated; 6 new tests (PR #716)
- BL-586: `BurnedSubtitleBuilder` force_style single-quote and invalid key rejection — `escape_force_style` now rejects bare single-quotes with a descriptive error; key validation rejects `'`, `,`, `=`, `:` per `emit_filter_option_path` convention; 10 new tests (PR #717)
- fix(BL-584): route long FFmpeg filtergraphs to temp file on Windows to avoid CreateProcessW 32,767-char argv limit (#718)

### Breaking Changes

- `BurnedSubtitleBuilder.build()` now raises `ValueError` for `force_style` values containing a bare single-quote. Font names with apostrophes (e.g., `O'Brien`) are rejected.
- `BurnedSubtitleBuilder.build()` now raises `ValueError` for `force_style` keys containing `'`, `,`, `=`, or `:`.

### Deferred (pending discharge)

- BL-586-AC-6: `test_burned_subtitle_force_style_ffmpeg_safe` — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_contract/test_subtitle.py::test_burned_subtitle_force_style_ffmpeg_safe`

### PRs

#716, #717, #718

### Resolved

BL-585 (SubtitleScriptBuilder font_file Windows path), BL-586 (BurnedSubtitleBuilder force_style safety)

---

## v093 — Render Correctness Hotfixes, API Test Coverage, Documentation & Rust Quality (2026-07-02)

### Fixed

- BL-583: Soft subtitle stream map corrected — subtitle filter input mapping repaired for multi-stream renders; `test_soft_subtitle_ffprobe_streams` FFmpeg-gated (AC-6 deferred) (PR #701)
- BL-574: Image-clip asset validation — `source_asset_id` now validated at clip-creation time, guarding against missing or deleted asset references before render time (PR #702)
- BL-579: TrackCreate finite validation — all numeric fields on `TrackCreate` now validated as finite IEEE 754 values; non-finite inputs raise `ValueError` at construction time (PR #703)

### Added

- BL-580: TTS HTTP layer tests — CRUD test suite for `POST /tts_cues`, `GET /tts_cues`, `GET /tts_cues/{id}`, `PATCH /tts_cues/{id}`, `DELETE /tts_cues/{id}` endpoints (PR #704)
- BL-581: DuckingPair HTTP layer tests — CRUD test suite for `POST /ducking_pairs`, `GET /ducking_pairs`, `PATCH /ducking_pairs/{id}`, `DELETE /ducking_pairs/{id}` endpoints; AC-4 weakened — SQLite FK integration test pending (PR #705)
- BL-588: Ducking quiet-window test discharge — `test_music_unchanged_during_silence` authored, discharging BL-517-AC-8 (PR #707)
- BL-589: TTS speech energy placement test — energy-placement test suite for TTS cue `start_s` positioning; ACs 2, 3, 6 FFmpeg-gated (deferred) (PR #708)
- BL-575: `WrongArity` variant added to `ProceduralParserError` Rust enum — distinguishes argument-count mismatches from syntax errors; PyO3 bindings updated (PR #713)
- BL-555: `BurnedSubtitleBuilder` migrated to `emit_filter_value` dispatch — replaces ad-hoc string formatting with the shared `emit_filter_value` dispatch function; 11 new contract tests; AC-5 gated pending BL-505B (PR #714)

### Changed

- BL-587: `generated_asset_id` drift repair — stale `generated_asset_id` field removed from `TtsCueResponse` and related schemas following the v092 rename to `audio_path` (PR #709)
- BL-565: UAT baseline cleanup — stale J204/J501 entries removed from `tests/fixtures/baseline-uat-failures.json`; AC-3 UAT-gated pending headed browser run (PR #710)
- BL-576: Smoke skip messages updated to reference `BL-515-AC-14` as the authoritative tracking item (PR #711)
- Feature 004: `docs/manual/smoke-test-key-files.md` updated with v090–v092 module additions (PR #712)

### Deferred (pending discharge)

- BL-583-AC-6: `test_soft_subtitle_ffprobe_streams` — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_contract/test_subtitle.py::test_soft_subtitle_ffprobe_streams`
- BL-589-AC-2/AC-3/AC-6: `TestTtsSpeechEnergyPlacementFFmpeg` — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_contract/test_tts.py::TestTtsSpeechEnergyPlacementFFmpeg`
- BL-581-AC-4: SQLite FK integration test for DuckingPair track FK constraint — `test_create_ducking_pair_invalid_track_returns_422` using real SQLite fixture
- BL-565-AC-3: Headed UAT confirmation run verifying J204/J501 are absent from Playwright results
- BL-555-AC-5: BL-505B cross-check — discharges automatically when BL-505B lands

### PRs

#701, #702, #703, #704, #705, #707, #708, #709, #710, #711, #712, #713, #714

### Resolved

BL-583 (subtitle stream map — AC-6 FFmpeg-deferred), BL-574 (image-clip asset validation), BL-579 (TrackCreate finite validation), BL-580 (TTS HTTP tests), BL-588 (ducking quiet-window discharge), BL-589 (TTS speech energy placement — ACs 2/3/6 FFmpeg-deferred), BL-587 (generated_asset_id drift), BL-576 (smoke skip message update), BL-575 (WrongArity variant)

### Partially resolved

BL-581 (DuckingPair HTTP tests — AC-4 weakened), BL-565 (UAT baseline cleanup — AC-3 UAT-deferred), BL-555 (emit_filter_value migration — AC-5 BL-505B-gated)

---

## v092 — Release 3 Wave 7 + Wave D + v091 TTS P1 Repair Riders (2026-07-01)

### Fixed
- BL-577: TTS GET /tts_cues returning HTTP 500 — `generated_asset_id` UUID coercion removed; field renamed to `audio_path: str | None` in `TtsCueResponse` (PR #694)
- BL-578: TTS render dropped source video audio — `amix` filter now preserves source audio stream alongside TTS in single-clip TTS renders (PR #695)

### Changed
- BL-556: `docs/STATUS.md` is now the sole canonical status file; root `STATUS.md` replaced with a one-line redirect stub (PR #696)

### Added
- BL-518: `SubtitleScriptBuilder` — timed drawtext caption chains with `enable='between(t,start,end)'` expressions (PR #697)
- BL-519: `BurnedSubtitleBuilder` — SRT/ASS sidecar burn-in via FFmpeg `subtitles=` and `ass=` filters (PR #698)
- BL-520: Soft subtitle embedding — MP4/MKV native subtitle tracks via `SoftSubtitleSpec` in `RenderPlanSettings` (PR #699)

---

## v091 — Multi-track Audio Mixer + TTS Narration (2026-06-29)

### Added

- **Multi-track audio mixer with per-track volume automation and voice-triggered ducking** (BL-517, PR #689): `MultiTrackAudioMixer` Rust builder assembles FFmpeg `asplit`/`sidechaincompress`/`amix` pipeline from per-track volume envelopes; wellness contract enforces clamp, monotonicity, and coverage invariants.
- **Configurable TTS narration** (BL-516, PRs #690 #691 #692): TTS cue CRUD API, Piper (local) and Kokoro (cloud) backend services with SHA-256 audio cache; TTS renderer integration with `adelay` injection and voice-track preflight.

### Known Limitations

- **BL-517-AC-8** (quiet-window test): `test_music_unchanged_during_silence` deferred post-merge; sidechaincompress mechanism guarantees property physically but automated test not yet authored.
- **BL-516-AC-4 / FR-002-AC-2** (speech energy placement): End-to-end energy measurement at `cue.start_s` deferred post-merge; requires real TTS audio + FFmpeg + ffprobe energy envelope verification.

### PRs

#689, #690, #691, #692

### Resolved

BL-517 (multi-track audio mixer — AC-8 deferred), BL-516 (TTS narration — AC-4/FR-002-AC-2 deferred)

---

## v090 — Asset Library, Image Clips, Rust Builder Validation Hardening (2026-06-28)

### Added

- **User Asset Library REST API** (BL-515, PRs #680 #681): Five endpoints for managing uploaded image/font assets — `POST /api/v1/assets` (multipart upload with Pillow magic-bytes validation, SHA-256 deduplication, 413/415/422 enforcement), `GET /api/v1/assets` (paginated list with kind filter), `GET /api/v1/assets/{id}` (metadata), `GET /api/v1/assets/{id}/file` (binary download), `DELETE /api/v1/assets/{id}` (soft-delete). Settings: `STOAT_ASSETS_DIR`, `STOAT_ASSETS_MAX_SIZE_BYTES`. Alembic migration with `CREATE TABLE IF NOT EXISTS` guard.
- **Image clip support** (BL-511, PR #682): `clip_type=image` added to `ClipCreate` schema with `source_asset_id` cross-field validation. Image clips persist to the database with `timeline_start`/`timeline_end` constraints enforced. Render path deferred to v091+.
- **Generic procedural image builder** (BL-514, PR #683): `GenericProceduralImageBuilder` PyO3 class backed by a Rust recursive-descent expression parser. Supports arithmetic, trigonometry, conditionals, and per-pixel `(x, y, t)` evaluation. Safety bounds: parse-depth limit 32, eval budget 10k ops/pixel, pow clamp ±100, per-row timeout.
- **Procedural shape generators** (BL-513): `ConcentricRingsGenerator`, `RadialBurstGenerator`, `SpiralGenerator` — IEEE 754 finiteness guards added in v090 (BL-572).
- **IEEE 754 validation for builders** (BL-569 / BL-570 / BL-572, PR #684): `!is_finite()` guards in `CurvesBuilder` knee-string validation, `VignetteBuilder`, and three shape generators. Three new `EscapeError` variants: `NonFiniteKneeCoord`, `KneeCoordOutOfRange`, `EmptyKneeString`.
- **Empty-expression guards for FFmpeg builders** (BL-567 / BL-568, PR #686): `HueRotationBuilder` and `ZoompanBuilder` now reject empty/whitespace-only expression strings at construction time (`ValueError`). `ZoompanBuilder` integer parameters `d`/`width`/`height`/`fps` promoted from `u32` to `i64` so negative values raise `ValueError` (not `OverflowError`).
- **UAT runner J501→J204 dependency** (BL-571, PR #685): `JOURNEY_DEPS[501] = [204]` wired so J501 skips when the asset-library smoke journey (J204) has not passed.

### Known Limitations

- **Image clip render path** (BL-511-AC-3 / AC-7): The FFmpeg `-loop 1 -i <image_path>` render path is explicitly out of v090 scope. A `deferred_ac` guard in `worker.py` raises `CommandBuildError` if an image clip is encountered at render time. Discharge planned for a future version after asset-lookup integration is complete.
- **BL-515-AC-14**: Referential integrity guard (DELETE protection when an image clip references the asset) is deferred pending BL-511 render path completion.

### PRs

#680, #681, #682, #683, #684, #685, #686

### Resolved

BL-515 (user asset library), BL-511 (image clip schema — render path deferred), BL-514 (generic procedural image builder), BL-572 (ConcentricRings/RadialBurst/Spiral IEEE 754 guards), BL-569 (CurvesBuilder IEEE 754 guards), BL-570 (VignetteBuilder IEEE 754 guards), BL-567 (HueRotation empty-expression guard), BL-568 (Zoompan u32→i64 promotion), BL-571 (UAT runner J501→J204 dependency)

---

## v089 — Release 3, Wave 3a + Wave 4: FFmpeg Filter Builders & Procedural Shape Generators

**Added:**
- ZoompanBuilder: Ken Burns slow-zoom and pan effects with fps/settb pinning
- CurvesBuilder: Colour grading with preset and per-channel KneeString modes
- VignetteBuilder: Cinematic corner-darkening with position-enum surface
- HueRotationBuilder: Hue cycling with single-quote expression wrapping
- Procedural Shape Generators: Spiral, RadialBurst, Checkerboard, ConcentricRings (new `shapes/` Rust module)
- Wave 3a smoke test coverage: 8 new smoke tests for FFmpeg builders and effects
- Timeline-T window verification: EffectDefinition.timeline_T_capable field and hygiene test suite

**Fixed:**
- (None — all new features, no bug fixes in v089)

**Deferred:**
- ZoompanBuilder negative-control FFmpeg test (BL-507-AC-3): Requires FFmpeg availability; discharge plan documented
- Timeline-T dispatcher and fallback rendering (BL-512-AC-2/AC-4): Blocked by BL-505 (multi-clip render graph)
- Shape generator snf-managed asset path (BL-513-AC-4): Blocked by BL-511 (asset path API); using temp-dir placeholder

**PRs:** #671–#678 (8 merged)

**Resolved:**
- BL-507: ZoompanBuilder implementation
- BL-508: CurvesBuilder implementation
- BL-509: VignetteBuilder implementation
- BL-510: HueRotationBuilder implementation
- BL-512: Timeline-T window parameter verification
- BL-513: Procedural shape generators

---

## v088 — R3 Wave 2 (2026-06-26)

### Added

- **EffectDefinition metadata fields**: `stream_kind`, `arity`, `chain_safe`, `timebase_mutating`, `timeline_T_capable`, `requires_path_escape`, `value_kind_per_option` added to `EffectDefinition` in `src/stoat_ferret/effects/definitions.py`; hygiene test cross-checks `timeline_T_capable` flags against FFmpeg `-filters` T flag (BL-552, PR #662)
- **Rust RenderGraphTranslator**: Rust translator at `rust/stoat_ferret_core/src/render/translate.rs` converts a clips+effects+transitions structure to an FFmpeg `filter_complex` string and ordered `-i` input paths; supports timeline-T windowed `enable=` expressions and split/trim/concat fallback; rejects N>100 clips; PyO3 bindings and `_core.pyi` stubs updated (BL-552, PR #662)
- **Worker multi-clip integration**: `src/stoat_ferret/render/worker.py` iterates all clips, fetches per-clip effects from the database, calls the Rust translator, and assembles the final FFmpeg command from translator output instead of the legacy `settings.filter_graph` path; render evidence fields (`exit_code`, `output_size_bytes`, `command_args`) populated after job completes (BL-553, PRs #663 #664)
- **Per-value-kind escape policy**: `ValueKind` enum (Expression, Path, KneeString, EnumLiteral, Numeric, Boolean, Text) and `emit_filter_value` dispatch function in `rust/stoat_ferret_core/src/ffmpeg/video.rs`; BlurBuilder, OpacityBuilder, ScaleBuilder migrated to use dispatch; `value_kind_per_option` dict populated for migrated builders; 11 contract tests added (BL-555, PR #665)
- **UAT known-failures registry — Journeys 502 and 504**: `tests/fixtures/baseline-uat-failures.json` registers J502 and J504 (HTTP 422 pre-existing condition); `uat_runner.py` exits 0 when only registered journeys fail (BL-558, PR #668)
- **Windows smoke documentation**: `docs/manual/smoke-test-harness.md` gains a Windows-specific invocation section documenting `UV_NO_CACHE=1 uv run pytest tests/smoke/ -v --timeout=120 --no-cov`; `AGENTS.md` Quality Gates section references the `UV_NO_CACHE=1` variant (BL-559, PR #668)
- **Multi-clip smoke tests and harness guide**: Smoke tests for multi-clip render with effects added; `docs/manual/smoke-test-harness.md` updated with v088 coverage (PRs #666 #667)

### Fixed

- **Dependency-license test skip guard**: `tests/test_dependency_licenses.py` skip guard now checks both resolution paths (`python -m pip_licenses` AND `shutil.which("pip-licenses")`); `scripts/check_dependency_licenses.py` emits a clear error when `pip-licenses` is absent instead of a TypeError (BL-560, PR #668)
- **C4 drift test live-spec comparison**: `tests/test_c4_yaml_drift.py` upgraded to compare the C4 YAML against `create_app().openapi()` (live in-process spec) instead of the committed static `gui/openapi.json`, catching app.py drift that static-JSON comparison misses (BL-561, PR #669)

### Deferred (pending discharge)

- BL-553 AC-4: SSIM integration test for 2-clip render — requires FFmpeg (`STOAT_TEST_FFMPEG=1 uv run pytest tests/test_render/ -k ssim`)
- BL-555 AC-3: 4 named builders (HueRotationBuilder, CurvesBuilder, VignetteBuilder, BurnedSubtitleBuilder) absent at HEAD; will be migrated when those builders ship (BL-508/509/510/519)
- BL-558 AC-5: Headless UAT confirmation run — requires live browser session
- BL-559 AC-3: Windows sandbox smoke execution verification

### PRs

#662, #663, #664, #665, #666, #667, #668, #669

### Resolved

BL-552 (EffectDefinition metadata + Rust RenderGraphTranslator), BL-555 (per-value-kind escape policy — AC-3 weakened), BL-558 (UAT failure registry J502/J504 — AC-5 deferred), BL-559 (Windows smoke documentation — AC-3 deferred), BL-560 (dep-license skip guard fix), BL-561 (C4 drift test live-spec upgrade)

### Partially resolved

BL-553 (worker multi-clip integration — AC-4 FFmpeg-deferred)

---

## v087 — Release 3 Waves 0–1 (2026-06-26)

### Added

- **ColorLUT path escaping**: `emit_filter_option_path` helper in `rust/stoat_ferret_core/src/ffmpeg/video.rs` enforces single-quoted colon-escape (variant 4) for Windows paths in ColorLUT FFmpeg filter args; policy verified across 5×4 matrix of operators and path types (BL-499, PR #650)
- **Animated opacity via geq**: Opacity builder emits `geq` expression for animation-mode projects instead of `colorchannelmixer`; Rust unit tests cover animation-mode detection and expression format (BL-502, PR #651)
- **Event namespace registration**: `render.*` namespace declared in `docs/design/FRAMEWORK_CONTEXT.md` and `AGENTS.md`; declaration-before-use process codified (BL-551, PR #652)
- **Preflight validation**: POST `/render` validates clip count and effect compatibility before enqueueing jobs; `render.preflight_reject` (422) and `render.preflight_warning` structured events fired at HTTP layer; preflight test suite added (BL-551, PRs #652 #653)
- **Render evidence persistence**: `evidence_json` column added to `render_jobs` via Alembic migration; `RenderExecutor.pop_evidence()` captures command args, exit code, stderr tail, output path, output size, and filter script path; evidence saved to repository after job completes (BL-554, PRs #655 #656)
- **Evidence API**: `GET /render/{job_id}/evidence` returns structured execution evidence; gated behind `STOAT_RENDER_EVIDENCE_FULL_ACCESS`; command args redacted (sk-or-v1-* tokens, STOAT_* env var values) before response; OpenAPI schema and TypeScript types regenerated (BL-554, PR #656)
- **RenderGraphTranslator**: Rust `translate.rs` module converts `RenderGraph` to an FFmpeg filter-chain; integrated into render worker and preview path; PyO3 bindings and stubs added (BL-505, PR #657)
- **Chatbot testing workflow**: `docs/design/chatbot-driven-testing/example-workflow.md` documents end-to-end testing approach with SSIM, Sobel edge magnitude, mean luminance validation, and workspace hygiene steps; integrity test suite added (BL-506, PR #658)
- **UAT journey workflows**: UAT journeys for multi-clip render, preflight validation, evidence API, and render-graph translator documented and smoke-tested (PRs #659 #660)

### PRs

#650, #651, #652, #653, #654, #655, #656, #657, #658, #659, #660

### Resolved

BL-499 (ColorLUT path escaping), BL-551 (render preflight validation and event namespace)

### Partially resolved

BL-502 (animated opacity via geq — FFmpeg discharge pending), BL-505 (RenderGraphTranslator — AC-5 pending v088), BL-506 (chatbot testing workflow — AC-2–6 pending v088), BL-554 (render evidence persistence and API — AC-5 pending v088)

---

## v086 — Post-v085 Compliance Riders (2026-06-25)

### Added

- **C4 YAML alignment**: `api-server-api.yaml` updated to align with live OpenAPI on `/api/v1/source` route, `SourceResponse` schema, and `license_info` block; version metadata unified to `0.3.0` across C4 YAML surfaces (BL-546, BL-547, PR #648)
- **Version metadata unification**: `app.py` now reads version via `importlib.metadata.version("stoat-ferret")` instead of a hardcoded literal; `test_version_surfaces_agree` test confirms all surfaces agree (BL-547, PR #648)
- **Gitignore guard comment-bypass fix**: `_active_gitignore_lines()` helper added to `test_hygiene.py`; test now strips comments before scanning active patterns (BL-549, PR #649)
- **CI stray-ref TOML extension**: CI stray-reference grep extended to scan `*.toml` files; `pyproject.toml`/`Cargo.toml` audited — 0 Apache/MIT hits (BL-550, PR #649)

### Fixed

- **uv subprocess portability**: `scripts/check_dependency_licenses.py` replaced `uv run pip-licenses` subprocess with `shutil.which("pip-licenses")` (AC-5 fallback path); Windows-portable across all CI environments (BL-548, PR #649)

### PRs

#648, #649

### Resolved

BL-546 (OpenAPI C4 YAML alignment), BL-547 (version metadata unification), BL-548 (subprocess portability), BL-549 (gitignore guard comment bypass), BL-550 (CI stray-ref TOML extension)

---

## v085 — Post-v084 Compliance and Hygiene Wave (2026-06-24)

### Added

- **C4 API documentation update**: `api-server-api.yaml` updated to AGPL-3.0-or-later; `/api/v1/source` endpoint and `SourceResponse` model documented in C4 YAML (BL-541, PR #642)
- **CI stray-reference YAML scan**: Stray-reference grep extended to scan `*.yaml` and `*.yml` files (BL-541, PR #643)
- **Gitignore orchestration guard assertion**: Test asserts orchestration guard patterns are present in `.gitignore` (BL-543, PR #645)

### Fixed

- **dep-checker test scope**: No-op test replaced with functional assertion; `test_no_arg_prints_usage` added; scope boundary documented (BL-542, PR #644)
- **stray-MIT test portability**: `subprocess.run(["grep", ...])` replaced with Python `re` for Windows portability (BL-544, PR #646)

### PRs

#642, #643, #644, #645, #646

---

## v084 — Post-v083 Compliance Hygiene Wave (2026-06-24)

### Added

- **GUI URL validation**: Validate Source link URL scheme before assigning to GUI href in StatusBar — prevent `javascript:` and other unsafe schemes from reaching `<a href>` (BL-537, PR #630)
- **Source endpoint typed response model**: `SourceResponse` Pydantic model added to `GET /api/v1/source` for strict schema validation and OpenAPI visibility (BL-539, PR #631)
- **C4 docs source router coverage**: C4 code-level docs updated to include `source.py` compliance router and `STOAT_SOURCE_URL` / `STOAT_BUILD_COMMIT` settings introduced in v083 (BL-531, PR #632)
- **Source contract smoke test**: Smoke test for `GET /api/v1/source` contract added to CI coverage (PR #633)
- **Source contract harness guide**: Agent harness documentation updated with source contract verification steps (PR #634)
- **SPDX header gate expanded**: `scripts/check_spdx_headers.sh` updated to scan all `git ls-files`-tracked `.py` and `.rs` files — removes the previous per-directory allowlist (BL-532, PR #635)
- **Manifest-driven license checker**: `scripts/check_dependency_licenses.py` now derives its inventory from `pyproject.toml` rather than a hardcoded list; copyleft detection added (BL-533, PR #636)
- **Bare MIT token detection**: POSIX ERE stray-reference grep extended to catch bare `MIT` license tokens missed by the prior allowlist approach (BL-538, PR #637)
- **Orchestration artifacts removal**: Committed auto-dev orchestration artifacts removed from product repo; `.gitignore` guards added to prevent re-introduction (BL-534, PR #638)
- **Root CHANGELOG redirect**: Stale `CHANGELOG.md` at repo root replaced with a redirect stub pointing to `docs/CHANGELOG.md` (BL-535, PR #639)
- **UAT known-failures registry — Journey 204**: `baseline-uat-failures.json` now registers Journey 204 (export-render) as a known failure with reason and tracking reference; `uat_runner.py` updated to handle legacy dict format (BL-536, PR #640)

### Deferred (pending discharge)

- BL-536 AC-2: `uat_runner.py` exits 0 when only registered journeys fail — requires live headless UAT run
- BL-536 AC-3: Confirmation UAT report lists zero unexpected failures — requires live headless UAT run

### PRs

#630, #631, #632, #633, #634, #635, #636, #637, #638, #639, #640

---

## v083 — AGPL Relicense + Repo Hygiene (2026-06-23)

### License Change

stoat-and-ferret is relicensed to **AGPL-3.0-or-later** from this version onward.

Releases prior to v083 remain under the license terms under which they were
actually distributed. The pre-v083 declaration was mixed (Apache-2.0 LICENSE
file alongside a `license = { text = "MIT" }` declaration in pyproject.toml);
the historical reconciliation is recorded in
docs/legal/historical-license-reconciliation.md (see BL-530).

### Added

- **Sole-ownership audit**: Clearance note at `docs/legal/relicense-ownership-audit.md` establishing sole-copyright provenance for the AGPL relicense gate (BL-521, PR #616)
- **Core license swap**: LICENSE replaced with AGPL-3.0-or-later text; pyproject.toml and Cargo.toml updated to AGPL-3.0-or-later (BL-522, PR #617)
- **Historical license reconciliation**: `docs/legal/historical-license-reconciliation.md` records pre-v083 distribution history and reconciliation verdict — no distributed artefacts pre-v083 (BL-530, PR #618)
- **SPDX header backfill**: All `.py` and `.rs` source files carry `# SPDX-License-Identifier: AGPL-3.0-or-later` and copyright headers (BL-523, PR #620)
- **SPDX CI + pre-commit gate**: `.github/workflows/license-headers.yml` and pre-commit hook enforce SPDX headers on every PR (BL-524, PR #621)
- **AGPL §13 source-offer endpoint**: `GET /api/v1/source` returns `source_url`, `version`, `commit`, `license`; `STOAT_SOURCE_URL` and `STOAT_BUILD_COMMIT` settings (BL-525, PRs #622 #623)
- **Source endpoint UAT step**: UAT step added to `docs/manual/uat-testing.md` for the Source compliance link (Impact-U3, PR #626)
- **CLA guardrail**: `CONTRIBUTING.md`, `CLA.md`, `.github/PULL_REQUEST_TEMPLATE.md`, and `.cla-assistant.json` added for contribution governance (BL-526, PR #627)
- **Dependency license inventory**: `docs/legal/dependency-license-inventory.md` with full transitive dep scan; `scripts/check_dependency_licenses.py` CI enforcement script (BL-529, PR #628)
- **AGPL badge**: README.md includes AGPL-3.0-or-later shields.io badge (BL-527)
- **NOTICE.md**: Project notice file documenting dependency license findings (BL-527)
- **Stray-reference allowlist**: `scripts/license_grep_allowlist.txt` and CI stray-reference check (BL-527)
- **auto-dev directory removal**: Removed rogue `docs/auto-dev/` from product repo; `.gitignore` guard added; hygiene tests added (BL-528, PR #619)

### PRs

#616, #617, #618, #619, #620, #621, #622, #623, #624, #625, #626, #627, #628, #629

---

## v082 — Release 2, Wave 5 Carry-Forward (2026-06-13)

### Added

- **ChromaticAberrationBuilder**: RGB-channel shift optical aberration effect using FFmpeg `rgbashift` filter (BL-453-AC-2, PR #612)
- **Chromatic aberration smoke test**: Parametrized smoke test entry and harness guide row (PRs #613, #614)
- **Animation expression escaping**: `escape_for_filter` helper applied to automation expressions to fix FFmpeg filter-graph comma-parsing errors (BL-502, PR #611)

### Fixed

- **BlurBuilder directional mode**: Replaced non-existent `dblur sigma` option with `avgblur` for correct directional blur output (BL-500, PR #609)
- **NoiseGeneratorBuilder**: Removed non-existent `cellauto 'd'` option; fixed seed parameter handling (BL-501, PR #610)
- **ColorLutBuilder path handling**: Converted backslash separators to forward slashes in Windows LUT file paths (BL-499, PR #608)

### Deferred (FFmpeg-gated / pending discharge)

- BL-499 AC-1/2/3: ColorLutBuilder Windows drive-letter colon escaping — `lut3d=file=C:/path` requires `C\:/path` to avoid filter-graph parser treating `:` as separator
- BL-453 AC-3: ChromaticAberrationBuilder FFmpeg contract test missing — mirror `test_lens_distort_ffmpeg_contract` pattern
- BL-452 AC-4: BlendModeBuilder FFmpeg contract test missing — `test_blend_mode_renders_contract` not yet written
- BL-502 AC-1/2/3: Animation contract tests SKIPPED — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_opacity_scale.py -k animation_renders`
- BL-457 AC-4: Browser UAT headless journey — blocked on BL-480 (qc-status-fail testid resolves to 3 elements)

### PRs

#608, #609, #610, #611, #612, #613, #614, #615

---

## v081 — Release 2, Wave 5: Video FX (2026-06-13)

### Added

- **Automation dispatch refactor**: Generic `automation_filter_template` field on `EffectDefinition` eliminates hardcoded conditionals across all effect builders (PR #594)
- **Blur and sharpen effects**: `BlurBuilder` (Gaussian/directional) and `SharpenBuilder` (unsharp mask) with keyframable radius; 3 contract tests (BL-451, PR #595)
- **Color LUT grading**: `ColorLutBuilder` with 3D LUT application and 3 bundled presets (`cinematic`, `warm_sunset`, `cool_shadows`) (BL-450, PR #597)
- **Keying and compositing**: `ChromaKeyBuilder`, `ColorKeyBuilder`, and `BlendModeBuilder` with 10 blend modes (BL-452, PR #598)
- **Optical distortion**: `LensDistortBuilder` for barrel/pincushion lens distortion (BL-453, PR #599)
- **Procedural generators**: `GradientGeneratorBuilder` and `NoiseGeneratorBuilder` via `lavfi` source (BL-454, PR #600)
- **Opacity and scale animation**: `OpacityBuilder` and `ScaleBuilder` with keyframed fades and slow-zoom envelopes (BL-455)
- **Smoke test coverage**: 10 new smoke tests covering all v081 video FX effects (PR #601)
- **Smoke-test harness guide**: Updated with v081 video FX coverage and discharge commands (PR #602)
- **UAT journeys**: J707–J710 for blur, chroma_key, lens_distort, gradient_generator; J706 for LUT grading (BL-457, PR #603)
- **Acceptance harness**: `tests/acceptance/v081_video_fx_harness.py` with 11 gate tests; Tier-2 checklist updated (PR #604)

### Deferred (FFmpeg-gated)

- BL-450 AC-3: color LUT render contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_color_lut.py -k contract`
- BL-451 AC-4: blur/sharpen render contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_blur_sharpen.py -k contract`
- BL-452 AC-4: keying/blend render contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_keying_blend.py -k contract`
- BL-453 AC-3: lens_distort render contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_optical_distortion.py -k contract`
- BL-454 AC-4: procedural generators render contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_procedural_generators.py -k contract`
- BL-455 AC-4: opacity/scale render contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_opacity_scale.py -k contract`
- BL-450 AC-4: J706 (j_grade) headed UAT
- BL-455 AC-4: automation lane headed UAT (opacity/scale)
- BL-457 AC-2: journey 706 headless — `python scripts/uat_runner.py --headless --journey 706`
- BL-457 AC-3: J-QC-Fail headed — blocked on BL-480 (qc-status-fail / remaster-btn testids)

### PRs

#594, #595, #597, #598, #599, #600, #601, #602, #603, #604, #605, #606

## v080 — Release 2, Wave 4: Editing & Time (2026-06-12)

### Added

- **ReverseBuilder**: Rust+PyO3 reverse effect with 30-second buffer-limit guard; `STOAT_REVERSE_MAX_DURATION_S` configuration variable (BL-444, PR #580)
- **FramerateConvertBuilder**: Rust+PyO3 framerate conversion with blend, optical-flow, and duplicate modes (BL-448, PR #583)
- **FreezeFrameBuilder**: Rust+PyO3 freeze-frame effect; NFR-001 mid-clip composition note in effects guide (BL-449, PR #584)
- **VariableSpeedBuilder**: Rust+PyO3 segmented-concat variable-speed with per-segment pitch control (BL-447, PR #582)
- **Universal range-window / WindowSpec**: `window` parameter on all effects; Pydantic `WindowSpec` model with `mode='after'` validation (BL-446, PR #581)
- **Clip split API**: `POST /clips/{id}/split` endpoint with atomic transaction (INSERT clip_a + INSERT clip_b + DELETE original); `ClipSplitRequest` / `ClipSplitResponse` schemas; GUI `RazorTool.tsx` component (BL-445, PR #586)
- **UAT journey files 701–706**: Journeys for markers, mastering, QC-fail, automation, reverse-split, and grade registered in uat_runner.py; `j_reverse_split.py` rewritten with real API assertions (BL-457, PR #590)
- **Acceptance harness**: `tests/acceptance/uc_media_mps_001_harness.py` for UC-MEDIA-MPS-001 with Tier-2 headed checklist (`docs/manual/tier2-acceptance-checklist.md`) (BL-459, PR #589)
- **Golden QC regression suite**: `tests/qc/fixtures/golden_qc_report.json` regenerated with real FFmpeg measurements; drift detection active (BL-458, PR #588)
- **Smoke test harness guide**: `docs/setup/smoke-test-harness-guide/07-dsp-contract-tests.md` updated with v080 effect types, split endpoint section, and `STOAT_REVERSE_MAX_DURATION_S` discharge procedures (PR #591)
- **STOAT_REVERSE_MAX_DURATION_S**: Configuration reference entries in `docs/setup/04_configuration.md`, `docs/manual/configuration-reference.md`, and `.env.example` (BL-444, PR #585)

### Deferred (FFmpeg-gated)

- BL-444-AC-4: reverse render contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_reverse.py::test_reverse_video_filter_produces_valid_output`
- BL-446-AC-3: window render probe — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_window.py::test_window_render_probe`
- BL-447-AC-1/2/3: variable-speed rendering — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_variable_speed.py -v`
- BL-448-AC-1/2/3: framerate convert rendering — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_framerate.py -v`
- BL-449-AC-3: freeze-frame render validation — `STOAT_TEST_FFMPEG=1 pytest tests/test_effects_freeze_frame.py::test_freeze_frame_produces_valid_output`
- BL-457-AC-2: journey 705 headless run — `python scripts/uat_runner.py --journey 705 --headless`
- BL-457-AC-3: journey 703 headed — blocked on BL-480 (qc-status-fail / remaster-btn testids)
- BL-459-AC-1/2/4: full acceptance harness — `STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/uc_media_mps_001_harness.py`

### PRs

#580, #581, #582, #583, #584, #585, #586, #587, #588, #589, #590, #591, #592

## v079 — Release 2, Wave 3: Sound Design + v078 Repair Rider (2026-06-12)

### Added

- **PanBuilder**: Stereo pan with static positioning and automation envelope; `eval=frame` enforced; `spatial_correlation` added as 12th QC check (BL-437, PRs #570)
- **ConvolutionReverbBuilder**: IR-based reverb via `afir` filter; 3 bundled IRs (`hall_small`, `room_medium`, `plate`) (BL-438, PRs #571, #572)
- **Generator clips**: `clip_type="generator"` + `generator_params` in Clips API; type-validated `ClipCreate` schema; `build_generator_source_filter` Rust dispatch (`aevalsrc`, `sine`) (BL-441, PRs #574, #575)
- **Tone synthesis**: Constant frequency, linear chirp sweep, and binaural beat mode via `aevalsrc` with `eval=frame` (BL-439, PR #576)
- **Loopable beds**: `build_loop_render_command` for seamless crossfaded loops (BL-440, PR #577)
- **SubBassBuilder**: Sub-bass layer generation with duck-on-beat ducking schema (BL-442, PR #577)
- **PitchShiftBuilder**: Formant-preserving pitch shift via `rubberband` filter (BL-443, PR #577)
- **Smoke test coverage**: Generator clip API, QC oracle smoke tests; smoke harness guide updated with Wave-3 discharge commands (PRs #579)

### Fixed

- **QC worker-path assertions**: `RenderService._complete_job` now fetches delivery profile and builds loudness/true-peak assertions dict for `QCService.run_checks`; previously passed null targets (BL-488, PR #565)
- **JobStatus enum rename**: `JobStatus.COMPLETE` → `COMPLETED` with value `"completed"` across 68+ occurrences; eliminates silent state mismatch in GUI and API (BL-490, PR #566)
- **Render plan schema**: `total_duration` required field enforced at preflight; schema aligned with renderer expectations (BL-489, PRs #567, #568)
- **UAT seed extension**: Seed DB includes QC-fail render row for journeys J703/J704 (BL-480, PR #569)
- **ON DELETE CASCADE**: Restored on `clips.project_id` FK after `batch_alter_table` dropped it during generator-clip migration (BL-441, PR #575)

### Deferred (FFmpeg-gated)

- BL-437 ACs 1-4: pan contract tests — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_pan.py -k contract`
- BL-438 ACs 1-3: convolution reverb contract test — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_effects_reverb.py::test_convolution_reverb_contract_ffmpeg`
- BL-439 AC-4: tone synthesis FFmpeg contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_api/test_tone_synthesis.py`
- BL-439 AC-2: automation envelope for tone — static `frequency_end` only; `py_compile_automation` not integrated
- BL-441 AC-2: generator clip render contract — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_api/test_generator_clip.py -k ffmpeg`
- BL-488 ACs 3+5: QC worker-path E2E — `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_render_service_qc.py::TestWorkerQCContractFFmpeg`

### PRs

#565, #566, #567, #568, #569, #570, #571, #572, #574, #575, #576, #577, #579

## v078 — QC Integrity, DSP Correctness & R2 Doc Parity (2026-06-11)

### Added

- **automatable_parameters field**: `automatable_parameters: list[str]` on `EffectResponse`; clients can discover which parameters support automation envelopes (BL-481, PR #555)
- **Preview automation envelope support**: VOLUME effect preview reflects automation envelope via `eval=frame` fix (BL-479+BL-482, PR #553)
- **QA smoke tests**: Automatable-params, worker QC path, and preview automation smoke tests in `tests/smoke/` (PR #556)

### Fixed

- **QC loudness calculation**: Fixed `QCService` ebur128→loudnorm metric mapping that returned null integrated loudness values (BL-476, PR #550)
- **Worker-path QC wiring**: `RenderService` now calls `QCService` after render completes; QC results stored and surfaced via render status (BL-477, PR #551)
- **Deesser parameter normalization**: `DeesserBuilder` frequency converted from Hz to `[0,1]` range before FFmpeg filter string construction (BL-478, PR #552)
- **Multiband compressor threshold normalization**: `MultibandCompressorBuilder` threshold converted from dB to linear before FFmpeg filter string construction (BL-478, PR #552)
- **Volume automation frame evaluation**: `eval=frame` added to volume filter to ensure automation curve is applied per-frame (BL-479+BL-482, PR #553)
- **QC-fail GUI surfaces**: `RenderJobCard` displays QC status badge and remaster button on QC failure; `uat_runner.py` false-green fix (BL-480, PR #562)
- **Pitch stability regression**: Librosa-based pitch stability test corrected (BL-435, PR #554)

### Documentation

- **8 new DSP effects**: Agent docs for NoiseReductionBuilder, DeesserBuilder, DeplosiveBuilder, TimeStretchBuilder, LimiterBuilder, LoudnormBuilder, ParametricEqBuilder, MultibandCompressorBuilder in api-reference, operator-guide, and prompt-recipes (BL-483, PR #559)
- **QC endpoints**: `/qc/run`, `/qc/reports/{id}`, `/render/{job_id}/qc` documented in api-reference and operator-guide (BL-484, PR #560)
- **Delivery profiles CRUD**: `delivery_profiles` CRUD endpoints and name-vs-UUID distinction documented (BL-485, PR #561)
- **C4 documentation**: Routers doc updated, effects count corrected from 9 to 17 across 14 locations (BL-469, PR #558)
- **Smoke-test harness guide**: Updated with new DSP contract test section (PR #557)

### Deferred (FFmpeg-gated / UAT-gated)

- BL-476-AC-4: Golden QC fixture regeneration — `STOAT_TEST_FFMPEG=1 uv run pytest tests/qc/ --update-golden`
- BL-477-AC-3: Worker-path QC E2E — `STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/uc_media_mps_001_harness.py`
- BL-478-AC-1/2: Deesser and multiband FFmpeg behavioral tests — `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/test_voice_repair_ffmpeg.py tests/effects/test_mastering_ffmpeg.py`
- BL-479-AC-1: Volume automation render level — `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/test_mastering_ffmpeg.py::test_volume_automation_level_follows_curve`
- BL-480-AC-1: j_qc_fail headed UAT journey — `python scripts/uat_runner.py --journey j_qc_fail` on Windows with headed Chromium

### PRs

#550, #551, #552, #553, #554, #555, #556, #557, #558, #559, #560, #561, #562, #563

## v077 — Release 2, Wave 2: Mastering + Voice Prep (2026-06-09)

### Added

- **Voice repair effects**: NoiseReductionBuilder, DeesserBuilder, DeplosiveBuilder, TimeStretchBuilder Rust builders with PyO3 bindings and effect registry integration (BL-428/429/430/431, PRs #535–#537)
- **Mastering effects**: LimiterBuilder, LoudnormBuilder, ParametricEqBuilder, MultibandCompressorBuilder Rust builders with PyO3 bindings (BL-432/433/434/435, PRs #538–#542)
- **Volume automation envelopes**: Envelope support on VOLUME effect (PR #540)
- **DSP smoke test coverage**: FFmpeg-gated test files for voice repair, mastering, and mixdown; `tests/effects/test_voice_repair_ffmpeg.py`, `test_mastering_ffmpeg.py`, `test_mixdown_ffmpeg.py` (BL-436, PRs #543–#544)
- **Golden QC regression suite**: `--update-golden` flag, real QC call in `test_qc_regression.py`, golden fixture infrastructure (BL-458, PR #546)
- **Browser UAT journeys R2**: Playwright journey bodies for journeys 701–706 in `tests/uat/journeys/j_*.py` (BL-457, PR #547)
- **UC-MEDIA-MPS-001 acceptance harness**: 15-assertion acceptance class with ≥14/17 OC threshold in `tests/acceptance/uc_media_mps_001_harness.py` (BL-459, PR #548)
- **Smoke test harness guide**: Added `docs/setup/smoke-test-harness-guide/07-dsp-contract-tests.md` (PR #545)

### Fixed

- Fixed UAT runner false-green: `run_journey()` returns non-pass when implementation absent; exit code reflects not-run journeys (BL-473, PR #534)
- Added stub_gen wholesale-copy trap warning co-located at all invocation points in AGENTS.md (BL-471, PR #533)

### Deferred (FFmpeg-gated / UAT-gated)

31 ACs deferred pending FFmpeg or UAT environment — see `source-to-outcome-evidence.json` for discharge commands. Key items: BL-428–436 behavioral render tests (FFmpeg), BL-458-AC-2/4 golden drift detection (FFmpeg), BL-457-AC-2 browser UAT journeys (headed Playwright), BL-459-AC-1/2/4 acceptance harness (FFmpeg). BL-458-AC-1 weakened (placeholder fixture; real fixture requires `STOAT_TEST_FFMPEG=1` discharge run).

### PRs

#533, #534, #535, #536, #537, #538, #539, #540, #541, #542, #543, #544, #545, #546, #547, #548

## v076 — Release 2, Wave 1: Verify & Deliver (2026-06-08)

### Added

- **QC infrastructure**: QC namespace and module structure, Rust FFmpeg-output parsers (stub with deferred FFmpeg gate), QCService 11-pass analysis orchestrator, `/qc` API endpoint, QC smoke tests
- **Delivery profiles**: `DeliveryProfile` model and database table, `/delivery-profiles` CRUD API, QC-gated export pipeline (blocks export on QC failures), render schema extended with `QC_FAILED` status
- **Chapter and clip metadata embedding**: Metadata passthrough architecture and embedding hooks (FFmpeg-gated ACs deferred)
- **QC-as-test layer**: OC→QC assertion mapping infrastructure (14/17 OC outcomes mapped), golden render and QC regression fixture infrastructure (FFmpeg-gated golden outputs deferred)
- **Acceptance harness scaffold**: Chatbot scenario acceptance tests (4 ACs complete), browser UAT journeys for Release 2 use cases (6+ headless Playwright journeys), UC-MEDIA-MPS-001 full acceptance harness scaffold

### Changed

- Render schema: added `QC_FAILED` as a terminal render status

### Deferred (FFmpeg-gated)

The following ACs are deferred pending FFmpeg infrastructure: BL-423 (QC parsers, ACs 1–5), BL-424 (QCService AC-5), BL-426 (chapter metadata embedding, ACs 1–4), BL-427 (OC mapping, ACs 2–3), BL-458 (golden regression, ACs 2, 4), BL-459 (acceptance harness, ACs 1, 2, 4). BL-457-AC-2 deferred pending headed Playwright on Windows.

### PRs

#526, #527, #528, #529, #530, #531

## [v075] — Release 2, Wave 0 — Enablers (2026-06-07)

### Added
- Added `compile_automation` Rust function with 4 curve kinds (linear, ease-in, ease-out, ease-in-out), proptest property suite (50 tests), and PyO3 binding `compile_automation(automation: Automation) -> str` (BL-418, PR #516)
- Added `AutomationEnvelope` / `AutomationKeyframe` Pydantic schemas, `validate_with_automation()` registry method, and `filter_preview: str | None` field to `EffectApplyResponse`; envelopes compile to nested `if(lt(t,...))` FFmpeg expressions (BL-420, PR #517)
- Added 4 automation envelope smoke tests to `tests/smoke/test_effects.py` (BL-420, PR #518)
- Added Release 2 test scaffolding: `tests/qc/` package with `assert_qc_check()` helper; `tests/chatbot/scenarios/r2_scaffold.py` chatbot runner hook; `tests/uat/journeys/r2_skeleton.py` UAT journey registered as J206 (BL-421, PR #519)
- Added project timeline markers CRUD REST API (`POST/GET/PATCH/DELETE /api/v1/projects/{pid}/markers`), `project_markers` Alembic migration with FK CASCADE, non-overlapping section marker validation (BL-419, PR #520)
- Added 4 markers smoke tests to `tests/smoke/test_markers.py` (BL-419, PR #521)
- Added `sample_rate` and `bit_depth` project audio baseline fields with `Literal[44100, 48000, 96000]` / `Literal[16, 24, 32]` Pydantic validation, PRAGMA-idempotent Alembic migration, and `RenderSettings` Rust `audio_sample_rate: Option<u32>` / `with_audio()` builder (no existing `new()` call sites changed) (BL-422, PR #522)
- Added 3 audio baseline smoke tests to `tests/smoke/test_project_workflow.py` (BL-422, PR #523)

### Deferred
- 3 behavioral ACs pending FFmpeg environment:
  - BL-418-AC-6: FFmpeg contract test for rendered automation envelope output; discharge: `STOAT_TEST_FFMPEG=1 uv run pytest tests/test_contract/test_automation_contract.py`
  - BL-421-AC-1: Golden QC fixture content; discharge: run with `STOAT_TEST_FFMPEG=1` after QCService is implemented in a downstream Release 2 feature
  - BL-422-AC-3 (FR-003-AC-5): Rendered audio output at configured sample rate/bit depth; discharge: `STOAT_TEST_FFMPEG=1 uv run pytest` with ffprobe verification

## [v074] — Agent-Surface Accuracy & Architecture Hygiene (2026-06-06)

### Fixed
- Fixed operator-guide.md render payload examples to include `render_plan` wrapper; removed stale per-job `output_path` field from WebSocket poll-response shape (BL-375, PR #504)
- Fixed 03_api-reference.md missing `partial_file_detected` field in RenderJob schema section (BL-464, PR #505)
- Fixed agent-doc recipe examples showing outdated render response shape and incorrect PREFLIGHT_FAILED claim (BL-402, PR #504/#505)
- Hoisted render settings validation to router level: `GET /render` returns 422 with `PREFLIGHT_FAILED` when `render_plan.settings` key is absent or malformed, before any job is created (BL-465, PR #503)

### Added
- Added `GET /api/v1/projects/{project_id}/clips/{clip_id}` and `GET /api/v1/projects/{project_id}/clips/{clip_id}/effects` endpoints (BL-409, PR #509)
- Added 8 API ergonomics fixes: `ClipResponse.effects` defaults to `[]`, `waveform_id` is now an async-id string, `EFFECT_NOT_FOUND` enumerated in error schema, batch quality naming corrected, and 4 additional papercuts (BL-405, PR #508)
- Added optional `VersionCreateRequest` body to `POST /versions`; body-less POST auto-snapshots the current timeline server-side (BL-404, PR #506)
- Added `subtitle_count` and `data_count` fields to `VideoResponse` schema; backed by Alembic migration on video table; populated via FFmpeg probe (BL-408, PR #510)
- Added `STOAT_RENDER_STUCK_THRESHOLD_SECONDS` bounds documentation (60–3600) to `docs/setup/04_configuration.md` and `docs/manual/configuration-reference.md` (BL-414, PR #507)
- Added `StaleRenderSweeper` to C4 component and code-level docs; updated smoke-test inventory from 84 to 191 tests across 37 files (BL-399, BL-400, PR #511)
- Added `timeout=900` to `run_journey()` subprocess.run with `TimeoutExpired` handler in `scripts/uat_runner.py` (BL-398, PR #512)
- Added smoke tests for v074 behavioral changes: settings-absent 422, render settings validation, subtitle/data stream counts (MANDATE_A, PR #513)
- Updated smoke-test harness guide for v074 additions and discharge procedures (MANDATE_B, PR #514)

### Deferred
- 2 behavioral ACs pending FFmpeg environment and corpus:
  - FFmpeg-gated (2 ACs): BL-408 AC-1 (`test_sintel_subtitle_count`) and AC-2 (`test_bbb_data_stream_count`); discharge: `STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/test_video_auxiliary_streams.py` with Sintel MKV and BBB MOV corpus

## [v073] — Render Correctness & Test-Coverage Discharge (2026-06-06)

### Fixed
- Hoisted `total_duration` preflight validation before the noop/real-mode split in `RenderService.submit`; both modes now validate `total_duration` equally (BL-460, PR #498)
- Fixed `build_command_for_job` missing `-progress pipe:1` flag; concurrent stderr drain now runs alongside the stdout readline loop, preventing blocking under real-mode render (BL-394, PR #501)
- Fixed Python 3.13 `async_executor` race: replaced `communicate()` with `process.wait()` plus a dedicated stderr reader; eliminates `DeprecationWarning` under `-W error::DeprecationWarning` (BL-393, PR #501)
- Repaired `test_concurrent_renders_have_distinct_output_paths` and `test_render_completed_event_contains_output_path` broken by the preflight hoist remediation pass (BL-461, PR #500)

### Added
- Added `ConfigDict(extra="forbid")` to `CreateRenderRequest` and `RenderPreviewRequest`; unknown fields now return HTTP 422 (BL-417, PR #499)
- Added `test_partial_file_cancel`, `test_render_progress_increments`, and `test_preview_no_deadlock` smoke tests; discharges BL-415 and BL-394 behavioral ACs under `STOAT_TEST_FFMPEG=1`, and BL-393 behavioral AC on Python 3.13 (BL-462, PR #501)

### Documentation
- Corrected `docs/manual/smoke-test-harness.md` discharge procedures: fixed `uv run pytest` invocation syntax, corrected test keywords, added BL-415-AC-3 FFmpeg-gated discharge entry (BL-463, PR #502)

### Deferred
- 1 behavioral AC pending environment-specific test infrastructure:
  - FFmpeg-gated (1 AC): BL-403 AC-3 (concurrent-no-contention file validity); discharge: `STOAT_TEST_FFMPEG=1 uv run pytest tests/smoke/ -k test_concurrent_renders_have_distinct_output_paths`

**Summary:** Render Correctness & Test-Coverage Discharge — 3 themes (render-correctness, render-data-correctness, render-test-coverage), 9 features, PRs #498–#502, 2645 passing tests. Closes BL-460, BL-393, BL-394, BL-415, BL-417, BL-461, BL-462, BL-463.

## [v072] — Render Reliability & Data Integrity (2026-06-05)

### Fixed
- Eliminated TOCTOU race between cancel and render completion: added CAS re-read after `executor.cancel()` returns; duplicate terminal events suppressed via `CancelPreemptedError`; returns 409 for cancel-on-terminal-state (BL-412, PR #483)
- Fixed stale `payload.status` in WS terminal events: `_broadcast_event` receives `target_status` kwarg sourced after `update_status`; REST and WS status fields are now always in agreement (BL-401, PR #484)
- Fixed `render_completed` WS event missing `output_path` field: extended `_broadcast_event` with `output_path` kwarg; TypeScript interface updated to `string | null` (BL-411, PR #487)
- Fixed concurrent renders sharing the same output path: render job now includes a 12-char UUID token in the output filename; each job gets a distinct, collision-free path (BL-403, PR #485)
- Fixed proxy failure path: added odd-dimension rounding (even-pixel clamp), last-500-bytes stderr capture for accurate FFmpeg error messages, and `PROXY_FAILED` WS terminal event on proxy error (BL-406, PR #490)
- Fixed SQLite foreign key enforcement never active: `PRAGMA foreign_keys=ON` added to all connection setup paths; `DELETE /videos/{id}` returns 409 when clips reference the video (BL-413, PR #491)
- Fixed Pydantic extra-field silent drop on request bodies: `ConfigDict(extra="forbid")` applied to all `*Create`/`*Update`/`*Request` schemas; unknown fields now return HTTP 422 (BL-407, PR #492)
- Fixed `POST /timeline/clips` acting as upsert: duplicate clip placement now returns 409 with the existing placement in the error body (BL-410, PR #493)

### Added
- Added `partial_file_detected` bool field to `RenderJob` model and API schema: set to `true` when a cancel race leaves a partial output file on disk; Alembic migration included (BL-415, PR #486)
- Added concurrent stderr drain to render executor: `_drain_stderr` asyncio task runs alongside stdout readline loop; prevents blocking; accumulated stderr logged at error level (BL-394, PR #488)
- Added `VIDEO_DELETED` and `CLIP_DELETED` WebSocket events: `DELETE /videos/{id}` and `DELETE /projects/{pid}/clips/{cid}` broadcast WS events on success; `timeline.duration` recomputed on clip deletion (BL-416, PR #494)
- Added smoke test harness guide (`docs/manual/smoke-test-harness.md`): documents `STOAT_TEST_FFMPEG=1` discharge procedures for FFmpeg-gated deferred ACs and Python 3.13 environment requirements (PR #495)
- Added preview lifecycle smoke test verifying HLS session lifecycle against real video files; Python 3.13 behavioral ACs deferred to UAT (BL-393, PR #489)
- Extended smoke tests: WS event assertions, `output_path` assertions, and FK guard assertions added to `tests/smoke/`

### Deferred
- 6 behavioral ACs pending environment-specific test infrastructure:
  - FFmpeg-gated (4 ACs): BL-394 AC-2/AC-3 (progress increment + WS events), BL-403 AC-3 (concurrent-no-contention file validity), BL-415 AC-3 (mid-encode cancel integration); discharge: `STOAT_TEST_FFMPEG=1 pytest tests/smoke/`
  - Python-3.13-gated (2 ACs): BL-393 AC-1/AC-2 (preview end-to-end + manifest endpoint); discharge: `python3.13 -m pytest tests/smoke/`
  - Discharge procedures documented in `docs/manual/smoke-test-harness.md`

**Summary:** Render Reliability & Data Integrity — 4 themes (render-state-integrity, render-execution-and-media-reliability, data-correctness, quality-and-testing), 14 features, PRs #483–#495, 2639 passing tests. Closes BL-393, BL-394, BL-401, BL-403, BL-406, BL-407, BL-410, BL-411, BL-412, BL-413, BL-415, BL-416.

## [v071] — UAT Stability, Evidence Relocation & Architecture Documentation (2026-06-02)

### Fixed
- Fixed `uat_runner.py` aggregator silently zeroing J503 step counts: renamed journey key from `uat_journey_503` to `aggregator_journey` to match the class name in `tests/uat/uat_journey_503.py`, ensuring aggregator results are correctly captured in `uat-report.json` (BL-382, PR #478)
- Fixed `uat_journey_604` and `uat_journey_605` hanging indefinitely in headed mode: replaced unbounded `Popen` subprocess execution with bounded timeout handling; added `test_uat_subprocess_timeout.py` smoke test to prevent regression (BL-381, PR #480)

### Changed
- Relocated UAT evidence output from `uat-evidence/` to `testing-evidence/uat-evidence/` for consistent test artifact organization under the `testing-evidence/` tree; updated `scripts/uat_runner.py`, `tests/uat/conftest.py`, and all documentation references (BL-383, PR #479)

### Documentation
- Refreshed `docs/C4-Documentation/c4-component-web-gui.md` for v067/v068 GUI render additions: documented `useRenderModal` hook, `ErrorBoundary` component, and updated render-related component relationships reflecting changes from PRs #443–#444 (BL-380, PR #481)
- Verified design-phase path validation: confirmed `persist_drafts.py` correctly validates all design output paths against expected directory structure; no code changes required (BL-379, artifact only)

### Deferred
- 5 behavioral ACs across BL-381, BL-382, BL-383 pending live Windows headed UAT run: J605 completes within 600s (BL-381 AC-2), J604/J605 `steps_total > 0` (BL-381 AC-6), J503 `steps_total > 0` in uat-report (BL-382 AC-2/AC-3), evidence at `testing-evidence/uat-evidence/{TS}/` (BL-383 AC-5)

**Summary:** UAT Stability, Evidence Relocation & Architecture Documentation — 2 themes (uat-stability, architecture-documentation), 5 features, PRs #478–#481, 2616 passing tests. Closes BL-379, BL-380, BL-381, BL-382, BL-383.

## [v070] — API Contract Hygiene, Documentation Accuracy & Render Recovery (2026-05-29)

### Added
- Enforced quality enum validation on batch render requests (`BatchJobConfig.quality` now `Literal["draft","standard","high"]`); default changed from `"medium"` to `"standard"`; GUI batch panel updated to match (BL-397, PR #470)
- Added recursion guard to scan endpoint: `recursive=true` on paths with subdirectories returns HTTP 400 `RECURSIVE_SCAN_FORBIDDEN`, preventing BL-378 directory commingling regression (BL-391, PR #472)
- Added `StaleRenderSweeper` background task: detects render jobs stuck in `status='running'` beyond a configurable threshold and transitions them to `status='failed'`, reducing MTTR from hours to seconds; adds `STOAT_RENDER_STUCK_THRESHOLD_SECONDS` setting (BL-389, PR #476)

### Documentation
- Documented empty-PUT timeline clearing behavior in `operator-guide.md` with data-loss warning; added smoke test verifying `PUT /timeline []` deletes all tracks (BL-387, PR #471)
- Synced Pattern 5 event envelope with five-field reality: added `event_id` to description and all five JSON examples; added cross-reference to `ws-event-vocabulary.md` (BL-385, PR #473)
- Documented error response envelope shapes in `03_api-reference.md`: app-level dict vs Pydantic list shapes with Python parsing guide; added cross-references from `operator-guide.md` and `prompt-recipes.md` (BL-386, PR #474)
- Disambiguated `fade` transition (xfade) from `video_fade` effect in effects documentation with explicit "distinct from" language (BL-392, PR #475)

**Summary:** API Contract Hygiene, Documentation Accuracy & Render Recovery — 3 themes (api-contract-hygiene, documentation-accuracy, render-recovery), 7 features, PRs #470–#476, 2616 passing tests. Closes BL-385, BL-386, BL-387, BL-389, BL-391, BL-392, BL-397.

## [v069] — Render & Preview Reliability + Agent Doc Accuracy (2026-05-28)

### Fixed
- Eliminated concurrent `StreamReader` race in `async_executor.py` using exclusive stderr ownership and bounded `asyncio.wait`; added `InvalidTransitionError → HTTP 409` handler in preview router (BL-393, BL-395, PR #461, PR #462)
- Added `asyncio.Lock` in `RenderService.submit_job` for noop serialization; added `-progress pipe:1` flag to FFmpeg command builder; wired project `output_width`/`output_height` through render pipeline with 1920/1080 defaults (BL-388, BL-390, BL-394, PR #463, PR #464, PR #465)

### Documentation
- Documented `render_plan` JSON schema with field descriptions and JSON string format correction in `prompt-recipes.md` (BL-375, PR #466)
- Added recursive parameter explanation with true/false variants to Recipe 1 in `prompt-recipes.md` (BL-384, PR #467)
- Added Pattern 6 (Preview Lifecycle) to `ai-integration-patterns.md` documenting full preview session lifecycle and API surface (BL-396, PR #468)

### Deferred
- 4 behavioral ACs pending real-FFmpeg smoke test discharge: FFmpeg progress reporting (BL-394 AC-1), output dimensions in FFmpeg command (BL-390 AC-2), async executor behavior under real FFmpeg load (BL-393 AC-1 and AC-3)

**Summary:** Render & Preview Reliability + Agent Doc Accuracy — 3 themes (preview-subsystem-repair, render-reliability, agent-documentation-accuracy), 8 features, PRs #461–#468, 2615 passing tests. Closes BL-375, BL-384, BL-388, BL-390, BL-393, BL-394, BL-395, BL-396.

## [v068] — Agent Doc Accuracy, GUI Render, Repo Hygiene, Framework Guardrails (2026-05-22)

### Fixed
- Corrected status tokens, effect types, and documentation consistency across docs/manual files (BL-358, PR #455)
- Added render_plan derivation to payload examples; corrected replay heartbeat documentation for Last-Event-ID anchors (BL-375, BL-376, PR #456)

### Added
- PyO3 0.26 enum non-hashability guardrail (`str()` workaround) and encoder_cache Phase-7-managed table guard pattern added to AGENTS.md and FRAMEWORK_CONTEXT.md (BL-367, BL-368, PR #459)

### Documentation
- Updated C4 code-level documentation for v067/v068 render changes: useRenderModal hook, ErrorBoundary component, render_plan field (BL-377, PR #457)
- Restructured videos/ directory from flat layout to categorized subdirectories; updated scan callers to non-recursive (BL-378, PR #458)
- Auto-dev process documentation updates including path-validation warning and source-correction ledger improvements (auto-dev-mcp PR #838)

**Summary:** Agent documentation accuracy hardening, GUI render contract fixes, repository directory hygiene, and framework process guardrails. 4 themes (agent-doc-accuracy, gui-render-path, repo-hygiene, framework-guardrails), 9 features, PRs #455–#459 + auto-dev-mcp #838, 2584 passing tests. Addresses BL-358, BL-367, BL-368, BL-375–BL-378.

## [v067] — Render-Submit Contract Completion & Doc/Tooling Integrity (2026-05-20)

### Added
- GUI `StartRenderModal` fetches timeline on project selection and constructs `render_plan.total_duration` in POST body, eliminating 422 failures in noop mode (BL-371, PR #443)
- `ErrorBoundary` wraps `RenderPage` with structured error detail extraction, preventing React white-screen crashes on 4xx responses (BL-372, PR #444)
- Smoke tests verify noop render returns 201, job queue visibility, and status polling to discharge deferred render-contract ACs (BL-375, PR #445)
- `BatchRenderUser` in `locustfile.py` generates RFC 4122 UUIDs for `project_id`, enabling valid load test execution (BL-365, PR #447)

### Fixed
- Corrected heartbeat-replay contradiction in `ai-integration-patterns.md` and `operator-guide.md`; heartbeats now documented as valid `Last-Event-ID` anchors (BL-376, PR #448)
- UAT `uat_journey_604` Playwright test path normalized via `.as_posix()`, enabling keyboard-navigation tests on Windows CI (BL-373, PR #452)
- Removed stale `journey-501` entry from `baseline-uat-failures.json` after BL-371/372 fixes resolved the underlying defect; CI confirmed PASS (BL-374, PR #453)

### Documentation
- Updated operator guide with canonical render test loop including `render_plan` derivation rule (BL-371, PR #446)
- Updated C4 architecture documentation for v066 WebSocket replay and job-retention infrastructure (`_BROADCAST_COUNTER`, `_replay_buffer`, `JOB_RETENTION_SECONDS`, `submitted_at`, `render_repository`) (BL-370, PR #449)
- Added PyO3 0.26 enum non-hashability guardrail to `AGENTS.md` with `str()` workaround (BL-367, PR #450)
- Documented `encoder_cache` as Phase-7-managed table with `sqlite_master` existence guard pattern in `FRAMEWORK_CONTEXT.md` (BL-368, PR #451)
- Added path-validation warning to design-phase source-intent-ledger templates; executor templates now read prior `source_correction` fields (BL-369, PR #830)

**Summary:** Render-Submit Contract Completion & Doc/Tooling Integrity — 3 themes (render-submit-contract-completion, agent-and-architecture-doc-accuracy, uat-and-design-tooling-integrity), 12 features, PRs #443–#453 + #830, 2581 passing tests. Closes BL-365, BL-367–BL-376.

## [v066] — WebSocket Reconnect & Replay Contract (2026-05-17)

### Fixed
- Replace per-scope `event_id` counters with a global monotonic counter; buffer heartbeats in replay buffer so reconnecting clients receive all missed events (BL-356, PR #434)
- Include render jobs in `system/state` `active_jobs` response; add terminal pruning to `list_jobs()` so the endpoint never returns stale completed jobs (BL-357, PR #437)

### Added
- WebSocket replay smoke tests for global-counter semantics, cross-scope isolation, and heartbeat anchor assertions (BL-356, PR #436)
- System/state smoke tests for terminal pruning, render job visibility, and AC-5 recovery (BL-357, PR #439)

### Documentation
- Correct `ws-event-vocabulary.md` and `prompt-recipes.md` for global-counter replay contract (BL-356, PR #435)
- Fix `operator-guide.md` and `prompt-recipes.md` reconnect-recovery guidance for render jobs (BL-357, PR #438)
- Update smoke-test-harness-guide for v066 WebSocket replay and system/state test sections (BL-356, BL-357, PR #440)

**Summary:** WebSocket Reconnect & Replay Contract — 2 themes (event-id-replay-contract, system-state-recovery-surface), 7 features (BL-356 global counter + replay buffer + WS smoke tests + docs, BL-357 render visibility + terminal pruning + system/state smoke tests + docs), PRs #434–#440, 2581 passing tests.

## [v065] - 2026-05-17

### Fixed
- Fix EncoderType `repr` serialization so `encoder_type` field in `/api/v1/version` returns `"h264"` / `"h265"` instead of `"EncoderType.H264"` (BL-360, PR #430)
- Add Alembic migration to clear poisoned `encoder_cache` rows written with the broken repr values (BL-360, PR #430)
- Bypass queue enqueue for noop render jobs to prevent worker race on job-not-found lookup (BL-355, PR #429)

### Added
- Render submit semantic preflight: validates `project_id` existence and returns `422` before enqueuing, eliminating silent downstream failures (BL-355, PR #427)
- `app_sha` field in `/api/v1/version` resolved at runtime from git HEAD SHA, enabling deterministic smoke-test identity assertions (BL-362, PR #431)
- Smoke test assertions for render validation, noop contract, `encoder_type` serialization, and `app_sha` identity (BL-355/360/362, PR #432)
- Smoke-test harness guide updated with v065 render validation and noop contract sections (PR #433)

**Summary:** Deterministic-Mode Correctness & Render Observability — 3 themes (render-correctness, encoder-version-observability, smoke-and-harness-coverage), 6 features (BL-355 render preflight + noop ownership, BL-360 encoder_type serialization fix + Alembic cache clear migration, BL-362 app_sha runtime identity + version endpoint, smoke test coverage + harness guide), PRs #427–#433, 2578 passing tests.

## [v064] - 2026-05-16

### Fixed
- Corrected render status namespace in operator-guide.md and prompt-recipes.md (`status == complete` → `"completed"`; scan/async jobs correctly use `"complete"`)
- Replaced non-existent `brightness` effect type with `volume` in prompt-recipes.md (4 occurrences)
- Replaced non-existent `fade` effect type with `video_fade` in operator-guide.md
- Rewrote Pattern 5 in ai-integration-patterns.md to document Last-Event-ID replay (removed false denial statements)
- Rewrote test_hygiene.py to enforce endpoint-family-aware namespace rules (DOC_FAMILY classification)
- Scoped wait-for-render.py docstring to generic queue jobs only; added 404 guard with redirect to render endpoint
- Clarified /render/preview as stateless and project-blind in example-workflow.md
- Verified and closed BL-351 (v062 hotfix data cleanup)

## [v063] — 2026-05-15

### Documentation

- Fix response type labels (`JobStatusResponse` → `RenderJobResponse`) and status tokens (`"complete"` → `"completed"`) in prompt-recipes.md and five additional docs/manual files; add regression test in tests/test_hygiene.py (Theme 1, Feature 001, BL-353, PR #415)
- Align render_jobs ordering in FRAMEWORK_CONTEXT.md with code implementation (Theme 1, Feature 002, BL-352, PR #416)
- Correct stale v058 retrospective narrative about STOAT_RENDER_WORKER_ENABLED flag removal (Theme 1, Feature 003, BL-354)
- Update C4 API schemas to include encoder field introduced by v060 (Theme 1, Feature 004, BL-350, PR #417)

### Changed

- Rename `effect_name` → `effect_type` in thumbnail request schema, smoke test payloads, and harness guide (Theme 2, Features 005–007, BL-349, PR #418)

**Summary:** Documentation audit fixes (response type labels, status tokens, C4 encoder field, render_jobs ordering) + API field rename (effect_name → effect_type). 2 themes, 7 features, PRs #415 #416 #417 #418.

## [v062-hotfix] - 2026-05-08

### Repository Hygiene Follow-up (BL-351)

Closes the residual gap flagged by the v062 retrospective (BL-346 AC#1) and removes the lone fixture that was blocking a wildcard `/data/*` ignore rule.

### Changed
- Move `data/baseline-uat-failures.json` to `tests/fixtures/baseline-uat-failures.json` so `data/` contains only runtime artifacts. Update `KNOWN_FAILURES_REGISTRY` constant in `scripts/uat_runner.py` and the two references in `docs/manual/uat-testing.md`.
- Replace the per-path `data/waveforms/`, `data/previews/`, `/data/thumbnails/` entries in `.gitignore` with a single wildcard `/data/*` rule, plus belt-and-braces explicit entries for `stoat.db`, `stoat.db-wal`, `stoat.db-shm`.

### Removed
- Untrack stale `data/migration_backups/migration_2026-04-22T12_16_40.db` (`git rm --cached`); migration backups are now covered by the wildcard rule.

## [v062] - 2026-05-07

### Documentation
- Update development setup guide with fixture bootstrap model (Theme 1, Feature 001, PR #409)
- Update runbook with fixture model, clarify scripts, verify BL-347 (Theme 1, Feature 002, PR #410)
- Update FRAMEWORK_CONTEXT.md and C4 diagrams with fixture lifecycle (Theme 2, Feature 003, PR #411)
- Add fixture lifecycle section to smoke test harness guide (Theme 2, Feature 004, PR #412)

**Summary:** Repository Hygiene — Documentation of fixture lifecycle and verification of artifact untracking. 2 themes (developer-facing-documentation, architecture-reference-documentation), 4 features, 60/60 acceptance criteria met.

## [v061] - 2026-05-07

### Fixed
- Fix npx path resolution on Windows for UAT runner (Theme 1, Feature 001)
- Fix render payload validation to match API contract (Theme 1, Feature 002)

### Verified
- Smoke test fixture integrity confirmed against current codebase (Theme 2, Feature 003)
- Sample project documentation aligned with public render_plan vocabulary (Theme 2, Feature 004)

**Summary:** Tooling Hygiene — Fix script-layer issues blocking Windows UAT and canonical seed workflows. 2 themes, 4 features, 18/18 acceptance criteria met.

## [v060] - 2026-05-06

### Render API Contract Repair, Asyncio Safety, Repository Hygiene, Architecture Refresh

v060 delivers critical render API vocabulary fixes enabling agent automation, Python 3.10 stability improvements, repository hygiene enforcement, and comprehensive documentation refresh across framework context, C4 architecture, and naming consistency audits.

**Themes:** 4 (render-api-contract-repair, asyncio-safety, repository-hygiene, documentation-refresh)
**Features:** 11/11 complete
**Quality:** 38/39 ACs met, 0 regressions, 2543 tests passing

**Key Outcomes:**

- **Render API vocabulary translation**: Added public vocabulary (draft | standard | high) mapping to FFmpeg presets (veryfast | medium | slow), resolving agent request validation failures that blocked automated render workflows. Extended `/render/formats` with encoder field enabling codec→encoder discovery.

- **Python 3.10+ asyncio stability**: Replaced 65 deprecated `asyncio.get_event_loop().run_until_complete()` calls with `asyncio.run()`, eliminating DeprecationWarning on Python 3.10+ and RuntimeError on 3.13+. Fixed 3 bare `await task` patterns in shutdown handlers with bounded `asyncio.wait()`, eliminating Python 3.10 indefinite stall risk (LRN-406).

- **Database lifecycle and git hygiene**: Established clean seed fixture at Alembic head with copy-on-absent bootstrap logic for fresh checkouts. Removed 299 thumbnail files and runtime database files from git tracking. Fixed cross-platform Windows UAT npx resolution via `shutil.which()`.

- **Framework context documentation**: Documented implicit render_jobs API ordering constraint for reproducible queue semantics. Refreshed C4 architecture diagrams to reflect v038–v057 feature additions (13→17 stores, 7→9 migrations). Conducted comprehensive effect_name vs effect_type naming audit, recommending standardization.

**PRs Merged:**
- #394: quality-preset-translation — Public vocabulary translation layer for render API
- #395: codec-encoder-bridge — Encoder discovery in /render/formats endpoint
- #396: seed-render-plan-fix — Synchronize seed script with new render API contract
- #397: asyncio-deprecation-fix — Replace deprecated event loop patterns
- #398: cancel-await-audit — Fix Python 3.10 cancel-await indefinite stall risk
- #399: database-fixture-lifecycle — Establish clean seed fixture and bootstrap logic
- #400: thumbnails-git-cleanup — Remove 299 thumbnail files from git tracking
- #401: uat-windows-npx-fix — Cross-platform npx resolution via shutil.which()
- #402: framework-context-ordering — Document render_jobs ordering constraint
- #403: c4-documentation-refresh — Update C4 diagrams reflecting v038–v057 changes
- #404: effect-name-audit — Audit effect_name vs effect_type, recommend standardization (BL-349 filed for v061+)

**Notes:**
- Feature 001 (quality-preset-translation) accepted one AC deviation (FR-001d) for backward compatibility. Field has `default="standard"`, allowing omission while maintaining default behavior.
- Follow-on backlog item BL-349 filed for v061+: standardize `effect_name` → `effect_type` in API schemas (low risk, high consistency payoff).

## [v059] - 2026-05-06

### Operator-Guide Audit and Repair

Operator-Guide Audit and Repair — documentation-only version fixing schema and endpoint drift in canonical agent workflow documentation (zero risk tier). Corrected field names, retracted undocumented dry-run shortcut, repaired render observability docs, and fixed timeline-clip workflow documentation to match the actual API.

**Themes:** 2 (operator-guide-doc-repair, smoke-test-verification)  
**Features:** 6/6 complete (effect-field-rename, dry-run-retraction, render-observability-fix, timeline-clip-workflow-fix, smoke-payload-audit, smoke-harness-guide-update)  
**Quality:** 35/36 acceptance criteria met (1 N/A by design), 0 regressions, 2543 tests passing

**Key Outcomes:**
- Fixed effect-apply field name from `name` to `effect_type` in operator-guide.md and api-reference.md (PR #389, BL-344)
- Retracted undocumented `render_plan` `dry_run` shortcut; documented `STOAT_RENDER_MODE=noop` alternative (PR #390, BL-342)
- Replaced render `/api/v1/jobs/{id}/wait` with correct `/api/v1/render` polling pattern in operator-guide (PR #391, BL-341)
- Overhauled timeline-clip workflow documentation to match actual API structure (PR #392, BL-343)
- Verified smoke-test payloads and harness guide accuracy (smoke-test-verification theme)

**PRs Merged:**
- #388: v058 closure
- #389: Effect field rename fix (BL-344)
- #390: Dry-run retraction and STOAT_RENDER_MODE=noop documentation (BL-342)
- #391: Render observability fix — polling pattern (BL-341)
- #392: Timeline-clip workflow documentation overhaul (BL-343)

## [v058] - 2026-05-05

### CI and Test Quality

Repaired malformed render_plan fixture data and removed the STOAT_RENDER_WORKER_ENABLED=false CI workaround, restoring render worker coverage in E2E and accessibility CI jobs. Fixed Python 3.10 asyncio task-cancellation stall in synthetic monitoring test. Migrated E2E focus assertions to document.activeElement pattern for cross-browser compatibility.

**Themes:** 1 (ci-and-test-quality)  
**Features:** 3/3 complete (001-ci-timeout-hardening, 002-render-fixture-repair, 003-e2e-focus-pattern-retrofit)  
**Quality:** 13/13 acceptance criteria met, 0 regressions

**Key Outcomes:**
- Added 30-minute CI job timeout and per-test 120s pytest-timeout to bound any CI hang (PR #384)
- Deleted 29 malformed render_jobs rows from data/stoat.db fixture (Windows-local paths inaccessible in CI); render worker starts clean in all CI jobs (PR #385)
- Removed STOAT_RENDER_WORKER_ENABLED=false workaround from e2e and a11y CI jobs (PR #385)
- Fixed Python 3.10 asyncio cancel stall in test_monitoring_task_continuous_execution using asyncio.wait with timeout (PR #385)
- Migrated 4 toBeFocused() assertions to document.activeElement pattern in accessibility.spec.ts and keyboard-navigation.spec.ts for cross-browser E2E robustness (PR #387)

**PRs Merged:**
- #384: CI timeout hardening (job timeout, per-test timeout, asyncio.wait_for fix)
- #385: Render fixture repair (delete malformed rows, remove CI workaround, Python 3.10 stall fix)
- #387: E2E focus pattern retrofit (migrate toBeFocused assertions to document.activeElement pattern)

## [v057] - 2026-05-04

### Documentation Quality Catchup

Updated C4 code-level documentation to reflect GUI store/hook/component and backend alembic/identity/WebSocket changes from v038–v057. Added FRAMEWORK_CONTEXT.md sections for accessibility testing strategy, batch progress transport, and render_worker.* event namespace.

**Themes:** 2 (c4-documentation-refresh, framework-context-additions)  
**Features:** 5/5 complete (001-gui-c4-refresh, 002-backend-c4-refresh, 001-axe-core-scanning-strategy, 002-batch-transport-docs, 003-render-worker-namespace)  
**Quality:** 52/52 acceptance criteria met, 0 regressions (2540 tests passed, 3 skipped, 0 failed)

**Key Outcomes:**
- GUI C4 code documentation updated: stores (14 → 17), hooks (13 → 20), workspace components added (PR #379)
- Backend C4 code documentation updated: alembic (7 → 9 migrations), identity module (ClientIdentityStore, InMemoryClientIdentityStore), WebSocket interface changes with client_identity_store param and client_id kwargs (PR #380)
- Accessibility testing strategy documented in FRAMEWORK_CONTEXT.md: axe-core scanning approach, decision tree for when to apply (PR #381)
- Batch progress HTTP polling transport documented in FRAMEWORK_CONTEXT.md: rationale for polling over SSE, transport selection guidance (PR #382)
- render_worker.* structured logging namespace added to FRAMEWORK_CONTEXT.md namespace taxonomy (PR #383)

**PRs Merged:**
- #379: GUI C4 code documentation refresh (stores, hooks, workspace components)
- #380: Backend C4 code documentation refresh (alembic, identity, WebSocket)
- #381: Accessibility testing strategy (axe-core scanning, decision tree)
- #382: Batch progress transport documentation
- #383: render_worker.* event namespace documentation

## [v056] - 2026-05-03

### WebSocket Client Identity

Implemented client identity management for WebSocket connections, enabling persistent token-based client tracking across reconnections.

**Theme:** websocket-client-identity  
**Features:** 3/3 complete (001-framework-documentation, 002-token-mechanism, 003-connection-integration)  
**Quality:** 49/49 acceptance criteria met, 58 new tests added, 0 regressions

**Key Outcomes:**
- Token mechanism: 32-char hex via `secrets.token_hex(16)`, validated via `is_valid_client_id()` (PR #376)
- Storage: `ClientIdentityStore` Protocol with `InMemoryClientIdentityStore` implementation, in-memory dict keyed by client token (PR #376)
- Integration: `ConnectionManager` wired with identity store; client token passed via WebSocket query parameter on connect, cleared on disconnect (PR #377)
- Backwards compatibility: Last-Event-ID replay path unchanged when no client token provided

**PRs Merged:**
- #376: Token mechanism and ClientIdentityStore implementation
- #377: ConnectionManager integration with WebSocket endpoint

## [v055] - 2026-05-03

### Render Worker Loop

Implemented a background render worker loop that dequeues render jobs and executes them via the existing `RenderService.run_job()` pipeline. The worker runs as a background task during app lifespan and is designed to be non-blocking and resilient.

**Theme:** render-worker-loop  
**Features:** 3/3 complete (001-command-builder, 002-worker-loop-core, 003-lifecycle-and-tests)  
**Quality:** 53 new tests added, 0 regressions

**Key Outcomes:**
- Command builder (`RenderCommandBuilder`) constructs validated FFmpeg command sequences from `RenderJob` (PR #373)
- Worker loop core (`RenderWorkerLoop`) dequeues jobs and dispatches to `RenderService.run_job()` with structured error handling (PR #374)
- Lifecycle integration wires `RenderWorkerLoop` into app lifespan at Phase 10 (after job queue worker), with graceful shutdown and full test coverage (PR #375)

**Recovery Context:**
v055 experienced a server restart mid-execution. Recovery involved manual PR merge (#375) and MCP state patching. Feature 003 completion report was not generated during recovery and is documented as a documentation lag.

**PRs Merged:**
- #373: Command builder for render jobs (`RenderCommandBuilder` with FFmpeg argument construction)
- #374: Render worker loop core (background dequeue loop with retry and error handling)
- #375: Lifecycle integration and tests (lifespan wiring, shutdown, 91-test coverage)

## [v054] - 2026-05-02

### GUI Performance & Compatibility Baselines

**Overview:** Established bundle size and cross-browser compatibility baselines for the web GUI. Measured Lighthouse performance and documented browser-specific testing gaps. All measurements are non-invasive; no source code was modified.

**Theme:** gui-perf-and-compat  
**Features:** 3/3 complete (001-changelog-v049, 002-bundle-analysis, 003-browser-compat-testing)  
**Quality:** 23/23 acceptance criteria met, 0 regressions

**Key Outcomes:**
- Bundle composition baseline: main 125.70 kB gzip, lazy PreviewPlayer chunk 162.20 kB gzip
- Lighthouse performance score: 79 (below 90 target due to CLS 0.44; documented in bundle-analysis.md)
- Time to Interactive (TTI): 2,130 ms (meets <3s target)
- Cross-browser test matrix: Chromium 95/96 pass, Firefox 91/96 pass, WebKit 88/96 pass
- Browser-specific issues documented with workarounds (FF-001, WK-001, WK-002)

**Backlog Items Resolved:** BL-328, BL-298, BL-299

**PRs Merged:**
- #370: Bundle size analysis baseline and optimization recommendations
- #371: Cross-browser compatibility testing and known-issue documentation

**Technical Insights:**
- Measurement-only features eliminate production risk by establishing baselines without code changes
- CI guards (`!process.env.CI`) prove effective for local-only multi-browser testing
- CLS is the primary constraint on Lighthouse score; fix is a Priority 1 recommendation for v055

## [v053] - 2026-05-02

### Comprehensive E2E Test Suite (Playwright)

Comprehensive Playwright E2E test suite for Phase 6 GUI workflows — workspace layout persistence, settings management, batch panel interaction, keyboard navigation, and accessibility validation.

**Features:**
- Workspace Layout & Settings Journeys (#366): E2E tests for workspace panel layout persistence, settings panel read/write, preset management across sessions
- Batch Panel WebSocket & Seed Endpoint (#367): E2E tests for batch job list rendering, seed endpoint integration, WebSocket progress event validation
- Keyboard Navigation & Accessibility (#368): E2E tests for keyboard-driven navigation, focus management, ARIA landmark traversal, screen reader announcements

**Quality Metrics:**
- 30/35 acceptance criteria met (5 deferred: browser-stack cross-browser, CI parallelism tuning)
- 0 regressions detected
- 58 new Playwright E2E tests added
- Full TypeScript type safety across all test files
- 3 features across 1 theme (01-gui-e2e-playwright-suite)

## [v052] - 2026-05-02

### GUI Accessibility

Achieved WCAG 2.1 Level AA conformance across all GUI components and workflows.

**Features:**
- Accessibility Core Infrastructure (#362): AccessibilityWrapper component, useAnnounce hook, dual aria-live regions
- ARIA Landmarks and Labels (#363): Semantic HTML markup, skip-to-content link, navigation landmarks
- Dynamic Status Announcements (#364): Live region integration for render progress, scan results, error states
- CI/E2E Validation Gates (#365): Automated axe-core audit, keyboard navigation testing, UAT journeys

**Quality Metrics:**
- 30/30 acceptance criteria met
- 0 regressions detected
- 2419 tests passed (3 skipped, 0 failures)
- 100% quality gate pass rate

## [v051] - 2026-05-01

Deployment Infrastructure & Developer Guardrails. Delivers three backlog items addressing deployment/DevX concerns: FFmpeg production decision with health endpoint semantics, CI Docker image build with size/quality gates, and Windows shell anti-pattern prevention via pre-commit hook. 55/55 ACs met, 0 regressions, 3 PRs (#359, #360, #361).

### Deployment Safety

- **FFmpeg Production Status Decision** — Resolved FFmpeg-in-production decision; classified FFmpeg as non-critical with graceful degradation; `/health/ready` returns HTTP 200 with `status: "degraded"` when FFmpeg unavailable rather than HTTP 503, enabling flexible deployment architectures (CPU-only containers, remote FFmpeg, staged rollouts) (BL-309, #359)

### CI Hardening

- **Docker Build CI Gate** — Added GitHub Actions CI workflow job to build production Docker image with multi-stage Dockerfile, enforcing size/quality gates to prevent bloat and configuration drift; validates production deployment readiness on every PR (BL-310, #360)

### Developer Experience

- **Windows Shell Anti-Pattern Prevention** — Implemented pre-commit hook using `grep -I -F` (fixed-string, binary-safe) to catch Windows `/dev/null` vs `nul` anti-patterns in shell scripts (.sh, .bash, .yml files); CI backup verification step in workflows prevents hook bypass; documented guidance in AGENTS.md (BL-311, #361)

## [v050] - 2026-05-01

Security Maintenance and Quality Improvements. Delivers three backlog items: a datetime deprecation fix eliminating DeprecationWarnings across the API layer, encoder cache test coverage expansion to ≥85%, and a UAT known-failure registry that distinguishes known failures from regressions. 18/18 ACs met, 0 regressions.

### Maintenance

- **Datetime Deprecation Fix** — Replaced `datetime.utcnow()` with `datetime.now(timezone.utc)` across 7 locations in the API layer to eliminate DeprecationWarnings and ensure Python 3.10+ compatibility (BL-322, #355)

### Test Coverage

- **Encoder Cache Coverage Expansion** — Added `tests/unit/render/test_encoder_cache.py` with 18 parameterized tests covering `AsyncSQLiteEncoderCacheRepository` and `InMemoryEncoderCacheRepository`, raising coverage from 71% to ≥85% (BL-324, #356)

### UAT Infrastructure

- **UAT Known-Failure Registry** — Implemented `data/baseline-uat-failures.json` registry and updated `scripts/uat_runner.py` to emit `KNOWN_FAILURE`/`UNEXPECTED_PASS` annotations, enabling distinction between known failures and regressions (BL-325, #357)

## [v049] - 2026-04-30

Workspace Shell Polish. Delivers two themes: workspace accessibility cleanup (a11y focus order fix with E2E coverage) and workspace panel routing (per-panel URL routing with PRESETS routes field and PANEL_DEFAULTS consolidation). 18/18 ACs met, 0 regressions.

### Workspace Accessibility

- **A11y Focus Order Fix** — Removed conditional-mount guard that broke focus order on initial workspace load; added workspace a11y E2E tests covering focus-order and keyboard navigation regressions (BL-305, #350)

### Workspace Panel Routing

- **Per-Panel Routing** — PRESETS routes field wires per-panel URL routing with URL params; `003-routing-design-validation` design document captures the routing design and validation approach (BL-306, #352, #353)
- **PANEL_DEFAULTS Consolidation** — Extracted `PANEL_DEFAULTS` const to eliminate duplicate panel size definitions across workspace layout components (BL-307, #351)

## [v048] - 2026-04-30

### Added
- Explicit `python-dotenv>=1.2.2` lower-bound constraint in `pyproject.toml` to clear CVE-2026-28684 and enforce minimum version with required security fixes (#347).
- Security audit cadence formalization: `docs/security/audit-cadence.md` documents quarterly review triggers, Python/FFmpeg/PyO3 major upgrade audits, and new unsafe Rust pattern scans. Integrated into `AGENTS.md` and `docs/design/FRAMEWORK_CONTEXT.md` as authoritative process artifact (#348).

### Changed
- `docs/security/review-phase6.md` §9: Replaced inline audit cadence prose with reference pointer to new `audit-cadence.md` for single-source-of-truth maintenance.

## [v047] - 2026-04-30

- docs(v047): C4 architecture refresh and load-test baseline documentation
- PR #344: Update C4 architecture diagrams for v037–v046 changes
- PR #345: Execute and record load-test baseline

## [v045] - 2026-04-29

Phase 6: Configuration Documentation Convergence. Documents all STOAT_* environment variables with operator-facing setup references and security-focused guidance, and enforces zero-drift by reducing the security audit baseline to an empty frozenset.

### Configuration Reference

- **STOAT_* Environment Variable Coverage** — 41 STOAT_* variables documented in `docs/setup/04_configuration.md` with name, type, default, valid range, and plain-English description; Configuration Documentation Rule added to AGENTS.md enforcing documentation for all future variables (BL-316, #338)

### Operator Security Configuration

- **Operator Security Configuration Guide** — `docs/manual/configuration-reference.md` with 13 security-sensitive STOAT_* variables covering production hazards, security implications, and recommended values; `KNOWN_UNDOCUMENTED_SETTINGS_VARS` allowlist in `tests/security/test_audit.py` reduced to empty `frozenset()` to enforce zero-drift audit baseline (BL-317, #339)

## [v046] - 2026-04-29

- docs(v046): Document startup initialization sequence, Alembic migration conventions, and structured event naming
- PR #341: Startup Initialization Sequence documentation
- PR #342: Alembic Migration Conventions documentation
- PR #343: Structured Event Naming Conventions documentation

## [v044] - 2026-04-28

Phase 6: GUI Unified Workspace. Delivers two themes: a workspace layout foundation (dockable resizable panels with persistent sizing and layout presets with keyboard shortcuts) and workspace feature panels (settings panel with theme selector and shortcut editor, keyboard shortcut reference overlay, and batch panel GUI with job monitoring and cancellation).

### Workspace Layout

- **Dockable Resizable Panel Layout** — Resizable panel infrastructure with `workspaceStore` (Zustand) and `WorkspaceLayout` component; persistent panel sizing via localStorage; conditional Shell mounting for backward-compatible routed pages (BL-291, #332)
- **Workspace Layout Presets** — PRESETS constants (Edit/Review/Render); `setPreset` action with Ctrl+1/2/3 keyboard bindings; per-preset size preservation via `sizesByPreset`; `useRef` guard prevents bidirectional preset/resize loops (BL-292, #333)

### Workspace Feature Panels

- **Settings Panel** — Theme selector and shortcut editor integrated into workspace sidebar; settings persist to localStorage (BL-293, #334)
- **Keyboard Shortcut Reference Overlay** — Dynamic shortcut enumeration from registry; focus trap with Escape-to-dismiss (BL-294, #335)
- **Batch Panel GUI** — Batch job submission form, live progress polling, job cancellation, and real-time status updates; async DELETE handler fix for correct post-cancel state (BL-295, #336)

## [v043] - 2026-04-27

Phase 6 Quality & Security Gate. Delivers two themes: a security-audit theme (Python API and Rust core security audits) and a performance-observability theme (performance benchmarks with Phase 6 metrics, load testing harness with noop render mode, and Grafana SLI dashboard).

### Security

- **Python API Security Audit** — Enumerated 8 potential vulnerability classes with grep-based AST probes; zero P0/P1 findings; SQL injection defense confirmed via parameterized queries and AST-walk detection; path traversal enforced via `STOAT_ALLOWED_SCAN_ROOTS`; introduced `tests/security/` test category with 3 probe scripts (BL-286, #327)
- **Rust Core Security Audit** — Full audit of all Rust sanitization and filter-building code; zero `unsafe` blocks confirmed across entire codebase; DrawtextBuilder injection surface validated with 20 additional property-based tests; single shared security report approach adopted (BL-287, #328)

### Performance & Observability

- **Performance Benchmarks and Phase 6 Metrics** — `tests/benchmarks/` suite with pytest-benchmark against live FastAPI endpoints; 7 new Prometheus metrics registered in `metrics.py` (`stoat_seed_duration_seconds`, `stoat_system_state_duration_seconds`, `stoat_ws_buffer_size`, `stoat_ws_connected_clients`, `stoat_active_jobs_count`, `stoat_feature_flag_state`, `stoat_migration_duration_seconds`); baseline results documented in `docs/design/11-performance-benchmarks.md` (BL-288, #329)
- **Load Test Harness** — Locust-based load test harness in `tests/load/`; `STOAT_RENDER_MODE=noop` setting short-circuits FFmpeg for synthetic throughput testing; `websocket-client` (gevent-compatible) for WebSocket load simulation; hardware-variable results deferred to operator runs (BL-289, #330)
- **Grafana SLI Dashboard** — `docs/observability/grafana-sli-dashboard.json` with 7 SLI panels (request rate, error rate, latency p50/p95/p99, WebSocket clients, active jobs); test-time source parsing validates metric truth set against live registrations (BL-290, #331)

## [v042] - 2026-04-26

Agent Operator Documentation and Residual Closure. Delivers targeted documentation for AI agent operators (operator guide, prompt recipes, WebSocket event vocabulary) and closes residual v039/v041 documentation gaps (CHANGELOG verification, AGENTS.md path corrections, manual TOC completeness).

### Documentation

- **Agent Operator Guide** — `docs/manual/operator-guide.md` compact reference for AI agents orchestrating stoat-and-ferret over HTTP/WebSocket; covers API orientation, canonical sequences, state machines, testing mode, and MCP abstraction criteria; all endpoint paths live-verified (BL-283, #323)
- **Prompt Recipes and Example Scripts** — `docs/manual/prompt-recipes.md` with 6 copy-paste recipes; `scripts/wait-for-render.py` and `scripts/dump-ws-events.py` executable utilities for common agent workflows (BL-284, #324)
- **WebSocket Event Vocabulary** — `docs/manual/ws-event-vocabulary.md` documenting all 24 event types with payloads, state transitions, and live-captured evidence; 9 frames captured for validation (BL-285, #325)
- **AGENTS.md Path Fix** — Updated 8 stale `stubs/` directory references to `src/` following the v041 stub consolidation (BL-303, #321)
- **Manual TOC Update** — Added 6 missing TOC entries to `docs/manual/00_README.md` for v041 and pre-v041 manual files (BL-304, #322)
- **CHANGELOG Verification** — Confirmed v039 (BL-301) and v041 (BL-302) CHANGELOG sections are present and accurate; no edits required

## [v041] - 2026-04-24

Documentation and Operational Excellence. Validates the OpenAPI specification against Phase 6 endpoints, enriches Rust core with rustdoc examples, delivers canonical API usage workflows, and ships an operational runbook with decision-tree troubleshooting.

### Documentation

- **OpenAPI Specification Validation** — Validated OpenAPI spec against all Phase 6 endpoints; documented endpoint contracts and response schemas for the full API surface (BL-279, #316)
- **Rust Core rustdoc Examples** — Added rustdoc examples to all public Rust types and functions; consolidated stubs to `src/` for co-location with implementations (BL-280, #317)
- **API Usage Examples** — `docs/manual/api-usage-examples.md` with 5 canonical workflows demonstrating end-to-end API interactions for scan, project creation, clip management, effects, and render (BL-281, #318)
- **Operational Runbook** — `docs/manual/operational-runbook.md` with decision-tree troubleshooting guides for common failure modes, health check interpretation, and recovery procedures (BL-282, #319)

## [v040] - 2026-04-23

### Features
- Event ID and timestamp on all WebSocket events
- WebSocket replay buffer with reconnection support
- System state snapshot endpoint for external agent orientation
- Test fixture seeding endpoints for repeatable agent workflows
- Long-poll job completion endpoint with configurable timeouts
- OpenAPI state machine documentation for job lifecycle

### Improvements
- All quality gates pass (2352 tests, 100% coverage)
- Comprehensive WebSocket observability and testability improvements

## [v039] - 2026-04-23

AI Integration & Schema Discovery. Delivers a Rust ParameterSchema translator for AI-friendly effect discovery, a schema introspection REST endpoint for dynamic resource discovery by external agents, and a comprehensive AI integration patterns guide documenting how external systems can interact with the API.

### Added

- **ParameterSchema Rust Translator** — `ParameterSchema` Rust type with PyO3 bindings translating stoat-and-ferret effect parameter schemas into a normalized, AI-consumable format; enables external agents to programmatically enumerate effect capabilities and constraints (BL-270, #306)
- **Schema Introspection Endpoint** — `GET /api/v1/schema/{resource}` REST endpoint returning JSON Schema descriptions for API resources; supports AI agent discovery of available data shapes without prior knowledge of the API (BL-271, #307)
- **AI Integration Patterns Guide** — `docs/manual/ai-integration-patterns.md` documenting recommended patterns for external agents interacting with the stoat-and-ferret API, including effect discovery, parameter validation, and session management (BL-272, #308)

## [v037] - 2026-04-17

WebSocket Enrichment, Container Deployment, and Developer Quality. Enriches render WebSocket events with frame/fps/encoder metadata, implements live frame streaming to Theater Mode, ships a production-ready multi-stage Dockerfile with health checks and Docker Compose dev stack, and improves developer quality with jest-dom Vitest setup and updated test harness documentation.

### Added

- **Format-Encoder Validation on Submission** — `POST /render` enforces format-encoder compatibility at submission time, returning 422 for invalid combinations (BL-258, #293)
- **Enriched Render WebSocket Progress Events** — `render.progress` events now include `frame`, `fps`, and `encoder` metadata fields for richer client-side display (BL-254, #294)
- **Live Frame Streaming to Theater Mode** — Frame streaming endpoint delivers 540p frames to Theater Mode during active renders (BL-255, #295)
- **Production Dockerfile** — Multi-stage Dockerfile for containerized production deployment with minimal runtime image and non-root user (BL-262, #296)
- **Container Health Checks** — Startup gate and liveness/readiness health check endpoints for container orchestration (BL-265, #297)
- **Docker Compose Dev Stack** — `docker-compose.yml` orchestrating API, frontend, and dependencies for local development (BL-264, #298)
- **Deployment Smoke Script** — `scripts/deploy_smoke.sh` and `GET /api/v1/version` endpoint for smoke-testing deployed containers (BL-263, #299)
- **Jest-dom Vitest Setup** — Jest-dom matchers configured in Vitest setup for expressive DOM assertions in GUI tests (BL-259, #300)

### Changed

- **RenderJobCard C4 Diagram** — Updated C4 component diagram to reflect v035 `cancelLoading`/`retryLoading`/`deleteLoading` flags (BL-257)

### Documentation

- **Three-Tier Test Harness Guide** — Test harness documentation updated with contract test tier description and guidance (BL-256, #301)

## v034 — Documentation Catch-Up: Phase 4 and Phase 5 (2026-04-11)

### Documentation

- Verified Phase 4 design documents (01-roadmap.md, 02-architecture.md, 05-api-specification.md, 07-quality-architecture.md, 08-gui-architecture.md) — all Phase 4 content confirmed present (BL-208, #PR-001)
- Verified Phase 4 IMPACT_ASSESSMENT.md grep patterns — PreviewSession, ProxyFile, ThumbnailStrip, Waveform, TheaterMode pattern groups confirmed present (BL-209)
- Updated design documents with Phase 5 render subsystem: milestones [x] in roadmap, render state machine in architecture, 11 render endpoints in API spec, render test patterns in quality architecture, RenderPage/RenderJobCard/StartRenderModal in GUI architecture (BL-237, #279)
- Added Phase 5 grep patterns to IMPACT_ASSESSMENT.md: RenderJob/RenderStatus, OutputFormat/QualityPreset, RenderQueue/RenderExecutor, RenderService/PreflightError, EncoderCacheEntry/AsyncEncoderCacheRepository pattern groups (BL-238, #280)
- Extended sample project seed script with render step (POST /api/v1/render); added smoke test asserting status==queued; documented export workflow in sample-project.md (BL-239, #281)
- C4 architecture delta: documented encoder_cache.py in c4-code-stoat-ferret-render.md; updated useRenderEvents to Shell in c4-code-gui-hooks.md; updated BottomHUD in c4-code-gui-components-theater.md; added Start Render button to c4-code-gui-pages.md TimelinePage; added v034 delta row to C4 README (BL-241, #282)
## v035 — Frontend Reliability and Render GUI Polish (2026-04-12)

### Changed

- **useWebSocket Burst Safety** — Replaced direct `setState` in `onmessage` with a ref-queue pattern (`queueRef` + `tick` counter) to survive React 18 automatic batching; hook now exposes `messages: MessageEvent[]` array alongside `lastMessage` for burst-complete delivery (BL-248, #283)
- **WebSocket Consumers** — `useRenderEvents`, `useJobProgress`, and `ActivityLog` updated to iterate `messages[]` array with `for (const msg of messages)` pattern; `DashboardPage` passes `messages` to `ActivityLog` (BL-248, #284)

### Added

- **Format-Encoder Compatibility Validation** — `render_preview` endpoint returns HTTP 422 with `INCOMPATIBLE_FORMAT_ENCODER` for invalid format-encoder combinations (e.g., `libvpx + mp4`); `av1` codec added to `mkv` format; `StartRenderModal` surfaces 422 error message in preview area (BL-252, #286)
- **RenderJobCard Loading States** — Per-button `cancelLoading`, `retryLoading`, `deleteLoading` flags with `try/finally` reset; buttons disabled during in-flight API calls to prevent duplicate requests (BL-253, #287)

### Fixed

- **TimelinePage Test Hygiene** — Corrected stale test counts in C4 documentation (TimelinePage: 7→13, total: 318→324); confirmed all 13 TimelinePage tests pass following the cbe2fa5 fix (BL-247, #285)

## v036 — Service Quality & Persistence (2026-04-14)

### Fixed

- **UAT CI Timeout Fix** — Fixed UAT CI job hanging by implementing pre-build artifact caching and `--no-build` flag in uat_runner.py; timeout budget documented in workflow (BL-261, #288)

### Added

- **DB Persistence for Services** — Wired SQLiteThumbnailStripRepository and SQLiteWaveformRepository into ThumbnailService and WaveformService via DI; services now survive restarts (BL-251, #289)
- **ProxyService Public API** — Added `list_by_video(video_id: str)` public method to ProxyService; removed scan.py encapsulation breach (BL-249, #290)
- **Proxy Auto-Generation Optimization** — Refactored `_auto_queue_proxies()` to accept video IDs from scan result instead of re-walking directory; eliminated redundant filesystem traversal (BL-250, #291)
- **Frontend Testing Guidance** — Added async `act()` documentation to FRAMEWORK_CONTEXT.md with multi-phase hook test patterns (BL-260)

## v033 — Render Testing, UAT Journeys, and Metrics (2026-04-11)

### Added
- Render API smoke tests for cancel, retry, and encoder-refresh endpoints (BL-232, #269)
- Render contract tests for output format validation (mp4/webm/mov/mkv via ffprobe), encoder detection against real FFmpeg output, and multi-segment concat duration integrity using lavfi virtual inputs (BL-233, #270, #271, #272)
- UAT journeys J501–J504 for render export, render queue management, render settings, and render failure recovery (BL-234, #274, #275, #276, #277)
- J401–J404 headless CI hardening with graceful no-project state handling; CI UAT timeout increased from 5 to 10 minutes (BL-205, #273)
- `render_jobs_total` Prometheus counter `submitted` label on job creation for in-flight job tracking via Prometheus arithmetic (BL-245, #278)

## v032 — Render Surface Integration (2026-04-08)

### Added
- Lifted `useRenderEvents` WebSocket hook to Shell component for application-wide render event listening (BL-235)
- Render progress indicators (percentage, ETA, speed ratio) in Theater Mode BottomHUD (BL-235)
- Start Render button on TimelinePage header with StartRenderModal integration (BL-236)

### Changed
- BottomHUD reads render state from shared `useRenderStore` instead of maintaining its own WebSocket connection

## [v031] - 2026-04-07

Phase 5 GUI Render Interactive Components. Enriches render progress WebSocket events with ETA and speed data, builds reusable render job card components, and ships the StartRenderModal for configuring and launching render jobs.

### Added

- **Render Progress Enrichment** — `eta_seconds` and `speed_ratio` fields in `render.progress` WebSocket events, computed via Rust `estimate_eta()` and Python arithmetic; propagated through renderStore `setProgress` action (BL-243, #260, #261)
- **StatusBadge Component** — Reusable color-coded dot + label component for render job status display across all 5 states (BL-229, #262)
- **RenderJobCard Component** — Full job card with progress bar, ETA, speed ratio, StatusBadge, and cancel/retry/delete action buttons; integrated into RenderPage Active/Pending/Completed sections (BL-229, #263)
- **Render Preview Endpoint** — `POST /api/v1/render/preview` returning FFmpeg command strings for format/quality/encoder combinations with Rust `build_render_command` (BL-230, #264)
- **StartRenderModal** — Modal with cascading format/quality/encoder selectors, disk space bar, debounced FFmpeg command preview, inline validation, and render submission (BL-230, #265)

## [v030] - 2026-04-05

GUI Render Page Shell + Public API Hygiene. Builds the user-facing render control center with routing, state management, page layout, and UAT coverage. Fixes LayoutError public API export and migrates compose.py imports.

### Added

- **Render Page Route & Navigation** — `/render` route in App.tsx, Render tab in Navigation with endpoint health check (BL-231, #255)
- **Render Store & WebSocket Hook** — Zustand renderStore with job list, queue status, encoder/format state; useRenderEvents hook dispatching 8 WebSocket render event types with reconnection re-fetch (BL-231, #256)
- **Render Page Layout** — RenderPage with Active/Pending/Completed job sections, queue status bar, disabled Start Render button, data-testid attributes (BL-228, #257)
- **Render UAT Journey 501** — Playwright test validating render page navigation, layout elements, and data-testid selectors (BL-231, BL-228, #258)

### Fixed

- **LayoutError Public API Export** — re-exported LayoutError through stoat_ferret_core public API, migrated compose.py from internal `_core` import (BL-246, #259)

## [v028] - 2026-04-01

Phase 5 Foundation: Rust Render Core + Render Job Infrastructure. Builds compute-intensive Rust render functions (plan, encoder, progress, command) with PyO3 bindings and proptest coverage, plus Python job infrastructure (model, queue, executor, checkpoints, service) for end-to-end render job lifecycle management.

### Added

- **Render Plan Builder** — Rust `build_render_plan()` with segment decomposition at clip boundaries, frame counting, cost estimation, and `validate_render_settings()` pre-flight checks (BL-210, #234)
- **Hardware Encoder Detection** — Rust `detect_hardware_encoders()` parsing FFmpeg output, `select_encoder()` with nvenc/qsv/vaapi/amf/mf/software fallback chain, `build_encoding_args()` for draft/standard/high presets (BL-211, #235)
- **Progress Tracking** — Rust `parse_ffmpeg_progress()` for FFmpeg `-progress pipe:1` output, `calculate_progress()` bounded 0.0-1.0, `estimate_eta()`, and `aggregate_segment_progress()` with duration weighting (BL-212, #236)
- **Render Command Builder** — Rust `build_render_command()`, `build_concat_command()` for ffconcat demuxer, `check_output_conflict()`, and `estimate_output_size()` with bitrate lookup table (BL-213, #237)
- **Render Job Model** — `RenderJob` dataclass, `RenderStatus` state machine, `OutputFormat`/`QualityPreset` enums, SQLite + InMemory repository implementations with 86 parity tests (BL-214, #238)
- **Render Queue** — persistent queue with `max_concurrent`/`max_depth` limits, FIFO ordering, startup recovery, and `QueueFullError` (BL-215, #239)
- **Render Executor** — FFmpeg subprocess management with Rust PyO3 progress parsing, stdin-based graceful cancellation, timeout enforcement, and temp file cleanup (BL-216, #240)
- **Render Checkpoints** — per-segment checkpoint persistence to SQLite, recovery scanning on startup, resume-from-checkpoint, stale cleanup with CASCADE FK (BL-217, #241)
- **Render Service** — lifecycle orchestration with pre-flight checks via Rust, WebSocket event broadcasting, retry logic, and DI wiring in `create_app()` (BL-218, #242)
- **Phase 4 FFmpeg Contract Tests** — HLS segment generation, Rust-simplified filter chain, thumbnail strip JPEG, and waveform PNG validation with real FFmpeg output (BL-204, #229)

## [v027] - 2026-03-30

Theater Mode, Integration Wiring, Phase 4 Test Coverage, and Documentation Updates. Adds fullscreen Theater Mode with HUD overlay and keyboard shortcuts. Wires transition IDs, timeline-player sync, audio waveforms, and proxy status indicators. Adds Phase 4 smoke tests, contract tests, and UAT journeys. Regenerates C4 architecture documentation and updates design documents.

### Added

- **Theater Mode Fullscreen Wrapper** — fullscreen container with auto-hiding HUD, CSS transition animations, and escape-to-exit (BL-199, #221)
- **Theater HUD Overlay** — AI action indicator and render progress display overlaid on fullscreen preview (BL-200, #222)
- **Theater Mode Keyboard Shortcuts** — hotkeys for theater toggle, HUD visibility, and playback controls in fullscreen (BL-201, #223)
- **Bidirectional Timeline-Player Sync** — playhead position synchronized between timeline and preview player in both directions (BL-202, #225)
- **Audio Waveform Visualization** — waveform overlay on timeline clips using generated waveform data (BL-206, #226)
- **Proxy Status Indicators** — ProxyStatusBadge component on VideoCard showing proxy generation state via WebSocket updates (BL-207, #227)
- **Phase 4 Preview Smoke Tests** — smoke tests covering preview session endpoints (BL-203, #228)
- **Phase 4 UAT Journeys** — J401-J404 UAT journeys for theater mode, timeline sync, waveform, and proxy status (BL-205, #230)
- **C4 Architecture Regeneration** — full C4 documentation regenerated covering v011-v027 (BL-147, #231)
- **Design Document Updates** — Phase 4 content added to architecture and GUI design documents (BL-208, #232)
- **Impact Assessment Patterns** — Phase 4 grep patterns added to IMPACT_ASSESSMENT (BL-209, #233)

### Fixed

- **Transition ID Assignment** — effects-router transitions now receive IDs for DELETE compatibility (BL-148, #224)

## [v026] - 2026-03-27

Phase 4 Observability + GUI Preview Player. Instruments preview and proxy subsystems with Prometheus metrics, structured logging, health checks, and graceful degradation. Wires deferred BL-179 WebSocket progress callbacks. Builds the complete GUI preview player with HLS.js, controls, seek tooltip, quality selector, and Preview page.

### Added

- **WebSocket Progress Wiring** — throttled progress callbacks in PreviewManager broadcasting `JOB_PROGRESS` events via WebSocket for real-time generation updates (BL-179, #208)
- **Preview & Proxy Prometheus Metrics** — 14 metric definitions (counters, gauges, histograms) across preview, proxy, and cache subsystems (BL-190, #209)
- **Preview Structured Logging** — structured log events across session lifecycle, proxy, cache, thumbnail, and waveform generation with `{subsystem}_{action}` naming convention (BL-191, #210)
- **Preview & Proxy Health Checks** — preview and proxy checks on `/health/ready` with degraded semantics for optional subsystems; HealthCards GUI updates (BL-192, #211)
- **Graceful Degradation & Shutdown** — 503 `FFMPEG_UNAVAILABLE` on preview endpoints when FFmpeg missing; `cancel_all()` with process termination and temp cleanup on shutdown (BL-193, #212)
- **Smoke Test Updates** — health check assertions for preview/proxy fields; new preview session creation smoke test (BL-192, #213)
- **Smoke Test Harness Guide** — documentation of new smoke test entries in smoke-test-key-files.md (BL-192, #214)
- **Preview Page & Store** — PreviewPage shell, Zustand previewStore, navigation tab, route, and regenerated OpenAPI types for v025 preview API (BL-198, #215)
- **HLS.js Preview Player** — PreviewPlayer with HLS.js integration, Safari native fallback, fatal error recovery, buffer tracking, and `React.lazy` dynamic import (BL-194, #216)
- **Player Controls** — play/pause, progress bar click-to-seek, skip ±5s, volume slider with mute, time display (mm:ss/hh:mm:ss), and full keyboard accessibility (BL-195, #217)
- **Seek Tooltip** — sprite-sheet frame calculation, smooth mouse-following via absolute positioning, and time-only fallback when thumbnails unavailable (BL-196, #218)
- **Quality Selector & Status Display** — quality dropdown (low/medium/high) with cancel-and-restart flow, and PreviewStatus with seek latency, buffer bar, and generation progress at ~4 Hz (BL-197, #219)
- **Preview Playback UAT Journey** — J205 with 5 steps, registered in `uat_runner.py` dependency graph, and updated uat-testing.md (BL-198, #220)

## [v025] - 2026-03-26

Phase 4 Preview Engine: Sessions + Visual Aids. Core preview playback infrastructure with HLS session management, thumbnail strip generation, and waveform visualization. Backend-only — no GUI components.

### Added

- **Preview Session Data Model** — `PreviewSession` dataclass, `PreviewStatus` enum, `preview_sessions` SQLite table, `AsyncPreviewSessionRepository` protocol with SQLite + InMemory implementations and 31 parity tests (BL-178, #198)
- **HLS Segment Generator** — FFmpeg HLS VOD segment generation with Rust filter simplification, progress callbacks, and cooperative cancellation (BL-179, #199)
- **Preview Session Manager** — `PreviewManager` with start/seek/stop lifecycle, concurrency limits, per-session locks, 4 new WebSocket `EventType` variants, background expiry cleanup (BL-180, #200)
- **Preview API Endpoints** — 7 REST endpoints for session management and HLS content serving with Pydantic schemas and DI wiring (BL-181, #201)
- **Preview Cache** — LRU eviction and TTL expiry for preview segment storage with configurable size limits (1 GB default) and background cleanup task (BL-182, #202)
- **Preview Cache API** — GET/DELETE endpoints for cache status inspection and clearing with `clear_all()` bulk operation (BL-183, #203)
- **Thumbnail Strip Service** — sprite sheet generation using FFmpeg fps+scale+tile filters with NxM grid tiling, JPEG dimension limit handling, configurable interval via `STOAT_THUMBNAIL_STRIP_INTERVAL`, `extract_frame_args()` shared primitive (BL-186, #204)
- **Thumbnail Strip API** — POST 202/GET metadata/GET strip.jpg endpoints with Pydantic schemas and DI wiring (BL-187, #205)
- **Waveform Generation Service** — dual output: PNG via showwavespic filter and JSON via astats/ffprobe, mono/stereo support, Windows path escaping, configurable via `STOAT_WAVEFORM_DIR` (BL-188, #206)
- **Waveform API** — POST 202/GET metadata/GET waveform.png/GET waveform.json endpoints with dual format support (BL-189, #207)

## [v024] - 2026-03-25

Phase 4 Foundation: Deferred Quality + Proxy Infrastructure + Rust Preview Core. Close the OpenAPI enum freshness gap from v023, build proxy data and service infrastructure for Phase 4 preview playback, and implement Rust-based filter simplification and cost estimation for real-time preview.

### Added

- **OpenAPI Enum CI Freshness Check** — boot-and-compare CI step ensures committed `gui/openapi.json` stays in sync with live FastAPI spec; key-sorted JSON normalization for deterministic diffs (BL-139, #190)
- **Proxy Data Model** — `ProxyFile` dataclass, `ProxyStatus`/`ProxyQuality` enums, `proxy_files` SQLite table with UNIQUE constraint, `AsyncProxyRepository` protocol with SQLite + InMemory implementations and 51 parity tests (BL-174, #191)
- **Proxy Generation Service** — async FFmpeg proxy transcoding with progress parsing, quality auto-selection, storage quota with LRU eviction, stale detection, per-job-type timeout (1800s) in job queue (BL-175, #192)
- **Proxy Management API** — REST endpoints for proxy generate (POST), status (GET), delete (DELETE), and batch operations (POST); Pydantic response models with DI wiring (BL-176, #193)
- **Proxy Scan Integration** — optional auto-queue of proxy generation on scan discovery, stale proxy detection during scan, `STOAT_PROXY_AUTO_GENERATE` setting (BL-177, #194)
- **Proxy Smoke Tests** — 4 smoke tests covering all proxy endpoints with direct DB seeding; harness documentation updated (Impact #9, #11, #195)
- **Preview Filter Simplification (Rust)** — `preview/` module with `PreviewQuality` enum, `simplify_filter_graph`/`simplify_filter_chain`/`is_expensive_filter` functions, getter methods on FilterGraph/FilterChain/Filter, 19 Rust tests + 9 Python binding tests via PyO3 (BL-184, #196)
- **Filter Cost Estimation and Scale Injection (Rust)** — `estimate_filter_cost` with sigmoid normalization, `select_preview_quality` with threshold mapping, `inject_preview_scale` for scale filter insertion, property-based test coverage via proptest (BL-185, #197)

### Changed

- **`TransitionResponse` renamed to `EffectTransitionResponse`** — resolves non-deterministic OpenAPI schema naming from duplicate class names across modules
- **Committed `gui/openapi.json` regenerated** — spec was stale; updated to match current FastAPI output

## [v023] - 2026-03-25

Persistence, Frontend Modernisation, and CI UAT. Persistent batch state and version retention improve resilience; WebSocket push replaces HTTP polling; OpenAPI codegen pipeline eliminates hand-authored TypeScript types; effect preview thumbnails added; UAT harness wired into CI to block merges on browser-level regressions.

### Added

- **Batch SQLite Persistence** — batch render state persisted to SQLite via Protocol + SQLite + InMemory repository pattern; jobs survive server restarts (BL-143, #183)
- **Version Retention Policy** — configurable `STOAT_VERSION_RETENTION_COUNT` env var for keep-last-N pruning per project (BL-144, #184)
- **WebSocket Job Progress** — `JOB_PROGRESS` event type with async broadcast from scan handler and `useJobProgress` frontend hook; replaces HTTP polling in ScanModal (BL-141, #185)
- **OpenAPI-to-TypeScript Codegen Pipeline** — Python spec export (`scripts/export_openapi.py`), `openapi-typescript` codegen, CI drift detection for both JSON and TypeScript layers (BL-139, #186)
- **Effect Preview Thumbnails** — `POST /api/v1/effects/preview/thumbnail` endpoint with async FFmpeg processing, EffectsPage thumbnail display with 500ms debounce (BL-086, #188)
- **UAT CI Pipeline** — GitHub Actions `uat` job with Playwright install, server boot, 4 UAT journeys headless, artifact upload, `dorny/paths-filter` scoping, 5-min timeout, Playwright browser caching (BL-149, #189)

### Changed

- **Frontend Type Migration** — 9 hand-authored TypeScript types replaced with generated OpenAPI imports across 34 files; convenience re-export layer (`generated/types.ts`); deleted unused `types/timeline.ts` (BL-139, #187)
- **`ci-status` gate** updated to include UAT job

### Fixed

- **WebSocket message-loss race condition** — broadcast reordering in `scan.py` ensures critical messages arrive last; ScanModal polling fallback added as safety net (discovered during CI UAT integration)
- **Headless scroll assertion** — journey 203 zoom fix for flaky headless Playwright assertion
- **TimelinePage test failures** — 3 pre-existing test failures fixed (undefined `projects` guard, shared Response mock)

## [v22.1] - 2026-03-23

UAT Bugfix Round. Post-v022 bugfix pass resolving issues discovered during UAT journey execution. 24 fixes across application bugs, test infrastructure, and observability. All 4 UAT journeys now passing.

### Fixed

- **Application Bugs**
  - `scan.py` — `thumbnail_service.generate()` wrapped in `asyncio.to_thread()` to prevent event loop blocking (BL-150)
  - `Navigation.tsx` — HEAD requests changed to GET to eliminate 405 console errors (BL-151)
  - `ClipFormModal.tsx` — pageSize reduced 1000 to 100 to match API validation limit (BL-157)
  - `useEffectPreview.ts` — guard added to skip preview when required schema fields absent (BL-162)
  - `TimelinePage.tsx` — `fetchTimeline()` wired to projectStore for correct project context (BL-163)
  - `useEffectPreview.ts` — null-schema guard added (BL-165)
  - `EffectsPage.tsx` — onChange guard added to prevent clip-clearing on same-project re-select (BL-170)

### Changed

- **Test Infrastructure**
  - `seed_sample_project.py` — httpx timeout increased 60s to 120s, poll iterations 60 to 120 (BL-152)
  - `uat_journey_201.py` — scan-complete timeout increased 30s to 90s (BL-153)
  - `seed_sample_project.py` — `videos_already_scanned()` guard to prevent redundant scans (BL-154)
  - `uat_runner.py` — subprocess.PIPE replaced with file redirect to prevent pipe deadlock (BL-156)
  - `uat_journey_204.py` — clip selection added before effect-stack assertion (BL-158)
  - `uat_journey_203.py` + 204 — effect-stack-item- testid corrected to effect-entry- (BL-159)
  - `uat_journey_203.py` — apply button testid corrected btn-apply-effect to apply-effect-btn (BL-161)
  - `uat_journey_203.py` — clip selection added before effect interactions (BL-166)
  - `uat_journey_203.py` — input selectors corrected from name= to data-testid= (BL-167)
  - `seed_sample_project.py` + `uat_journey_203.py` — timeline track seeding added (BL-168)
  - `uat_journey_203.py` + 204 — clip-block- and preset testids corrected to match components (BL-171)
  - `uat_journey_204.py` — --force flag added to seed invocation for fresh test data (BL-172)
  - `uat_journey_203.py` — filter-preview assertion removed from post-Apply step (BL-173)

- **Observability**
  - `scan.py`, `videos.py`, `manager.py` — 12 structured log events added throughout scan flow (BL-155)
  - `TimelinePage`, `TimelineCanvas`, `timeline.py` — console.debug and structlog events added (BL-160)
  - `effects.py` — `effect_preview_validation_failed` structlog warning added (BL-164)
  - `timeline.py` — `timeline_data_requested` log level promoted DEBUG to INFO (BL-169)

## [v022] - 2026-03-18

UAT (User Acceptance Testing) Framework. Browser-based UAT that validates complete user journeys against a live application instance, closing the end-user UX validation gap between API-level smoke tests and real-world usage.

### Added

- **UAT Runner Harness**
  - `scripts/uat_runner.py` with CLI (`--headed`/`--headless`, `--journey`, `--skip-build`, `--output-dir`)
  - Full build-boot-test-teardown lifecycle with health polling and sample data seeding
  - Dependency-aware fail-fast journey execution (graph: 201->202->203, 204 independent)
  - `uat` optional dependency group in `pyproject.toml`

- **Screenshot & Report Infrastructure**
  - `take_screenshot()` helper with naming convention and `FAIL_` prefix for failures
  - `ConsoleErrorCollector` class for filtered browser console error capture
  - JSON (`uat-report.json`) and markdown (`uat-report.md`) structured report generation

- **Auto-Dev Integration**
  - `docs/auto-dev/VERSION_CLOSURE.md` with tiered UAT automation (Tier 1: headless Playwright, Tier 2: manual fallback)
  - UAT acceptance tier added to testing pyramid in `docs/design/07-quality-architecture.md`

- **UAT Journey Scripts**
  - `uat_journey_201.py` — scan, browse, and FTS5 search workflow (5 steps, 5+ screenshots)
  - `uat_journey_202.py` — project creation, clip addition with in/out points, clips table verification (~290 lines)
  - `uat_journey_203.py` — effects apply/edit/remove, timeline canvas, layout presets (3 sub-journeys, 9 steps)
  - `uat_journey_204.py` — self-seeding Running Montage validation across clips, effects, and timeline pages (~280 lines)

## [v021] - 2026-03-17

Quality & API Completeness. Verifies the BL-138 timeline persistence fix, performs a formal DrawtextBuilder security review, fills five smoke test coverage gaps, and completes the API surface with version creation, filesystem pagination, and layout preset position endpoints.

### Added

- **Version Creation Endpoint**
  - `POST /projects/{id}/versions` returning 201 with auto-incremented version number and SHA-256 checksum

- **Filesystem Pagination**
  - `limit`/`offset` pagination on `GET /filesystem/directories` with `total`, `limit`, `offset` response metadata
  - Updated `DirectoryBrowser.tsx` to use paginated API

- **Preset Positions API**
  - Augmented `GET /compose/presets` with `positions` field served from Rust single source of truth
  - Deleted duplicated `presetPositions.ts` client-side constants

- **Smoke Test Gap Fill**
  - 5 new smoke tests: transition DELETE, audio_ducking, audio_fade, video_fade, acrossfade effect types

- **DrawtextBuilder Security Review**
  - 20 new Rust tests and 10 new Python tests for `escape_drawtext()` injection and Unicode handling
  - Formal security review document confirming no vulnerabilities

- **Timeline Persistence Integration Test**
  - SQLite close/reopen integration test verifying `track_id`, `timeline_start`, `timeline_end` survive DB round-trip (BL-138)

## [v020] - 2026-03-15

Sample Project: Running Montage. Delivers the complete sample project infrastructure for the Running Montage example, including a CLI seed script, smoke test fixture with effects and transitions, regression test, developer-facing user guide, and cross-artifact sync check in IMPACT_ASSESSMENT.

### Added

- **Running Montage Seed Script**
  - `scripts/seed_sample_project.py` — synchronous CLI script creating full Running Montage project (health check, video scan, project, 4 clips, 5 effects, 1 transition)

- **Sample Project Fixture Extensions**
  - Extended `sample_project` fixture in `tests/smoke/conftest.py` with effects and transition creation
  - Added `SAMPLE_EFFECT_DEFS` and `SAMPLE_TRANSITION_DEFS` shared constants

- **Sample Project Regression Test**
  - `tests/smoke/test_sample_project.py` validating project metadata, clip frames, source video associations, and effect-to-clip mappings against canonical constants

- **Sample Project User Guide**
  - `docs/setup/guides/sample-project.md` with prerequisites, quick start, data overview, API exploration, reset instructions, and developer cross-references

- **Sample Project Artifact Sync Check**
  - 5th check in `docs/auto-dev/IMPACT_ASSESSMENT.md` covering seed script, fixture, and guide synchronization across constant categories

## [v019] - 2026-03-14

Smoke Test Coverage Expansion. Extends the Phase 2 smoke test suite to cover 6 API surfaces introduced in v015-v018 (timeline clips, transitions, compose layout, video detail, version restore, filesystem directories), adds negative-path smoke tests for Phase 3 validation rules, and updates harness documentation to reflect Phase 2 completion.

### Added

- **Timeline Clip CRUD Smoke Tests**
  - PATCH position, PATCH track, and DELETE smoke tests for timeline clips in `test_timeline.py`

- **Timeline Transition Smoke Tests**
  - POST and DELETE smoke tests for timeline transitions
  - `create_adjacent_clips_timeline()` conftest helper for multi-clip timeline setup

- **Compose Layout Smoke Tests**
  - POST smoke test for compose layout preset application in `test_compose.py`

- **Video Detail Smoke Tests**
  - GET detail, GET thumbnail, and DELETE smoke tests for videos in `test_library.py`

- **Version Restore Smoke Tests**
  - POST restore smoke test with `create_version_repo()` factory helper for direct repository access

- **Filesystem Directory Smoke Tests**
  - GET directories smoke test with `tmp_path` fixtures and `dir_tree` deterministic fixture in `test_filesystem.py`

- **Negative-Path Smoke Tests**
  - 6 negative-path smoke tests covering timeline, audio, batch, and compose error handling
  - Validates consistent `{"detail": {"code": "...", "message": "..."}}` error response format

- **Harness Documentation Update**
  - Updated 6 documentation files to reflect Phase 1 implementation and Phase 2 expansion status

### Changed

- Smoke test suite expanded from ~22 to ~43 tests across timeline, compose, library, versions, and filesystem modules
- `conftest.py` extended with reusable helpers: `create_adjacent_clips_timeline()`, `create_version_repo()`

### Fixed

- N/A

## [v018] - 2026-03-13

GUI Timeline Canvas + Quality. Builds the visual composition interface (timeline canvas, clip visualization, layout preview), validates Phase 3 with comprehensive smoke and contract tests, and closes out Phase 3 with documentation and C4 architecture updates across all four levels.

### Added

- **Phase 3 Smoke Tests**
  - 5 smoke test files (7 tests) covering timeline, compose, batch render, versions, and audio mix endpoints
  - Full HTTP stack validation with real Rust core via `smoke_client` fixture

- **Phase 3 Contract Tests**
  - 6 contract tests validating overlay filters, composition graphs, and audio mix against real FFmpeg
  - Uses lavfi virtual inputs (`testsrc2`, `sine`) for portable, fast test execution

- **Timeline Page & Navigation**
  - `/gui/timeline` route with Timeline tab in navigation
  - `timelineStore` and `composeStore` Zustand stores with `isLoading`/`error`/`data` async pattern
  - Wired to Phase 3 timeline and compose API endpoints

- **Timeline Canvas**
  - `TimeRuler`, `Track`, `ZoomControls`, `TimelineCanvas` components
  - `timeToPixel()`/`pixelToTime()` coordinate utility for position-accurate rendering
  - Horizontal scroll and zoom controls

- **Clip Visualization & Playhead**
  - `TimelineClip` component with position-accurate rendering, click-to-select, and duration labels
  - `Playhead` component with time position indicator

- **Layout Preview Panel**
  - `LayoutSelector`, `LayoutPreview`, and `LayerStack` components
  - Preset selection consuming backend preset schema
  - Custom coordinate input support
  - Percentage-based CSS positioning for resolution-independent previews

- **Design Document Updates**
  - Updated 5 design docs (roadmap, architecture, API spec, quality architecture, GUI architecture) with Phase 3 content

- **Impact Assessment Patterns**
  - Phase 3 composition model grep patterns (TrackType, LayoutPosition, LayoutPreset, AudioMixSpec, BatchProgress) added to IMPACT_ASSESSMENT

- **C4 Architecture Documentation**
  - 58 Code-level docs across 10 directories covering all modules
  - 8 Component-level docs for all logical components
  - Container-level docs (containers.md, interfaces.md)
  - Context-level system-context.md
  - Covers 6 versions of accumulated drift (v009-v017)

### Changed

- GUI navigation extended with Timeline tab
- Frontend test suite expanded to 301 tests (104 new tests across timeline theme)
- C4 documentation fully regenerated from scratch for current codebase state

### Fixed

- N/A

## [v017] - 2026-03-13

Composition & Audio API + Batch. Delivers composition layout API with preset discovery and filter preview, audio mix configuration endpoints, WebSocket broadcast events for composition mutations, batch rendering with semaphore concurrency, and project version persistence with save/restore/list operations.

### Added

- **Configurable Server Port**
  - Default port changed from 8000 to 8765 to avoid conflicts
  - Wired through pydantic-settings with `SF_PORT` environment variable override
  - Updated 6 code/config files and 17 documentation files

- **Composition Layout API**
  - `GET /api/v1/compose/presets` endpoint returning all 7 Rust LayoutPreset variants with metadata
  - `POST /api/v1/projects/{id}/compose/layout` accepting preset or custom positions
  - FFmpeg filter preview generation via Rust `build_overlay_filter()` delegation
  - 30 tests across preset discovery and layout application

- **Audio Mix Configuration**
  - `PUT /api/v1/projects/{id}/audio/mix` for persisting audio mix settings
  - `POST /api/v1/projects/{id}/audio/mix/preview` for FFmpeg filter preview
  - Per-track volume, fade-in/fade-out, master volume, and normalize controls
  - Rust `AudioMixSpec` filter generation with `VolumeBuilder` semicolon concatenation
  - `audio_mix_json` column for JSON persistence following `transitions_json` pattern

- **Composition WebSocket Events**
  - 4 new `EventType` enums: `TIMELINE_UPDATED`, `LAYOUT_APPLIED`, `AUDIO_MIX_CHANGED`, `TRANSITION_APPLIED`
  - Broadcast wired into 8 mutation routes across timeline, compose, and audio routers
  - DRY `_broadcast()` helper pattern for consistent event dispatch

- **Batch Render Endpoint**
  - `POST /api/v1/render/batch` with `asyncio.Semaphore` concurrency control
  - `GET /api/v1/render/batch/{batch_id}` for batch status polling
  - Configurable `batch_parallel_limit` and `batch_max_jobs` settings with bounded ranges

- **Version Persistence**
  - `project_versions` table with SHA-256 checksum integrity verification
  - `AsyncVersionRepository` with SQLite and in-memory implementations
  - Contract tests ensuring parity between both repository backends
  - Non-destructive restore pattern (creates new version, preserves full history)

- **Version API Endpoints**
  - `GET /api/v1/projects/{id}/versions` with pagination support
  - `POST /api/v1/projects/{id}/versions/{version}/restore` with checksum validation

### Changed

- Default API port from 8000 to 8765 across all configuration and documentation
- Project model extended with `audio_mix_json` column for audio mix persistence
- Database schema extended with `project_versions` table for version storage
- Timeline, compose, and audio routers extended with WebSocket broadcast calls

### Fixed

- Clip repository SQL for timeline fields (`track_id`, `timeline_start`, `timeline_end`) now correctly included in UPDATE statements

## [v016] - 2026-03-11

Composition Graph + Timeline API. First full Phase 3 version delivering the Rust composition graph builder, multi-track audio mixing specification, batch progress calculator, timeline data layer with persistent storage, and complete timeline REST API with transition support.

### Added

- **AudioMixSpec & TrackAudioConfig (Rust)**
  - `AudioMixSpec` for coordinated multi-track audio mixing with per-track volume, fade-in/fade-out
  - `TrackAudioConfig` for individual track audio parameters
  - PyO3 bindings with proptest coverage for parameter validation

- **Batch Progress Calculator (Rust)**
  - `BatchJobStatus` enum with wrapper pyclass pattern for enum variant data
  - `BatchProgress` struct for batch render progress aggregation
  - `calculate_batch_progress()` pure function with PyO3 bindings

- **Composition Graph Builder (Rust)**
  - `build_composition_graph()` integrating overlay, scale, transitions, and audio mix into complete `FilterGraph` output
  - Sequential and layout composition modes with universal canvas base
  - PyO3 bindings with Python parity tests

- **Track & Clip Data Models (Python)**
  - `Track` dataclass for multi-track timeline representation
  - Extended `Clip` with nullable timeline fields: `track_id`, `timeline_start`, `timeline_end`
  - Database migration for `tracks` table and ALTER TABLE for clip timeline columns

- **Timeline Repository (Python)**
  - `AsyncTimelineRepository` with async CRUD for tracks and timeline-aware clip queries
  - `AsyncSQLiteTimelineRepository` and `InMemoryTimelineRepository` implementations
  - DI wiring via `create_app()` kwargs following established patterns

- **Timeline API Endpoints (Python)**
  - `PUT /api/v1/projects/{id}/timeline` — Initialize/replace timeline
  - `GET /api/v1/projects/{id}/timeline` — Get timeline with tracks and clips
  - `POST /api/v1/projects/{id}/timeline/clips` — Add clip to timeline
  - `PATCH /api/v1/projects/{id}/timeline/clips/{id}` — Update timeline clip
  - `DELETE /api/v1/projects/{id}/timeline/clips/{id}` — Remove clip from timeline
  - 6 Pydantic request/response schemas for timeline operations

- **Timeline Transition Endpoints (Python)**
  - `POST /api/v1/projects/{id}/timeline/transitions` — Create transition between adjacent clips
  - `DELETE /api/v1/projects/{id}/timeline/transitions/{id}` — Remove transition
  - Rust core integration via `calculate_composition_positions()` for offset calculation
  - Adjacency validation guard before Rust delegation

### Changed

- Clip model extended with nullable timeline fields for track assignment and timeline positioning
- Database schema extended with `tracks` table and clip timeline columns

### Fixed

- N/A

## [v015] - 2026-03-10

Phase 2 Quality Debt + Rust Layout/Composition Core. Retires all Phase 2 quality debt (coverage enforcement, property testing, FFmpeg contract tests, performance benchmarks) and builds the foundational Rust layout and composition modules for Phase 3.

### Added

- **Unit Test Coverage Enforcement**
  - Achieved >95% line coverage for all 8 `src/ffmpeg/` modules with error path tests
  - CI enforcement step parsing `cargo llvm-cov --json` for per-module coverage checks

- **Property-Based Testing (Filter Builders)**
  - 12 proptest strategies across drawtext, speed, audio, and transitions builders
  - Coverage of both valid and invalid parameter ranges for thorough edge case detection

- **FFmpeg Contract Tests**
  - 15 contract tests validating Phase 2 filter builder outputs against real FFmpeg execution
  - `@requires_ffmpeg` marker for graceful CI skip in environments without FFmpeg

- **Performance Benchmarks**
  - 15 Criterion benchmarks across 7 groups for filter builders
  - Baseline performance measurements with HTML reports in `target/criterion/`

- **LayoutPosition (Rust)**
  - `LayoutPosition` struct with normalized coordinates (0.0–1.0), `to_pixels()` conversion, and `validate()`
  - `LayoutError` exception type for invalid coordinate values
  - PyO3 bindings with proptest coverage for pixel rounding edge cases

- **LayoutPreset (Rust)**
  - `LayoutPreset` enum with 7 variants: 4 PIP corners, SideBySide, TopBottom, Grid2x2
  - `positions(input_count)` method returning `Vec<LayoutPosition>` for preset layouts
  - PyO3 bindings with manual type stubs (pyo3-stub-gen does not support enums)

- **Overlay & Scale Filter Builders (Rust)**
  - `build_overlay_filter()` and `build_scale_for_layout()` in `compose/overlay` module
  - Converts LayoutPosition to FFmpeg filter strings with `force_divisible_by=2` for codec compatibility
  - PyO3 bindings, proptest strategies, and FFmpeg contract tests

- **Composition Position Calculator (Rust)**
  - `CompositionClip` and `TransitionSpec` structs for multi-clip timeline representation
  - `calculate_composition_positions()` and `calculate_timeline_duration()` with transition overlap clamping
  - PyO3 bindings and comprehensive tests for clamping edge cases

### Changed

- N/A

### Fixed

- N/A

## [v014] - 2026-03-09

Phase 2 Smoke Test. API-level smoke test suite exercising the full backend stack (HTTP → FastAPI → Services → PyO3/Rust → SQLite) with real video files, providing a verified Phase 2 baseline before Phase 3 begins.

### Added

- **Smoke Test Infrastructure**
  - `tests/smoke/` directory with `conftest.py` containing `EXPECTED_VIDEOS` dict, 5 fixtures (`videos_dir`, `smoke_client`, `sample_project`, etc.), and 3 async helpers
  - 6 real MP4 video files committed to git for deterministic, cross-platform test inputs
  - Lifespan-aware `smoke_client` fixture wrapping `httpx.AsyncClient` inside `async with lifespan(app)`
  - Per-test DB isolation via `tmp_path` for independent, parallelizable smoke tests
  - Default exclusion via `--ignore=tests/smoke` in pytest addopts to keep fast unit test loop unaffected

- **Core Workflow Smoke Tests**
  - 7 use cases across 4 test files covering scan, library, project, and clip workflows
  - Full-stack validation: HTTP → FastAPI → Services → PyO3/Rust → SQLite

- **Effects, Transitions & Health Smoke Tests**
  - 5 use cases across 3 test files covering effect catalog/apply, effect update/delete, fade transitions, health endpoints, and speed control + stacking
  - Full-stack exercise through Rust PyO3 filter builders validating filter-string output shape

- **CI Integration & Maintenance**
  - CI `smoke-tests` job running on 3 OS × Python 3.12 matrix
  - `pytest-timeout` dependency for smoke test time bounds
  - `IMPACT_ASSESSMENT.md` updated with 3 maintenance checks using grep-pattern approach
  - AGENTS.md quality gates updated with smoke test guidance

### Changed

- `--no-cov` flag used for smoke tests to avoid coverage threshold failures on integration-focused tests

### Fixed

- N/A

## [v013] - 2026-03-07

Scan Dialog Freeze Fix. Fixes the P0 scan dialog freeze where the progress bar reached 100% but the completion branch never fired, and adds timeout status handling so timed-out scans show an error instead of polling indefinitely.

### Added

- N/A

### Changed

- N/A

### Fixed

- **Scan Dialog Freeze (BL-080)**
  - Fixed `'completed'` vs `'complete'` string mismatch between frontend `JobStatus` type union and backend `JobStatus.COMPLETE` enum in `ScanModal.tsx`
  - Updated polling comparison and test mock atomically
  - Added integration test for scan completion flow (running -> complete -> onScanComplete fires)
- **Timeout Status Handling**
  - Added `'timeout'` to frontend `JobStatus` type union
  - Added timeout error handling branch mirroring the existing `'failed'` pattern
  - Timed-out scans now show an error message instead of polling indefinitely

## [v012] - 2026-02-25

API Surface & Bindings Cleanup. Removes 11 unused PyO3 bindings and 1 dead bridge function from the Rust-Python boundary, wires transition effects into the Effect Workshop GUI, and corrects misleading API specification examples.

### Added

- **Transition GUI in Effect Workshop**
  - Transitions tab on EffectsPage with clip-pair selection mode
  - `transitionStore` Zustand store for transition state management
  - `TransitionPanel` component with schema-driven parameter forms via `EffectParameterForm` reuse
  - `ClipSelector` extended with optional pair-mode props for two-clip selection flow
  - Non-adjacent-clip error feedback from existing `POST /api/v1/effects/transition` endpoint

### Removed

- **Dead `execute_command()` Bridge Function**
  - Removed `execute_command()` function and `CommandExecutionError` class from `stoat_ferret.ffmpeg.integration`
  - Removed exports from `stoat_ferret.ffmpeg` package `__init__.py`
  - Deleted `tests/test_integration.py` (13 tests covering only the removed function)
  - Zero production callers — `ThumbnailService` calls `executor.run()` directly
  - **Re-add trigger:** Phase 3 Composition Engine or any future render/export endpoint needing Rust command building (LRN-029)

- **Unused v001 PyO3 Bindings (BL-067)**
  - Removed `find_gaps`, `merge_ranges`, `total_coverage` PyO3 wrappers from `timeline/range.rs`
  - Removed `validate_crf`, `validate_speed` PyO3 wrappers from `sanitize/mod.rs`
  - Removed 5 functions from Python module registration, imports, stubs, and `__all__`
  - Removed `TestRangeListOperations` class (~15 tests) and `TestSanitization` crf/speed tests (~4 tests) from `tests/test_pyo3_bindings.py`
  - Deleted `benchmarks/bench_ranges.py` (3 benchmarks referencing removed bindings)
  - Rust-internal implementations preserved; zero production callers
  - **Re-add triggers:** TimeRange ops: Phase 3 Composition Engine; sanitization: Python-level standalone validation need

- **Unused v006 PyO3 Bindings (BL-068)**
  - Removed `Expr` (PyExpr) PyO3 wrapper from `ffmpeg/expression.rs`
  - Removed `validated_to_string`, `compose_chain`, `compose_branch`, `compose_merge` PyO3 wrappers from `ffmpeg/filter.rs`
  - Removed 6 bindings from Python module registration, imports, stubs, and `__all__`
  - Removed `TestExpr` class (~16 tests) and `TestFilterComposition` class (~15 tests) from `tests/test_pyo3_bindings.py`
  - Rust-internal implementations preserved; zero production callers
  - **Re-add triggers:** Expr: Python-level expression building for custom filter effects; compose: Python-level filter graph composition outside Rust builders

### Changed

- N/A

### Fixed

- **API Spec Documentation Corrections**
  - Fixed 6 job status example values in API specification and manual to use 0.0–1.0 normalized floats matching actual code behavior
  - Corrected running, complete, cancel, failed, and timeout progress examples
  - Fixed manual range documentation for progress field
  - Added `cancelled` status to documented job status values

## [v011] - 2026-02-24

GUI Usability & Developer Experience. Closes the biggest GUI interaction gaps with a directory browser for scan path selection and full clip CRUD controls, then improves developer onboarding with environment template, Windows guidance, and design-time impact assessment checks.

### Added

- **Directory Browser**
  - `GET /api/v1/filesystem/directories` endpoint with `validate_scan_path()` security enforcement
  - `DirectoryBrowser` overlay component in ScanModal for selecting scan paths
  - Non-blocking filesystem access via `run_in_executor` for `os.scandir()`

- **Clip CRUD Controls**
  - Add/Edit/Delete clip controls on ProjectDetails page
  - `ClipFormModal` with form validation for clip in/out points
  - `clipStore` Zustand store following per-entity pattern (like `effectStackStore`)
  - Wired to existing backend POST/PATCH/DELETE clip endpoints

- **Environment Template**
  - `.env.example` covering all 11 Settings fields with inline documentation
  - Cross-references added to AGENTS.md, quickstart guide, and contributing docs

- **Windows Developer Guidance**
  - Git Bash `/dev/null` pitfall documentation added to AGENTS.md Windows section

- **Impact Assessment**
  - `IMPACT_ASSESSMENT.md` with 4 design-time checks: async safety, settings documentation, cross-version wiring, GUI input mechanisms (BL-076)
  - Captures recurring issue patterns for early detection during version design

### Changed

- ScanModal now includes embedded DirectoryBrowser overlay for path selection instead of manual text entry only

### Fixed

- N/A

## [v010] - 2026-02-23

Async Pipeline Fix & Job Controls. Fixes the P0 blocking subprocess.run() in ffprobe that froze the asyncio event loop during scans, adds CI guardrails and runtime regression tests to prevent recurrence, then builds user-facing job progress reporting and cooperative cancellation on the working pipeline.

### Added

- **Async FFprobe**
  - `ffprobe_video()` converted from blocking `subprocess.run()` to `asyncio.create_subprocess_exec()` with timeout and process cleanup
  - 30-second configurable timeout with proper process termination on timeout/cancellation

- **Async Blocking CI Gate**
  - Ruff ASYNC rules (ASYNC210, ASYNC221, ASYNC230) enabled to detect blocking calls in async functions at CI time
  - `_check_ffmpeg()` in health.py wrapped with `asyncio.to_thread()` to comply with new rules

- **Event-Loop Responsiveness Test**
  - Integration test verifying asyncio event loop stays responsive (< 2s jitter) during directory scans
  - Uses production `AsyncioJobQueue` to exercise real async concurrency

- **Job Progress Reporting**
  - `progress` field added to job entries (percentage, current file index, total files)
  - Scan handler reports per-file progress via `progress_callback`
  - Progress exposed via `GET /api/v1/jobs/{id}` endpoint

- **Cooperative Job Cancellation**
  - `cancel_event` (`asyncio.Event`) for cooperative cancellation signaling
  - `POST /api/v1/jobs/{id}/cancel` endpoint with 200/404/409 status codes
  - Scan handler checks cancellation at per-file checkpoints, saves partial results
  - Frontend abort button with Vitest test coverage

### Changed

- `scan_directory()` pre-collects video files for accurate progress total instead of lazy glob iteration
- `AsyncJobQueue` Protocol extended with `set_progress()` and `cancel()` methods
- `InMemoryJobQueue` updated with no-op stubs for new protocol methods

### Fixed

- P0: `ffprobe_video()` no longer freezes the asyncio event loop during directory scans (BL-072)

## [v009] - 2026-02-22

Observability Pipeline & GUI Runtime Fixes. Wires pre-existing observability components (FFmpeg metrics, audit logging, file-based logs) into the application's DI chain and startup sequence, and fixes three GUI runtime gaps (SPA routing fallback, projects pagination, WebSocket broadcasts).

### Added

- **FFmpeg Observability Wiring**
  - `ObservableFFmpegExecutor` wired into DI chain via lifespan; FFmpeg operations now emit Prometheus metrics and structured logs in production
  - Test-injection bypass preserves clean test doubles without observable wrapper noise

- **Audit Logging Wiring**
  - `AuditLogger` wired into repository DI with separate sync `sqlite3.Connection` alongside `aiosqlite`
  - WAL mode enables concurrent sync/async access without deadlocks
  - Database mutations now produce audit entries automatically

- **File-Based Logging**
  - `RotatingFileHandler` integrated into `configure_logging()` with 10MB rotation and 5 backup files
  - `logs/` directory auto-created on startup
  - Idempotent handler registration prevents duplicate file handlers

- **SPA Routing Fallback**
  - Replaced `StaticFiles` mount with catch-all FastAPI routes (`/gui` and `/gui/{path:path}`)
  - Static files served directly; unmatched paths fall back to `index.html` for client-side routing

- **Projects Pagination Fix**
  - `count()` added to `AsyncProjectRepository` protocol (SQLite `SELECT COUNT(*)`, InMemory `len()`)
  - API endpoint returns true total count instead of page result length
  - Frontend pagination UI added to projects page matching library browser pattern

- **WebSocket Broadcasts**
  - `ConnectionManager.broadcast()` wired into project creation (`PROJECT_CREATED`) and scan handler (`SCAN_STARTED`, `SCAN_COMPLETED`)
  - Guard pattern (`if ws_manager:`) allows broadcasts to be optional without affecting tests or minimal deployments

### Changed

- Lifespan startup sequence extended with FFmpeg observability wrapping, audit logger initialization, and file handler registration
- SPA routing uses catch-all routes instead of `StaticFiles` mount for GUI paths
- Projects list endpoint returns accurate pagination total via repository `count()`

### Fixed

- Direct navigation to GUI sub-paths (e.g., `/gui/library`) no longer returns 404
- Projects pagination total now reflects actual dataset size instead of current page length

## [v008] - 2026-02-22

Application Startup Wiring & CI Stability. Wires disconnected infrastructure — database schema creation, structured logging, and orphaned settings — into the FastAPI lifespan startup sequence, and fixes a flaky E2E test that intermittently blocked CI merges.

### Added

- **Database Startup Wiring**
  - `create_tables_async()` called in lifespan so database schema is created automatically on fresh startup
  - 3 duplicate test helpers consolidated into shared import

- **Logging Startup Wiring**
  - `configure_logging()` wired into lifespan with `settings.log_level` controlling verbosity
  - Idempotent handler guard prevents duplicate log handlers
  - Uvicorn log level made configurable from settings

- **Orphaned Settings Wiring**
  - `settings.debug` wired to `FastAPI(debug=...)` for error detail control
  - `settings.ws_heartbeat_interval` replaces hardcoded constant in WebSocket manager
  - All 9 `Settings` fields now consumed by production code

### Changed

- Lifespan startup sequence extended with database schema creation and logging configuration
- WebSocket heartbeat interval now driven by settings instead of hardcoded value

### Fixed

- Flaky E2E `toBeHidden()` assertion in `project-creation.spec.ts` — added explicit 10-second timeout matching established pattern in other specs (BL-055)

## [v007] - 2026-02-19

Effect Workshop GUI. Implements Rust filter builders for audio mixing and video transitions, refactors the effect registry to builder-protocol dispatch with JSON schema validation, builds the complete GUI effect workshop (catalog, parameter forms, live preview, builder workflow), and validates with E2E tests and accessibility compliance. Covers milestones M2.4–M2.6, M2.8–M2.9.

### Added

- **Audio Mixing Builders (Rust)**
  - `AmixBuilder` for multi-input audio mixing with weighted inputs and dropout handling
  - `VolumeBuilder` for audio level adjustment with expression support
  - `AfadeBuilder` for audio fade-in/fade-out with configurable curves (FadeCurve enum)
  - `DuckingPattern` for multi-filter audio ducking using FilterGraph composition API
  - 54 Rust unit tests + 42 Python parity tests

- **Transition Filter Builders (Rust)**
  - `FadeBuilder` for video fade-in/fade-out with alpha channel support
  - `XfadeBuilder` with `TransitionType` enum covering all 59 FFmpeg xfade variants
  - `AcrossfadeBuilder` for combined audio crossfade + video xfade transitions
  - Reused `FadeCurve` enum from audio module for cross-domain consistency
  - 35 Rust unit tests + 46 Python parity tests

- **Effect Registry Refactor**
  - Builder-protocol dispatch via `build_fn` field on `EffectDefinition`, replacing if/elif monolith
  - JSON schema validation using `jsonschema.Draft7Validator` with structured error messages
  - 9 effects registered with self-contained build functions and parameter schemas
  - Prometheus counter for effect build operations

- **Transition API**
  - `POST /api/v1/effects/transition` endpoint with clip adjacency validation
  - Specific error codes: `SAME_CLIP`, `EMPTY_TIMELINE`, `NOT_ADJACENT`
  - Persistent transition storage via `transitions_json` column on Project model

- **Effect Catalog UI**
  - Grid/list view of available effects with search (300ms debounce) and category filter
  - AI hint tooltips from effect registry metadata
  - Effect selection dispatched to parameter form

- **Dynamic Parameter Forms**
  - Schema-driven `SchemaField` dispatcher rendering typed sub-components
  - Input widgets: number/range slider, string, enum dropdown, boolean toggle, color picker
  - Validation from JSON schema constraints with dirty-state tracking

- **Live Filter Preview**
  - `POST /api/v1/effects/preview` endpoint returning built filter strings
  - Debounced preview panel with regex-based FFmpeg syntax highlighting
  - Copy-to-clipboard functionality

- **Effect Builder Workflow**
  - Clip selector component for choosing target clips
  - Effect stack visualization with ordering
  - `PATCH /api/v1/projects/{id}/clips/{id}/effects/{index}` for editing effects
  - `DELETE /api/v1/projects/{id}/clips/{id}/effects/{index}` for removing effects
  - Full CRUD lifecycle: browse catalog → configure parameters → preview → apply → edit/remove

- **E2E Testing & Accessibility**
  - 8 Playwright E2E tests covering catalog browse, parameter config, apply/edit/remove workflow
  - Keyboard navigation test (Tab, Enter, Space through full workflow)
  - axe-core WCAG AA accessibility scans on effect workshop pages
  - Serial test mode for stateful CRUD test group

- **Documentation Updates**
  - API specification updated with 3 new endpoints (preview, PATCH, DELETE)
  - Roadmap milestones M2.4, M2.5, M2.6, M2.8, M2.9 marked complete
  - GUI architecture document updated with Effect Workshop components
  - C4 architecture documentation regenerated at all levels

### Changed

- Effect registry dispatch refactored from monolithic if/elif to per-definition `build_fn` callables
- Project model extended with `transitions_json` column for persistent transition storage
- Effects router simplified — dispatch delegated to registry lookup

### Fixed

- Parameter validation errors now return structured messages from JSON schema validation instead of opaque PyO3 type coercion failures

## [v006] - 2026-02-19

Effects Engine Foundation. Builds a greenfield Rust filter expression engine with graph validation, composition system, text overlay and speed control builders, effect discovery API, and clip effect application endpoint. Completes Phase 2 core milestones (M2.1-M2.3).

### Added

- **Filter Expression Engine (Rust)**
  - `Expr` enum with type-safe builder API for FFmpeg filter expressions
  - Operator overloading and precedence-aware serialization (minimizes parentheses)
  - FFmpeg variable support (`t`, `n`, `w`, `h`, etc.) and function calls (`if`, `lt`, `between`, etc.)
  - Proptest validation for expression correctness (balanced parens, no NaN/Inf)
  - Full PyO3 bindings with Python type stubs

- **Filter Graph Validation (Rust)**
  - Opt-in `validate()` and `validated_to_string()` methods on `FilterGraph`
  - Unconnected pad detection, duplicate label detection
  - Cycle detection using Kahn's algorithm (O(V+E)) with involved-label error messages
  - Backward-compatible: existing `to_string()` behavior unchanged

- **Filter Composition API (Rust)**
  - `compose_chain`, `compose_branch`, `compose_merge` programmatic composition functions
  - `LabelGenerator` with thread-safe `AtomicU64` counter for automatic pad label management
  - Auto-generated `_auto_{prefix}_{seq}` labels for debugging clarity

- **DrawtextBuilder (Rust)**
  - Type-safe drawtext filter builder with fluent API
  - Position presets enum (Center, BottomCenter, TopLeft, etc.) with margin parameters
  - Font styling (family, size, color), shadow and box background effects
  - Alpha fade animation via expression engine integration
  - Extended text escaping (`%` -> `%%` for drawtext expansion mode)

- **SpeedControl (Rust)**
  - `setpts` video speed builder with expression-based PTS manipulation
  - `atempo` audio speed builder with automatic chaining for speeds outside [0.5, 2.0]
  - Decomposition algorithm for extreme speeds (e.g., 4x -> atempo=2.0,atempo=2.0)
  - Drop-audio option for video-only speed changes
  - Proptest validation for atempo chain product correctness and bound compliance

- **Effect Discovery API (Python)**
  - `EffectRegistry` with parameter schemas and AI hints for each registered effect
  - `GET /api/v1/effects` endpoint returning available effects with metadata
  - Preview function integration (previewed filters match applied filters)

- **Clip Effect Application API (Python)**
  - `POST /api/v1/projects/{id}/clips/{id}/effects` endpoint
  - Effect storage as JSON list column in clip model (`effects_json TEXT`)
  - DrawtextBuilder and SpeedControl dispatch from API parameters
  - DI via `create_app()` kwarg -> `app.state.effect_registry` pattern

- **Architecture Documentation**
  - Updated `02-architecture.md` with Rust filter modules, Effects Service, and clip model extension
  - API specification reconciled with actual implementation
  - C4 architecture documentation regenerated at all levels

### Changed

- Clip model extended with `effects_json` column for persistent effect storage
- Effects router serves both global (`/api/v1/effects`) and per-clip (`/api/v1/projects/{id}/clips/{id}/effects`) routes

### Fixed

- N/A (greenfield implementation)

## [v005] - 2026-02-09

GUI Shell, Library Browser & Project Manager. Builds the frontend from scratch: React/TypeScript/Vite project, WebSocket real-time events, backend thumbnail pipeline, four main GUI panels, and Playwright E2E testing. Completes Phase 1 (M1.10-M1.12).

### Added

- **Frontend Foundation**
  - React/TypeScript/Vite project scaffolded in `gui/` with Tailwind CSS v4
  - FastAPI StaticFiles mount at `/gui` with conditional directory check
  - CI `frontend` job for build/lint/test in parallel with Python matrix
  - WebSocket endpoint (`/ws`) with `ConnectionManager`, heartbeat, correlation IDs
  - Lazy dead connection cleanup during broadcast with `asyncio.Lock`
  - Settings fields: `thumbnail_dir`, `gui_static_path`, `ws_heartbeat_interval`

- **Backend Services**
  - `ThumbnailService` with FFmpeg executor pattern for video thumbnail extraction
  - `GET /api/v1/videos/{id}/thumbnail` endpoint with placeholder fallback
  - Scan-time automatic thumbnail generation
  - `AsyncVideoRepository.count()` protocol method (SQLite and InMemory)
  - Paginated list endpoint now returns true total count (not page length)

- **GUI Components**
  - Application shell with header/content/footer layout and tab navigation via React Router
  - Health indicator polling `/health/ready` every 30s (green/yellow/red)
  - WebSocket hook with auto-reconnect and exponential backoff (1s to 30s)
  - Dashboard panel with health cards (Python API, Rust Core, FFmpeg) and real-time activity log
  - Prometheus metrics cards parsing text format for request count/duration
  - Library browser with responsive video grid, thumbnails, search (300ms debounce), sort controls, scan modal with progress, and pagination
  - Project manager with list view, creation modal (resolution/fps/format validation), project details with timeline positions, and delete confirmation
  - Three Zustand stores: activity, library, project

- **E2E Testing**
  - Playwright configuration with `webServer` auto-starting FastAPI
  - CI `e2e` job on ubuntu-latest with Chromium browser caching
  - Navigation, scan trigger, project creation, and WCAG AA accessibility E2E tests
  - axe-core accessibility checks on all three main views

### Changed

- `create_app()` auto-loads `gui_static_path` from settings when not explicitly provided
- Architecture, API, and AGENTS documentation updated for frontend and WebSocket

### Fixed

- SortControls WCAG 4.1.2 violation: added missing `aria-label` attribute
- Pagination `total` field now returns true dataset count instead of page result count

## [v004] - 2026-02-09

Testing Infrastructure & Quality Verification. Establishes test doubles, dependency injection, fixture factories, black box and contract tests, async scan infrastructure, security audit, performance benchmarks, and developer experience tooling.

### Added

- **Test Foundation**
  - InMemory test doubles for all repositories with deepcopy isolation and seed helpers
  - Constructor-based dependency injection via `create_app()` kwargs on `app.state`
  - Builder-pattern fixture factory with `build()` (unit) and `create_via_api()` (integration) outputs
  - `InMemoryJobQueue` for deterministic synchronous job execution in tests

- **Black Box & Contract Testing**
  - 30 REST API black box workflow tests (project CRUD, clips, error handling, edge cases)
  - 21 parametrized FFmpeg contract tests verifying Real, Recording, and Fake executor parity
  - `strict` mode for FFmpeg executor args verification
  - Per-token `startswith` search in InMemory repositories matching FTS5 prefix semantics
  - 7 search parity tests ensuring InMemory/SQLite consistency

- **Async Scan Infrastructure**
  - `AsyncioJobQueue` using `asyncio.Queue` producer-consumer pattern with background worker
  - `POST /videos/scan` now returns `202 Accepted` with `job_id` for async processing
  - `GET /api/v1/jobs/{job_id}` endpoint for job status polling
  - Handler registration pattern with `make_scan_handler()` factory for DI
  - Configurable per-job timeout (default 5 minutes)

- **Security & Performance**
  - Security audit of all 8 Rust sanitization/validation functions against OWASP vectors
  - `ALLOWED_SCAN_ROOTS` configuration with `validate_scan_path()` enforcement
  - 35 security tests across 5 attack categories (path traversal, null bytes, shell injection, whitelist bypass, FFmpeg filter injection)
  - Performance benchmark suite comparing Rust vs Python across 7 operations in 4 categories
  - Security audit document (`docs/design/09-security-audit.md`)
  - Performance benchmark document (`docs/design/10-performance-benchmarks.md`)

- **Developer Experience & Coverage**
  - Property-based testing guidance with Hypothesis dependency and design template integration
  - Rust code coverage via `cargo-llvm-cov` with 75% CI threshold
  - Docker-based testing environment with multi-stage build (`Dockerfile`, `docker-compose.yml`)
  - `@pytest.mark.requires_ffmpeg` marker for conditional CI execution

### Changed

- `POST /videos/scan` refactored from synchronous blocking to async job queue pattern
- Design documents updated to reflect async scan behavior (`02-architecture.md`, `03-prototype-design.md`, `04-technical-stack.md`, `05-api-specification.md`)
- Requirements and implementation-plan templates updated with property test (PT-xxx) sections

### Fixed

- Coverage exclusion audit: removed unjustified `pragma: no cover` on ImportError fallback in `__init__.py`, added fallback tests

## [v003] - 2026-01-28

API Layer + Clip Model (Roadmap M1.6-1.7). Establishes FastAPI REST API, async repository layer, video library endpoints, clip/project data models with Rust validation, and CI improvements.

### Added

- **Process Improvements**
  - `AsyncVideoRepository` protocol with async SQLite and in-memory implementations
  - CI migration verification step (upgrade → downgrade → upgrade)
  - CI path filters using `dorny/paths-filter` to skip heavy tests for docs-only changes
  - Three-job CI structure (changes → test → ci-status) for branch protection

- **API Foundation**
  - FastAPI application factory with lifespan context manager for database lifecycle
  - Externalized configuration using pydantic-settings with environment variable support
  - Health endpoints: `/health/live` (liveness) and `/health/ready` (readiness with dependency checks)
  - Middleware stack with correlation ID (`X-Correlation-ID` header) and Prometheus metrics

- **Library API**
  - `GET /api/v1/videos` - List videos with pagination (offset/limit)
  - `GET /api/v1/videos/{video_id}` - Get video details by ID
  - `GET /api/v1/videos/search` - Full-text search with FTS5 integration
  - `POST /api/v1/videos/scan` - Directory scanning with FFprobe metadata extraction
  - `DELETE /api/v1/videos/{video_id}` - Delete video with optional file removal (`delete_file` flag)

- **Clip Model**
  - `Project` model for organizing clips with output settings (resolution, fps)
  - `Clip` model with in/out points delegating validation to Rust core
  - `AsyncProjectRepository` and `AsyncClipRepository` with SQLite and in-memory implementations
  - `GET/POST /api/v1/projects` - List and create projects
  - `GET/PUT/DELETE /api/v1/projects/{project_id}` - Project CRUD operations
  - `GET/POST /api/v1/projects/{project_id}/clips` - List and create clips
  - `GET/PUT/DELETE /api/v1/clips/{clip_id}` - Clip CRUD operations

### Changed

- Repository pattern now supports both sync (CLI) and async (API) access
- CI workflow now conditionally runs tests based on changed paths
- pytest-asyncio configured with `asyncio_mode = "auto"` for cleaner async tests

### Fixed

- CI migration reversibility now verified automatically on every push

## [v002] - 2026-01-27

Database & FFmpeg Integration with Python Bindings Completion. Addresses roadmap M1.4-1.5.

### Added

- **Python Bindings Completion**
  - `Clip` and `ClipValidationError` types exposed to Python with full property access
  - `find_gaps`, `merge_ranges`, and `total_coverage` functions for TimeRange operations
  - Automatic stub generation verification script (`scripts/verify_stubs.py`)
  - CI drift detection for stub files

- **Database Foundation**
  - SQLite schema with 14-column `videos` table for video metadata storage
  - FTS5 full-text search with automatic index synchronization via triggers
  - `VideoRepository` protocol with SQLite and InMemory implementations
  - Alembic migration support with rollback capability
  - Audit logging for tracking all data modifications (`audit_log` table)

- **FFmpeg Integration**
  - FFprobe wrapper for extracting structured video metadata (`VideoMetadata` dataclass)
  - `FFmpegExecutor` protocol with Real, Recording, and Fake implementations
  - Integration layer bridging Rust `FFmpegCommand` to Python executor
  - Recording/replay pattern for deterministic subprocess testing
  - `ObservableFFmpegExecutor` wrapper with structured logging (structlog)
  - Prometheus metrics for FFmpeg command execution (duration, success/failure counts)

- **Process Documentation**
  - PyO3 bindings section in AGENTS.md with incremental binding rule
  - Stub regeneration workflow documentation
  - Naming convention guidance (`py_` prefix with `#[pyo3(name)]` attribute)

### Changed

- API naming cleanup: removed `py_` prefixes from 16 Python-visible method names
- Updated 37 test assertions for new API naming
- Renamed Rust `ValidationError` to `ClipValidationError` in Python for clarity

### Fixed

- Stub drift between generated and manual stubs now caught by CI verification

## [v001] - 2026-01-26

Foundation version establishing hybrid Python/Rust architecture with timeline math and FFmpeg command building.

### Added

- **Project Foundation**
  - Python project structure with uv, ruff, mypy, and pytest
  - Rust workspace with PyO3 bindings (abi3-py310)
  - GitHub Actions CI pipeline (Ubuntu, Windows, macOS × Python 3.10, 3.11, 3.12)
  - Type stubs for IDE support and mypy integration

- **Timeline Math (Rust)**
  - `FrameRate` type with rational numerator/denominator representation
  - `Position` type for frame-accurate timeline positions
  - `Duration` type for frame-accurate time spans
  - `Clip` type with validation (start, end, media_start, media_duration)
  - `ValidationError` with field, message, actual, and expected values
  - `TimeRange` with half-open interval semantics
  - Range operations: overlap, intersection, union, subtraction, contains
  - List operations: find_gaps, merge_ranges (O(n log n))
  - Property-based tests for invariants (proptest)

- **FFmpeg Command Builder (Rust)**
  - `FFmpegCommand` fluent builder with input/output management
  - Position-sensitive option handling (seek, codecs, filters)
  - `Filter`, `FilterChain`, and `FilterGraph` types
  - Common filter constructors: scale, pad, fps, setpts, concat, atrim
  - Input sanitization: text escaping, path validation, bounds checking
  - Codec and preset whitelist validation
  - Complete PyO3 bindings with method chaining support

- **Python API**
  - `stoat_ferret_core` module with all Rust types exposed
  - ImportError fallback for development without Rust builds
  - Full type stubs in `stubs/stoat_ferret_core/`

### Changed

- N/A (initial release)

### Fixed

- N/A (initial release)

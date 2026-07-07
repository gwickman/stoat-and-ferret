# STATUS.md

## v099 — Image/Generator Clip Types + Windowed Effects

**Delivered:** 2026-07-07
**PRs:** #753, #754, #756, #757 (4 merged; #755 open)
**Tests:** 3745 collected (uv run pytest --collect-only -q)

### Highlights

- Per-clip parameter fix: parameters dict now passed to build_fn in render worker — BL-615
- Clip-type routing: extended render worker to handle image and generator clip types — BL-604, BL-511
- R3 acceptance tests and cleanup for render worker coverage — BL-604-AC-3
- WindowSpec data structure and windowed_custom() factory for windowed effects — BL-512
- Windowed effect dispatch in worker.py with enable=between(t,s,e) emission in translate.rs — BL-512

### Theme Summary

| Theme | BL Items | PRs | Status |
|-------|----------|-----|--------|
| render-worker-clip-coverage | BL-615, BL-604, BL-511 | #753, #754 | merged; #755 open |
| windowed-effects-integration | BL-512 | #756, #757 | merged |

### AC Status

- Theme 1: per-clip param and image/generator routing merged; R3 acceptance tests pending PR #755 merge
- Theme 2: 2 features merged; WindowSpec factory and windowed effect dispatch
- Total: 4 PRs merged; PR #755 open; intent fulfilment partial (BL-512-AC-2 non-T path and BL-512-AC-4 deferred to v100; BL-604-AC-3/4/5 pending PR #755 merge)

### Carry-Forwards

| Item | Description | Status |
|------|-------------|--------|
| BL-512-AC-2 | Windowed effects non-T path (frame-based addressing) | Deferred to v100 |
| BL-512-AC-4 | Windowed effects preview automation | Deferred to v100 |
| BL-604-AC-3/4/5 | R3 acceptance tests + E2E discharge cross-links | Pending PR #755 merge |

### User Actions Required

None required.

## v098 — FFmpeg-8 Correctness + STOAT_TEST_FFMPEG CI Lane + Multi-Clip Render Closure

**Delivered:** 2026-07-06
**PRs:** #744, #745, #746, #747, #748, #749, #750 (7 PRs)
**Tests:** 3680 passing (baseline 3591, +89)

### Highlights

- Pan `aeval` comma escape fix: PanBuilder now single-quotes filter expressions — BL-610
- Opacity `geq` test fix: 3-part FFmpeg 8 compat fix to `_mean_alpha` — BL-611
- Animated alpha `geq` uppercase T fix in `translate.rs` — BL-602
- Dedicated `ffmpeg-tests` CI job added: FFmpeg 8.x, `STOAT_TEST_FFMPEG=1`, F1–F5 triage — BL-607
- AGENTS.md + smoke-test docs updated with CI lane documentation — BL-607
- `RenderEffect.custom()` added, `ValueKind` enum + `emit_filter_value` dispatch, 4 builders migrated, wired `worker.py` — BL-555
- SSIM gated tests added; xfade `offset=` bug discovered and fixed in `RenderGraphTranslator` — BL-505/BL-553

### Theme Summary

| Theme | BL Items | PRs | Status |
|-------|----------|-----|--------|
| ffmpeg-8-correctness | BL-610, BL-611, BL-602 | #744, #745, #746 | merged |
| stoat-test-ffmpeg-ci-lane | BL-607 | #747, #748 | merged |
| render-pipeline-closure | BL-555, BL-505, BL-553 | #749, #750 | merged |

### AC Status

- Theme 1: 3 BL items, all correctness fixes merged and verified
- Theme 2: CI lane active on all matrix variants; `STOAT_TEST_FFMPEG=1` gates enabled
- Theme 3: `RenderEffect.custom()` fully wired; SSIM gated tests pass; xfade `offset=` emitted correctly for all transitions
- Total: 7 PRs merged, all AC items supported or verified

### Carry-Forwards

| Item | Description | Status |
|------|-------------|--------|
| BL-478-AC-1/2, BL-479-AC-1 | Deesser / multiband / volume automation gated tests | Discharge on `STOAT_TEST_FFMPEG=1` CI green run (carried from v097) |

### User Actions Required

None required.

## v097 — Test-truth keystone + FFmpeg-8 builder regression fixes

**Delivered:** 2026-07-06
**PRs:** #737, #738, #739, #741, #742 (+ 3 direct commits to main)
**Tests:** 3591 passing (baseline 3589, +2)

### Highlights

- Fixed 5 FFmpeg-8 Rust builder regressions: deesser `m=`, pan `aeval` accessors, `freezeframes` → `tpad`, `aevalsrc expr` → `exprs`, `arubberband` → `rubberband` — BL-605
- Opacity Python preview path rewritten from `colorchannelmixer` to `geq` + `{expr_T}` — BL-502
- `STOAT_TEST_FFMPEG=1` enabled on all 9 CI matrix variants; ~159 dormant gated assertions now active — BL-607
- Vacuous/broken gated tests fixed or removed (extractplanes alpha, URL underscore, `cmd.args()`) — BL-606
- DoD policy document added: MUST-language coverage requirements for new effect types — BL-503
- Per-effect gated coverage guard test (`test_effect_gated_coverage.py`) blocks regressions at merge — BL-503
- BL-506 fully discharged: SSIM tokens confirmed, `tempfile.mkdtemp` confirmed, step-7 forward-pointer added — BL-506
- `spatial.rs` comma escaping bug found and fixed during CI lane activation — BL-607-AC-3
- BL-478-AC-1/2 and BL-479-AC-1 pending_ci: discharge on first `STOAT_TEST_FFMPEG=1` CI green run

### Theme Summary

| Theme | BL Items | PRs | Status |
|-------|----------|-----|--------|
| ffmpeg-8-builder-correctness | BL-605, BL-502, BL-479 | #737, #738 | merged |
| test-infrastructure-ci-gate | BL-606, BL-607, BL-503, BL-506, BL-478 | #739, #741, #742 + 3 direct commits | merged |

### AC Status

- Theme 1: 11 supported, 4 unverifiable, 5 deferred_post_merge (FFmpeg-gated)
- Theme 2: 13 fully met, 1 partial (BL-607-AC-2 — CI ran on main push not PR), 2 deferred (BL-606-AC-2 blocked by BL-555), 3 pending_ci (BL-478-AC-1/2, BL-479-AC-1)
- Total: all 6 features complete; BL-606-AC-2 deferred due to BL-555 (RenderEffect.custom() not exposed)

### Carry-Forwards

| Item | Description | Status |
|------|-------------|--------|
| BL-606-AC-2 | boxblur gated assertion | Deferred — blocked by BL-555 (RenderEffect.custom() not yet in Rust translator) |
| BL-502-AC-2/3, BL-479-AC-1 | Alpha-changes-over-time opacity; volume automation FFmpeg | Deferred — require FFmpeg 8.x + BL-606-G1 extractplanes fix |
| BL-478-AC-1/2, BL-479-AC-1 | Deesser / multiband / volume automation gated tests | Pending CI discharge on first `STOAT_TEST_FFMPEG=1` green run |

### User Actions Required

None required. Pending_ci items (BL-478-AC-1/2, BL-479-AC-1) discharge automatically on next CI run.

## v096 — Post-v095 Hygiene

**Delivered:** 2026-07-04
**PRs:** #731–#736 (6 PRs)

### Highlights

- Documentation and tooling cleanup after v095 hygiene bundle
- 10/10 ACs completed; 0 regressions

## v095 — Post-R3 Hygiene Bundle

**Delivered:** 2026-07-03
**PRs:** #720–#730 (11 PRs)
**Tests:** 3587 passing

### Highlights

- Post-Release-3 hygiene: linting, mypy, test cleanup, CI reliability
- Build Docker Image CI fixed (first clean run after R3 wave)
- 39/39 ACs met; 0 regressions

## v094 — Subtitle Filter Remediation

**Delivered:** 2026-07-03
**PRs:** #716–#718 (3 PRs)

### Highlights

- Long filtergraph routed to temp file on Windows to avoid argv limit — BL-584
- Font file path escaped via `emit_filter_option_path` in SubtitleScriptBuilder — BL-585
- Single-quote rejection and key validation added to BurnedSubtitleBuilder — BL-586
- 17/18 ACs met; BL-586-AC-6 FFmpeg-gated deferred

## v093 — Render Correctness + API Coverage + Hygiene

**Delivered:** 2026-07-02
**PRs:** #701–#715 (15 PRs)

### Highlights

- Soft subtitle `-map :s` emitted correctly in all render paths — BL-583
- Asset existence and kind validated on image-clip creation — BL-574
- TTS `audio_path` field added to API spec, architecture docs, and GUI client — BL-587
- SQLite FK coverage for DuckingPair; API test coverage for multi-track audio — BL-581, BL-588, BL-589
- `RenderEffect.custom()` Rust translator wired — BL-555 (Theme 04)
- 4 themes, 13 features delivered

## v092 — Release 3, Wave 7 — TTS Riders

**Delivered:** 2026-07-01
**PRs:** #694–#700 (7 PRs)

### Highlights

- BurnedSubtitleBuilder: SRT/ASS sidecar burn-in support — BL-519
- TTS audio mixing hardened: zero-track guard, duplicate stream_idx protection, start_s bounds checking — BL-582
- Source audio amixed with TTS label when source video has audio — BL-578
- 29/35 ACs supported; 6 FFmpeg-gated deferred

## v091 — Multi-Track Audio Mixer + TTS Narration

**Delivered:** 2026-06-29
**PRs:** #689–#692 (4 PRs)
**Tests:** 3456 passing

### Highlights

- Multi-track audio mixer: independent track volumes, ducking pairs, SQLite-backed DuckingPair storage, amix integration — BL-516
- TTS narration: text-to-speech cue rendering into render graph via TtsCue data structure — BL-517
- 16/18 ACs supported; 2 deferred (quiet-window test BL-517-AC-8, speech energy placement BL-516-AC-4)

## v090 — Asset Library + Image Clips + Generic Procedural Parser + Builder Validation Hardening

**Delivered:** 2026-06-28
**PRs:** #680–#686 (7 PRs)
**Tests:** 3403 passing

### Highlights

- Asset library with SQLite-backed storage, CRUD endpoints, and kind-based retrieval — BL-511
- Image clip type: static image assets rendered as video frames in render worker — BL-511
- Generator clip type: procedural generator clips routed through render worker — BL-511
- Generic procedural clip parser for declarative effect configuration — BL-515
- Builder validation hardening across effect builders — BL-569, BL-570
- 60/65 ACs met; 5 deferred (scope/FFmpeg-gated)

## v089 — R3 Wave 3a + Wave 4: FFmpeg Filter Builders & Procedural Shape Generators

**Delivered:** 2026-06-27
**PRs:** #671–#679 (9 PRs)

### Highlights

- FFmpeg filter builder additions for R3 wave shapes and procedural generators
- ZoompanBuilder and additional motion effect builders
- 25/30 ACs supported; 5 deferred (FFmpeg-gated)

## v088 — Release 3, Wave 2

**Delivered:** 2026-06-26
**PRs:** #662–#669 (8 PRs)

### Highlights

- Release 3 Wave 2 feature delivery
- 29/33 ACs supported; 4 deferred (FFmpeg/UAT-gated)

## v087 — Release 3, Waves 0–1

**Delivered:** 2026-06-26
**PRs:** #650–#661 (12 PRs)

### Highlights

- Release 3 Wave 0 and Wave 1 feature delivery
- 10/39 ACs fully verified; remainder FFmpeg/UAT-gated

## v086 — Post-v085 Compliance Riders

**Delivered:** 2026-06-25
**PRs:** #648–#649 (2 PRs)

### Highlights

- Post-v085 compliance and test hygiene riders
- 22/22 ACs completed; 0 regressions

## v085 — Post-v084 Compliance Riders

**Delivered:** 2026-06-24
**PRs:** #642–#646 (5 PRs)

### Highlights

- Post-v084 compliance riders and test corrections
- 18/18 ACs completed; 0 regressions

## v084 — Post-v083 Compliance Hygiene Wave

**Delivered:** 2026-06-24
**PRs:** #630–#641 (12 PRs)

### Highlights

- Compliance and hygiene fixes after AGPL relicense
- 45/47 ACs supported; 2 deferred (headless UAT); 0 regressions

## v083 — AGPL Relicense + Repo Hygiene

**Delivered:** 2026-06-23
**PRs:** #616–#629 (14 PRs)

### Highlights

- Project relicensed under GNU Affero General Public License (AGPL)
- Repository hygiene and compliance cleanup
- 71/76 ACs supported; 0 regressions

## v082 — Release 2, Wave 5 Carry-Forward

**Delivered:** 2026-06-13
**PRs:** #608–#614 (7 PRs)
**Tests:** 3275 passing (baseline 3199, +76)

### Highlights

- FFmpeg path fix: backslash→forward-slash in color_lut filter — BL-499
- FFmpeg dblur fix: radius used instead of sigma for directional blur — BL-500
- Removed invalid cellauto `d=` option from NoiseGeneratorBuilder — BL-501
- Escaped commas in automation expressions for FFmpeg filter-graph parser — BL-502
- ChromaticAberrationBuilder added via `rgbashift` filter (34th effect in registry) — BL-453-AC-2
- chromatic_aberration added to smoke test parametrize
- Smoke-test-harness guide updated with chromatic_aberration row and cellauto fix note
- FFmpeg contract discharge: blur/sharpen PASS, generators PASS, lens distort PASS, keying/blend partial, color-lut partial (path colon escaping carry-forward)
- UAT discharge: journeys 701/702/704/705/706 PASS, journey 703 blocked by BL-480

### Theme Summary

| Theme | BL Items | PRs | Status |
|-------|----------|-----|--------|
| ffmpeg-correctness-hotfixes | BL-499, BL-500, BL-501, BL-502 | #608–#611 | merged |
| chromatic-aberration | BL-453-AC-2 | #612–#614 | merged |

### AC Status

- All 7 PRs merged to main
- FFmpeg contract verification complete for blur/sharpen, generators, lens distort
- UAT journeys 701/702/704/705/706 discharged
- 2 ACs carry-forward (see below)

### Carry-Forwards

| Item | Description | Status |
|------|-------------|--------|
| BL-457-AC-3 | J703 QC-fail journey | Blocked by BL-480 (qc-status-fail/remaster-btn testids absent from GUI) |
| color-lut path colon escaping | FFmpeg color_lut filter with colon in path | Partial — forward-slash fix merged; colon escaping still needed |

## v080 — Release 2, Wave 4 — Editing & Time

**Delivered:** 2026-06-12
**PRs:** #580–#591 (11 PRs)
**Tests:** 6967+ passing (baseline at start of v080)

### Highlights

- Reverse effect with 30s buffer-limit guard via STOAT_REVERSE_MAX_DURATION_S env var — BL-444
- Range-window gating effect for time-domain window operations — BL-446
- Variable-speed effect with segmented-concat rendering — BL-447
- Framerate-convert effect with blend, optical-flow, and duplicate modes — BL-448
- Freeze-frame effect for static frame extraction — BL-449
- Clip split/razor endpoint with timeline propagation and GUI affordance — BL-445
- j_reverse_split.py rewritten with real reverse+split API assertions; Tier-2 UAT checklist created — BL-457
- Golden QC fixture regenerated with real FFmpeg measurements; BL-476 confirmed resolved — BL-458
- Tier-2 acceptance harness and gate tests created; BL-476/477 confirmed passing — BL-459
- Smoke tests for reverse, variable_speed, framerate_convert, freeze_frame, and split operations
- Smoke-test-harness guide updated with v080 effect types, split endpoint, and STOAT_REVERSE_MAX_DURATION_S

### Theme Summary

| Theme | BL Items | PRs | Status |
|-------|----------|-----|--------|
| effect-engine-core | BL-444, BL-446, BL-447, BL-448, BL-449 | #580–#584 | merged |
| clip-operations-and-docs | BL-445 | #585–#587 | merged |
| wave-t-testing-harness | BL-457, BL-458, BL-459 | #588–#591 | merged |

### AC Status

- All 11 features merged to main
- 5 ACs deferred (require `STOAT_TEST_FFMPEG=1` or headed browser)
- 1 AC blocked by BL-480 (GUI testids absent)
- All deferred ACs have discharge commands below

### Discharge Commands

| Item | Description | Discharge |
|------|-------------|-----------|
| BL-457-AC-2 (FR-002-AC-2) | j_reverse_split.py headless UAT run | `python scripts/uat_runner.py --journey 705 --headless` (requires live server) |
| BL-457-AC-3 (FR-003-AC-1) | J-QC-Fail journey | Blocked by BL-480 (qc-status-fail/remaster-btn testids absent from GUI) |
| BL-459-AC-1/2/4 | Full acceptance harness (FFmpeg-gated) | `STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/uc_media_mps_001_harness.py -v` |

### User Actions Required

1. **BL-457-AC-2** — Run `python scripts/uat_runner.py --journey 705 --headless` to discharge j_reverse_split.py UAT (requires live server)
2. **BL-459-AC-1/2/4** — Run `STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/uc_media_mps_001_harness.py -v` to discharge full acceptance harness (FFmpeg-gated)

## v078 — QC Integrity, DSP Correctness & R2 Doc Parity

**Delivered:** 2026-06-11
**PRs:** #550–#562 (13 PRs)
**Tests:** 2852+ passing (smoke tests added in Theme 04)

### Highlights

- QC loudness measurement corrected: ebur128 replaced by loudnorm print_format=json — BL-476
- QCService wired into worker-path renders via RenderService._complete_job() — BL-477
- Deesser frequency normalized Hz→[0,1]; multiband compressor threshold normalized dB→linear — BL-478
- Volume automation eval=frame; effects-preview-automation endpoint wired; preview validation fixed — BL-479/BL-482
- automatable_parameters field added to EffectResponse — BL-481
- librosa added to test extras; pitch stability test unconditionally enabled — BL-435 rider
- Smoke tests for automatable_parameters, worker-path QC, and preview automation — Theme 04
- R2 doc parity: C4 routers updated (9→17 effects, 14 locations), 8 new DSP effects documented — BL-469/BL-483
- QC endpoints documented in api-reference and operator-guide — BL-484
- delivery_profiles CRUD documented; name-vs-UUID distinction explicit — BL-485
- QC-fail GUI surfaces on RenderJobCard; uat_runner and screenshot path fixes — BL-480

### Theme Summary

| Theme | BL Items | PRs | Status |
|-------|----------|-----|--------|
| qc-integrity | BL-476, BL-477 | #550, #551 | merged |
| dsp-correctness | BL-478, BL-479, BL-435 rider | #552, #553, #554 | merged |
| automation-api-ergonomics | BL-481, BL-482 | #553, #555 | merged |
| qa-infrastructure | smoke tests, harness guide | #556, #557 | merged |
| r2-doc-parity | BL-469, BL-483, BL-484, BL-485, BL-480 | #558–#562 | merged |

### AC Status

- All 13 features merged to main
- 5 ACs deferred_post_merge (require `STOAT_TEST_FFMPEG=1` or headed browser)
- All deferred ACs have discharge commands below

### Discharge Commands

| Item | Description | Discharge |
|------|-------------|-----------|
| BL-476-AC-4 | Golden QC fixture | `STOAT_TEST_FFMPEG=1 uv run pytest tests/qc/ -v` |
| BL-477-AC-3 | Worker-path QC acceptance | `STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/ -v` |
| BL-478-AC-1/2 | Deesser + multiband FFmpeg | `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/ -v` |
| BL-479-AC-1 | Volume automation FFmpeg | `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/ -v` |
| BL-480-AC-1 | J703/J704 UAT headed | `python scripts/uat_runner.py --journey 703` and `--journey 704` (headed Chromium, Windows) |

### User Actions Required

1. **BL-476-AC-4** — Run `STOAT_TEST_FFMPEG=1 uv run pytest tests/qc/ -v` to discharge golden QC fixture against real FFmpeg output
2. **BL-477-AC-3** — Run `STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/ -v` to discharge worker-path QC acceptance harness with real FFmpeg
3. **BL-478-AC-1/2** — Run `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/ -v` to discharge deesser (Hz→[0,1]) and multiband (dB→linear) normalization
4. **BL-479-AC-1** — Run `STOAT_TEST_FFMPEG=1 uv run pytest tests/effects/ -v` to discharge volume automation frame-eval correctness
5. **BL-480-AC-1** — Run `python scripts/uat_runner.py --journey 703` and `--journey 704` on Windows with headed Chromium (J703/J704 UAT pass)

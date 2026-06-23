# Release 3 — Traceability Matrix

**Audience:** auditor, reviewer, anyone asking "what proves this is real?"
**Purpose:** every requirement → use case → BL → PoC evidence → test.

## Master traceability table

| Requirement | Use case | BL | PoC evidence (gw-test path) | Test (after BL implementation) |
|---|---|---|---|---|
| C1 multi-clip timeline | UC1 + UC2 | BL-505 | `poc-0-render-graph/` (SSIM 0.999999 vs source) | integration test: multi-clip duration + SSIM clip attribution |
| C2 per-clip effects + windows | UC1 + UC2 | BL-505 + BL-512 | `poc-0-render-graph/` (blur within window 1-3) | integration test: effect application + window dispatch (T-capable + non-T fallback) |
| C3 transitions (xfade) | UC2 | BL-505 | `verification-1-zoompan-xfade/` (xfade duration math) | integration test: 3-clip with 2 xfades |
| C4 image-as-clip | UC1 + UC2 | BL-511 (depends BL-515 + BL-502) | composition through yuv420p verified in `poc-bl502-geq-redesign/` | integration test: image clip with opacity fade renders visibly |
| A1 asset library | UC1 + UC2 | BL-515 | (no direct PoC; standard CRUD) | integration test: upload+list+download+dedup+traversal |
| A2 procedural shapes | UC1 + UC2 | BL-513 | `poc-5-rust-image-spike/` (all 4 shapes, 2.5-7.7 ms at 720×720) | contract test: hash of decoded-RGBA pixel buffer matches pinned reference |
| A3 generic procedural | optional both | BL-514 | `poc-1-parser-langfit/bespoke-spike/` (352 lines, 0.42 µs/eval, safety bounds engage) | unit test: parser grammar + safety + render time budget |
| AU1 multi-track audio | UC1 + UC2 | BL-517 | `poc-3-multi-track-audio/retest-stereo/` + `poc-bl517-cleaner-fixture/` (stereo preserved + 9.68 dB measured attenuation) | integration test: 3-track render + per-track-presence spectrogram probe |
| AU2 sidechain ducking | UC1 + UC2 | BL-517 | `poc-bl517-cleaner-fixture/parameter-sweep-aggressive.csv` (9 parameter combos, ≥ 6 dB at default) | integration test: with-ducking vs no-ducking music-band attenuation in voice window |
| AU3 TTS narration (Piper local) | UC1 + UC2 | BL-516 | `poc-2-tts/piper-en_US-lessac-medium.wav` (3.32 s latency for 11 s of speech, 22 kHz mono WAV) | integration test: Piper synthesis end-to-end |
| AU3 TTS narration (Kokoro cloud) | UC1 + UC2 (optional) | BL-516 | `poc-2-tts/kokoro-af_bella.mp3` (24 kHz mono MP3, 146 s cold start for 14 s of speech) | integration test: Kokoro synthesis via OpenRouter (skipped if no key) |
| S1 burned subtitles | UC2 + UC1 optional | BL-519 | `verification-2-libass/libass-smoke.mp4` (libass present, smoke render works) | integration test: SRT burn + OCR/pixel-diff at midpoint |
| S2 soft subtitles | UC1 + UC2 | BL-520 | (no direct PoC; standard mov_text mux) | integration test: ffprobe asserts 2 subtitle streams with correct language metadata |
| S3 subtitle script helper | UC1 + UC2 | BL-518 | (uses drawtext primitives which are well-known) | integration test: 3-entry script renders captions at right timestamps |
| E1 zoompan | UC2 | BL-507 | `verification-1-zoompan-xfade/` (mandatory fps,settb pin) | contract test: zoompan emits both fps and settb; negative control fails |
| E2 curves | UC2 | BL-508 | (single-filter wrap, no PoC) | contract test: preset render differs from original |
| E3 vignette | UC2 | BL-509 | (single-filter wrap, no PoC) | contract test: corner darkening measurable |
| E4 hue rotation | UC2 | BL-510 | `poc-4-escape-policy/` (single-quote-wrap protects commas for hue) | contract test: comma-bearing hue expression renders without escape |
| T1 render preflight | trust scenario | BL-505A | `poc-obs-render-command/recommendation.md` (gap identification) | integration test: unrepresentable project returns 422 |
| T2 render evidence | trust scenario | BL-506-tech | `poc-obs-render-command/recommendation.md` (no API surface today) | integration test: evidence fields populated on every render |
| T3a BL-499 carry-forward | UC1 + UC2 | BL-499 | `poc-bl499-path-escape/escape-policy-matrix.csv` (5-variant × 4-filter matrix verified) | contract test: Windows-absolute LUT renders via emit_filter_option_path |
| T3b BL-502 carry-forward | UC1 + UC2 | BL-502 | `poc-bl502-geq-redesign/` (three proofs: parse + alpha changes + composition survival) | contract test: animated opacity visible after composition through yuv420p |

## PoC evidence index

All PoC artefacts live at `<gw-test>/snf-showcase-20260614/gaps-identified/poc-work/`. (gw-test is outside this repo; the path is documented for audit.)

| PoC | Location | Key finding |
|---|---|---|
| PoC-0 render graph | `poc-0-render-graph/` | Multi-input filter_complex emits from JSON fixture; SSIM 0.999999 |
| PoC-1 parser language-fit | `poc-1-parser-langfit/` | Only evalexpr (AGPL-3.0) passes language-fit; bespoke spike validates 352-line alternative |
| PoC-2 TTS (Kokoro) | `poc-2-tts/kokoro-af_bella.mp3` | Cloud TTS via OpenRouter works without privacy switch |
| PoC-2 TTS (Piper) | `poc-2-tts/piper-en_US-lessac-medium.wav` | Local TTS 50× faster than cloud cold start |
| PoC-3 multi-track audio | `poc-3-multi-track-audio/retest-stereo/` + `poc-bl517-cleaner-fixture/` | Stereo preserved + 9.68 dB ducking attenuation at default params |
| PoC-4 escape policy | `poc-4-escape-policy/` | Single-quote-wrap policy per-filter; not universal |
| PoC-5 procedural shapes | `poc-5-rust-image-spike/` | All 4 shapes in 2.5-7.7 ms at 720×720 |
| PoC-Obs render command | `poc-obs-render-command/recommendation.md` | No API surface today for actual render command |
| PoC-bl499 path matrix | `poc-bl499-path-escape/` | 5-variant × 4-filter matrix; policy = single-quoted + colon-escaped |
| PoC-bl502 geq redesign | `poc-bl502-geq-redesign/` | Three proofs: parse + alpha changes + composition survival |
| PoC-bl517 cleaner fixture | `poc-bl517-cleaner-fixture/` | Parameter sweep across threshold/ratio; default ≥ 6 dB attenuation |
| Verification-1 zoompan timebase | `verification-1-zoompan-xfade/` | Mandatory fps,settb pin |
| Verification-2 libass | `verification-2-libass/` | libass present in bundled FFmpeg |

## Codex review chain

The design package is the output of an extended review chain. For audit:

| # | Doc | Subject |
|---|---|---|
| 01 | `01-codex-review-1.md` | Original 22-item gap list review |
| 02 | `02-review-1-response.md` | Verified responses to codex 01 |
| 03 | `03-codex-review-1-followup.md` | STATUS.md hygiene followup |
| 04 | `04-review-1-followup-response.md` | Acknowledged + folded |
| 05 | `05-poc-review-codex-1.md` | Codex review of poc-results |
| 05 | `05-poc-review-opus-1.md` | Self-review of poc-results |
| 06 | `06-post-poc-action-plan.md` | First post-PoC plan |
| 07 | `07-codex-review-1.md` | Codex review of 06 |
| 08 | `08-post-poc-action-plan-2.md` | Revised plan with two-track separation |
| 09 | `09-action-plan-2-execution-results.md` | Track A + B execution + BL-502 discovery |
| 10 | `10-codex-response.md` | Codex review; BL-499 escape variants verified |
| 11 | `11-autonomous-derisking-plan.md` | Loop-driven plan; OpenRouter TTS verified |
| 12 | `12-codex-review.md` | Codex review of 11 |
| 13 | `13-response-to-codex-review-12.md` | Final OpenRouter TTS verification |
| 14 | `14-bl-codex-review.md` | Codex review of 18-draft BL set |
| 15 | `15-review-response.md` | Verified zoompan no-T + 18 drafts + 21-item punchlist execution |
| 16 | `16-codex-response.md` | Codex review of 15; 3 residual fixes (BL-515 config docs, BL-519 VTT cleanup, BL-520 escape AC) |
| 17 | `17-release-3-design.md` | This package's creation prompt + summary (under gaps-identified, not the repo) |

All 17 prior docs live at `<gw-test>/snf-showcase-20260614/gaps-identified/`. The repo-side authoritative documentation is this `docs/design/03-release-03/` folder.

## Use-case-to-BL roll-up

### UC1 Maya (hypnotherapy)

Required BLs (in dependency order):
- BL-499, BL-502 (Wave 0)
- BL-505A, BL-505B, BL-505C, BL-506-tech (Waves 1+2)
- BL-512 (Wave 4)
- BL-515, BL-511 (Wave 3b)
- BL-513 (Wave 3a — Spiral + ConcentricRings)
- BL-517 (Wave 5)
- BL-516 (Wave 6)
- BL-518 (Wave 7)
- BL-520 (Wave 7 for accessibility soft subs)

Optional: BL-519 (burned subs for non-accessibility distribution), BL-510 (hue rotation for mood shifts).

### UC2 Devon (educational explainer)

Required BLs:
- BL-499, BL-502 (Wave 0)
- BL-505A, BL-505B, BL-505C, BL-506-tech
- BL-512
- BL-515, BL-511
- BL-513 (RadialBurst)
- BL-517, BL-516
- BL-518
- BL-519 (short-form burned subs)
- BL-520 (YouTube soft subs)
- BL-507, BL-508, BL-509, BL-510 (all four wishlist builders)

Optional: BL-514 (generic procedural — only if specific shapes don't suffice).

### Cross-cutting trust scenarios

Required: BL-505A, BL-506-tech.

All other BLs benefit indirectly (their renders surface evidence too).

## Test-to-BL mapping (test author guide)

| Test type | New tests added by Release 3 | BL |
|---|---|---|
| Rust unit | Parser, path escape helper, expression escape helper, translator | BL-514, BL-499, Wave V, BL-505B |
| Python schema | Asset, audio track, ducking pair, soft subtitle, TTS effect | BL-515, BL-517, BL-520, BL-516 |
| Contract (FFmpeg subprocess) | Each new builder × at least one positive + one negative | BL-507/508/509/510/513/514/518/519, BL-510 single-quote, BL-499 path matrix |
| Integration | Multi-clip SSIM, asset upload+render, multi-track ducking attenuation, TTS synthesis, subtitle presence, render evidence end-to-end | BL-505, BL-515, BL-517, BL-516, BL-519/520, BL-506-tech |
| Chatbot scenario | UC1 + UC2 + trust scenario | all |
| UAT (Playwright) | Asset library page, voice picker, multi-track inspector, evidence inspector | all GUI-touching BLs |
| Hygiene | Registry vs ffmpeg -filters, undocumented settings, config doc sync, two-registry drift | Cross-cutting |
| Smoke harness rows | One per new effect type + clip type | all builders + BL-511 |

## How to verify the package itself

Anyone reviewing this design can sanity-check:

- `ffmpeg -filters | grep zoompan` returns `.. zoompan` (no T) — confirms the corrected T-flag table.
- `ls <gw-test>/snf-showcase-20260614/gaps-identified/poc-work/draft-bl-items/ | wc -l` returns 18 — confirms the BL count.
- `head <gw-test>/snf-showcase-20260614/gaps-identified/poc-work/poc-0-render-graph/run.log` shows the SSIM measurements — confirms PoC-0.
- `ffprobe poc-work/poc-2-tts/piper-en_US-lessac-medium.wav` shows 22050 Hz mono — confirms Piper format.

The package is meant to be auditable, not trusted.

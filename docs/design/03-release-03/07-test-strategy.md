# Release 3 — Test Strategy

**Audience:** test author, harness maintainer, auto-dev orchestrator.
**Principle:** every requirement is verifiable. No "looks fine" acceptance.

## Test layer summary

| Layer | What it verifies | When it runs | Target failure rate |
|---|---|---|---|
| Unit (Rust + Python) | Functions, builders, schema validation, escape helpers, expression parser | Every commit | 0 |
| Integration (Python + FFmpeg) | API → render-graph translator → FFmpeg subprocess → output | Every PR | 0 |
| Contract (Rust unit + FFmpeg subprocess) | Each builder's emitted filter actually renders | Every PR + nightly | 0 |
| Hygiene (CI guard) | Registry vs `ffmpeg -filters`, undocumented settings vars, config doc sync | Every PR | 0 |
| Chatbot-driven (LLM + harness) | API-callable scenarios end-to-end with evidence assertions | Every release candidate | low (defects, not flakes) |
| UAT (Playwright headed) | GUI flows for the two use cases + cross-cutting trust | Pre-release | low |
| Smoke harness | Every effect + clip type renders without error | Nightly | 0 |
| QC pass (Release 2 carry-over) | Loudness, true-peak, A/V sync, decode integrity | Per render | 0 (gate) |

## Unit tests

### Rust core

- **Expression parser (BL-514).** Parse + eval coverage for all built-ins. Pathological-input tests (depth limit, step budget, pow clamp). Property tests via `proptest` for grammar round-trip.
- **Path escape helper (`emit_filter_option_path`, BL-499).** Five-variant × 4-filter matrix from `poc-bl499-path-escape/` (NOT PoC-2 which is TTS; per codex `18` smaller correction 1). Apostrophe-in-path rejection. Forward-vs-backslash handling. Unix-path passthrough.
- **Expression escape helper (`emit_expression`, Wave V).** Single-quote wrapping. Embedded single-quote rejection.
- **Render-graph translator (BL-505B).** Per-clip sub-chain construction. Window dispatch (T-capable vs non-T). fps,settb pin emission. Argv vs filter-option path distinction.
- **EffectDefinition metadata cross-check.** Every builder declares timeline_T_capable consistent with its emitted filter.

### Python API + schemas

- **Render preflight (BL-505A).** Every capability gate has a test that submits an unrepresentable project and asserts the right 422.
- **Render evidence schema.** Every field present and correct type. Redaction policy: full evidence omitted when caller lacks admin role.
- **Asset library validation (BL-515).** Content-sniff mismatch, MIME allow-list, size limit, path traversal probes (`../`, absolute, symlink), tags + filter pagination.
- **Multi-track audio schema (BL-517).** Track-id uniqueness, weight ranges, ducking-pair references. (BCP-47 validation belongs to BL-520 soft subtitles, not multi-track audio — per codex `18` smaller correction 2.)
- **Soft subtitle language schema (BL-520).** BCP-47 validation; ISO-639-2/B output mapping; reject unknown tags with clear error.
- **TTS effect schema (BL-516).** Backend enum, voice catalogue validation per backend.
- **Soft subtitle schema (BL-520).** BCP-47 → ISO-639-2/B mapping; reject unknown tags with clear error.

## Integration tests

These run actual FFmpeg subprocesses against generated lavfi inputs (no real video assets needed; tests are deterministic and CI-friendly).

### Render path

- **Multi-clip render produces correct duration.** 3 clips × 5 s with 1 s xfades → 13 s output.
- **SSIM clip attribution.** Frame extracted at clip 2's midpoint vs source clip 2 returns SSIM > 0.99. (Pattern: PoC-0 measured 0.999999.)
- **fps,settb pin negative control.** Removing the pin from a zoompan-feeding-xfade graph produces 0-byte output. (Pattern: Verification-1.)
- **format=yuv420p terminal.** ffprobe asserts pix_fmt is yuv420p on every render.
- **Per-clip effect application.** A clip with a blur effect produces output that is measurably blurrier than the source.
- **Windowed effect dispatch.** A hue effect with window [1, 3] produces hue-shifted output at t=2 and original-hue output at t=4.
- **Non-T windowed effect fallback.** A zoompan effect with window [1, 3] uses split/trim/concat and produces the right segmented output (zoom only inside window).

### Render evidence

- **Evidence persisted on success.** Submit job → wait completion → assert `evidence.exit_code=0, command_args` non-empty, `output_size_bytes > 0`.
- **Evidence persisted on failure.** Force a render failure (invalid filter chain) → assert `evidence.exit_code != 0` and `stderr_tail` contains the error.
- **Evidence redaction.** Non-admin caller sees only the public surface; admin sees full evidence.

### Asset library

- **Upload + reference + render.** Upload an image asset → create an image clip referencing it → render → assert the image appears in output at the right timestamp.
- **Dedup by hash.** Same content uploaded twice → second response returns existing asset id (200 not 201).
- **Soft-delete invariant.** Delete an asset referenced by a clip → 409 with referenced-projects list.

### TTS

- **Piper synthesis.** Submit a render with tts_narration effect (backend=piper_local) → assert output WAV has the right duration via ffprobe.
- **Kokoro synthesis.** Same with backend=openrouter_kokoro → assert MP3 output via the existing test harness. Skipped if no API key configured.
- **Cache hit.** Two renders with the same text+voice+backend → second render's evidence shows the cache was used.

### Multi-track audio

- **3-track ducking attenuation.** Music + voice + binaural with default ducking → assert music carrier band loses ≥ 6 dB in voice-burst window, 0 dB in quiet window. Binaural unchanged.
- **Stereo preservation.** Same as above → assert output `channels=2` and L≠R for the binaural component.

### Subtitles

- **SRT burn-in OCR.** Burn a 3-entry SRT → extract frames at each entry's midpoint → assert text presence via OCR or pixel-difference vs no-subtitle control.
- **Soft subtitles in mp4.** Render with 2 soft tracks (en + es) → ffprobe asserts 2 subtitle streams with correct ISO-639 language metadata.
- **force_style escape.** Render SRT with `force_style='Fontsize=32'` → assert exit 0 and visible size change in output.

## Contract tests (per builder)

Every new effect builder ships with at least one contract test that:

1. Constructs the builder with valid params.
2. Calls `.build()` to get the emitted filter string.
3. Renders the filter against a lavfi source via FFmpeg subprocess.
4. Asserts exit 0 + non-zero output size.

Plus a negative control where applicable (e.g. zoompan without fps,settb pin must fail).

## Hygiene tests (CI gates)

These prevent silent regressions:

| Test | What it asserts |
|---|---|
| Registry vs `ffmpeg -filters` | Every builder's `timeline_T_capable` flag matches the filter's actual T flag in the bundled FFmpeg. (Catches the zoompan misclassification class of error.) |
| `subtitles`/`ass` filter presence | bundled FFmpeg has libass; the filters appear in `ffmpeg -filters`. |
| Undocumented settings vars | `KNOWN_UNDOCUMENTED_SETTINGS_VARS` is empty after Release 3. (Catches new `STOAT_*` env vars without doc updates.) |
| Config doc sync | Every `STOAT_*` in `settings.py` appears in BOTH `docs/setup/04_configuration.md` AND `docs/manual/configuration-reference.md`. |
| `escape_for_filter` deprecation | No NEW call-sites of the legacy `escape_for_filter` (migration to `emit_expression`). |
| Two-registry drift | Python AI-hint records match the Rust EffectDefinition registry (PyO3 cross-check). |

## Chatbot-driven verification (release-candidate gate)

Builds on the Release 2 chatbot harness. Release 3 changes the contract: **the harness MUST consume the render evidence API and fail loudly when fields are absent or wrong**.

### Mandatory assertions per render

Every chatbot-driven render in the harness now asserts:

```
assert evidence is not None
assert evidence['exit_code'] == 0
assert evidence['output_size_bytes'] > 50_000     # not a 0-byte stub
assert evidence['command_args'][0].endswith(('ffmpeg', 'ffmpeg.exe'))
# For multi-clip renders:
assert SSIM(extracted_frame_at(clip_N_midpoint), source_clip_N) > 0.99
# For renders that should apply specific effects:
assert effect_presence_probe(output, effect_name) == True
```

No silent success. The harness writes an evidence JSON sidecar per round.

### Round scenarios

The harness runs at minimum:

1. **Use Case 1** (Maya hypnotherapy) end-to-end.
2. **Use Case 2** (Devon explainer) end-to-end — both renders (soft and burned subtitle variants).
3. **Trust scenario** — submit a multi-clip project; assert preflight + evidence; intentionally submit an unrepresentable project; assert 422.

Each scenario produces a `evidence/round-N/` directory with:
- `evidence.json` (the API response)
- `output.mp4` (the render)
- `ffprobe.json` (stream summary)
- `frame-t*.png` (extracted frames at the midpoints)
- `ssim-matrix.json` (per-clip SSIM)
- `stderr.txt` (FFmpeg stderr from the evidence)

## UAT (Playwright headed)

New scenarios — see `06-gui-integration.md` Section "Test coverage" — plus a regression matrix:

- Every existing Release 1 + 2 UAT scenario still passes.
- Windows player compatibility check: outputs play in Windows Media Player (the original silent-yuv420p mistake regression).

UAT runs on the dev workstation against a real Windows-native FFmpeg.

## Smoke harness (nightly)

The smoke harness (`docs/manual/smoke-test-harness.md`) gains a row for each:

- New effect builder (zoompan, curves, vignette, hue_rotation, procedural_shape, procedural_image, subtitle_script, burned_subtitle, tts_narration).
- New clip type (image).
- New audio architecture (multi-track + ducking).
- New output feature (soft subtitles).

Each row: param dict → expected filter substring → exit 0 → output size > threshold.

## QC pass (carry-over from Release 2)

The Release 2 QC pass continues to gate every render. Release 3 doesn't change its contract:

- Loudness compliant (per delivery profile).
- True-peak under limit.
- No clipping.
- No A/V sync drift.
- Decode integrity.
- Embedded metadata correct.

Release 3's multi-track + TTS outputs feed into the same QC pass.

## Test data assets

A new `tests/assets/release_3/` directory ships test inputs:

- `red-5s.mp4`, `blue-5s.mp4`, `green-5s.mp4` — testsrc colors for multi-clip verification.
- `test-subtitle.srt`, `test-subtitle.ass` — minimal subtitle sidecars.
- `test-spiral.png`, `test-logo.png` — image-clip assets.
- `test-music-200hz.wav`, `test-voice-burst.wav`, `test-binaural-440-448.wav` — synthesised audio for ducking tests (matches T3 fixture spec).

All assets are CI-checked-in (small) or generated at test setup time via lavfi.

## Coverage gates

A Release 3 PR must:

- Add at least one unit test for every new function it introduces.
- Add at least one integration test for every new API surface.
- Add at least one contract test for every new builder.
- Update the chatbot harness if the change affects an existing scenario.
- Pass all hygiene gates.
- **Pass OpenAPI freshness checks** (per codex `18` Major Risk): if Pydantic models or FastAPI routes changed, the PR includes both regenerated `gui/openapi.json` (via `uv run python -m scripts.export_openapi`) AND regenerated `gui/src/generated/api-types.ts` (via `cd gui && npm run generate:types`). CI's existing freshness checks fail the PR otherwise.
- **Pass PyO3/stub workflow** (per codex `18` Major Risk): if the PR adds a Rust API surface used from Python (new PyO3-visible function or class), the PR also:
  - Adds PyO3 bindings in the same feature.
  - Regenerates the stub via `cargo run --bin stub_gen`.
  - **Does NOT copy generated stubs wholesale into `src/stoat_ferret_core/_core.pyi`** — manual stubs are append-only; never overwritten with the generated output (per the operational memory rule documented in the project).
  - Runs `uv run python scripts/verify_stubs.py` and that passes.

These two cross-cutting rules apply to every BL that touches schemas/routes (most of Release 3) and every BL that touches Rust/PyO3 (BL-505B translator, BL-514 parser binding, BL-513 shape generators if PyO3-exposed, BL-502 geq emit if exposed). They are explicitly added as ACs in each affected BL draft (see `backlog/`).

No exceptions. The auto-dev process enforces this in the version-execution phase.

## What's deliberately NOT tested

- Performance under load (no soak tests in Release 3; defer to later).
- Long-form (>30 min) renders (CI time budget; covered by manual UAT on the dev workstation).
- Edge cases of obscure FFmpeg filter combinations not used by the BL set.
- Pixel-perfect cross-platform reproducibility (FFmpeg + libass may differ by build; tests assert structural properties, not byte-exact frames).

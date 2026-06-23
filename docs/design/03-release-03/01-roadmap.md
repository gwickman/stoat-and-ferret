# Release 3 — Roadmap

**Project:** stoat-and-ferret — AI-driven video editor (hybrid Python/Rust)
**Release goal:** From "produces and proves a finished master" to "**lets a user compose a multi-clip creative project with custom assets, narrated audio, animated effects and accessible subtitles**" — with truthful render evidence at every stage so the chatbot harness can verify outputs, not just trust API success.

> **Release 3 is a multi-version release program, not a single auto-dev version.** It spans six versions (v083-v088). Each wave below is approved + executed independently. Do not treat Release 3 as one version theme.

## Executive summary

Release 3 closes the silent-success gap in the render path and adds the capability surface the wellness/educational/explainer use cases need: multi-clip render, per-clip effects with timed windows, image-as-clip and user-asset library, procedural shape and equation-driven image generation, voice narration (Piper local + OpenRouter Kokoro cloud), multi-track audio mixing with sidechain ducking and per-track volume automation, burned-in subtitles, soft subtitles in mp4 containers, and the small wishlist of single-filter effect wraps (curves, vignette, hue rotation, zoompan).

The release is organised into capability waves with a clear dependency spine. Like Release 2, testing is cross-cutting and not a separate closing phase — chatbot-driven verification + render-evidence-artefact assertions + UAT scenarios are first-class deliverables for every wave.

## Dependency spine

```
Wave 0  Carry-forwards (v082 broken builders)
            │
            ▼
Wave 1  Truth + render evidence (BL-505A, BL-506-tech)
            │
            ▼
Wave 2  Multi-clip render graph (BL-505B, BL-505C)
            │
            ├──> Wave 3a  Builder wishlist (BL-507/508/509/510/513)
            │
            ├──> Wave 3b  Asset library + image-as-clip (BL-515 → BL-511)
            │
            ├──> Wave 4   Time-window dispatch (BL-512 reframed)
            │
            ├──> Wave 5   Audio architecture (BL-517 multi-track) ──> Wave 6 TTS (BL-516)
            │
            └──> Wave 7   Subtitles (BL-518 + BL-519 + BL-520)

Cross-cutting:
   Wave V  Value-kind escape policy + path policy (BL-499, EffectBuilderValueEscaping)
   Wave G  Generic procedural (BL-514, bespoke parser)
   Wave T  Test harness updates + verification workflow
   Wave D  Doc updates (smoke harness, manual, configuration reference)
```

**Why this order:**

1. **Wave 0 — carry-forwards FIRST.** BL-499 (Windows path escape policy) and BL-502 (animated opacity via geq) are v082 bugs whose escape fixes shipped but whose runtime/policy was never verified. They block other work because BL-511 references path-bearing assets and BL-512's enable= dispatch relies on the correct timeline-T table that the PoC chain corrected.
2. **Wave 1 — truth-telling SECOND.** BL-505A (render preflight that rejects unrepresentable project state) and BL-506-tech (render evidence artefact API) stop the silent-success failure mode independently of the full render-graph rewrite. They're cheap to ship and immediately make every other wave testable.
3. **Wave 2 — render graph.** The load-bearing wave. Until multi-clip + per-clip effects render, every downstream wave is hypothetical capability.
4. **Waves 3-7 are mostly parallel** once Wave 2 lands. The builders are mechanical wraps; the asset library is standard CRUD; subtitles fan out from BL-515; audio fan-outs from BL-517.

## Capability waves

### Wave 0 — Carry-forwards (v082 fixups, must precede everything else)

- [ ] **BL-499** — codify the path-escape policy across `lut3d`, `subtitles`, `ass`, `movie` (single-quoted + colon-escaped variant verified working). Add `emit_filter_option_path` helper. Apostrophe-in-path rejection AC.
- [ ] **BL-502** — replace the runtime-failing `colorchannelmixer=aa='{expr}':eval=frame` opacity-automation pattern with `geq` using uppercase `T`. Three proofs required: parses, alpha changes over time, alpha survives composition through final `format=yuv420p`.

### Wave 1 — Truth + render evidence (cheap, leverage-heavy)

- [ ] **BL-505A** — render preflight truthfulness. `POST /render` returns 422 or a structured warning when the persisted project state contains things the worker cannot represent (multi-clip, per-clip effects, generator/image clips, multi-audio-tracks). Stops the silent-success mode while the full graph rewrite is being built.
- [ ] **BL-506-tech** (sibling under BL-506) — persist render evidence per job and expose via the job-response API: `command_args`, `exit_code`, `stderr_tail`, `output_size_bytes`, `filter_script_path`, plus a redaction policy for absolute paths.

### Wave 2 — Multi-clip render graph (the gate)

- [ ] **BL-505B** — Rust render-graph translator. Reads project clips + effects + transitions, emits multi-input `filter_complex` with per-clip sub-chains, timeline-window dispatch (T-capable filters use `enable=`; non-T use split/trim/concat), `fps,settb` segment-boundary normalisation, xfade composition, final `format=yuv420p`. Concept acceptance proven by PoC-0 with SSIM 0.999999.
- [ ] **BL-505C** — worker integration. `build_command_for_job` in `src/stoat_ferret/render/worker.py` calls the translator instead of using `clips[0]` + `settings.filter_graph`.
- [ ] **EffectDefinition metadata extension** (no separate BL — part of BL-505B): add `stream_kind`, `arity`, `chain_safe`, `timebase_mutating`, `timeline_T_capable`, `requires_path_escape`, `value_kind_per_option`. Plus a hygiene test cross-checking `timeline_T_capable` against `ffmpeg -filters` output. **Rust registry is authoritative**; Python AI hints derived.

### Wave 3a — Builder wishlist (single-filter wraps, parallel)

- [ ] **BL-507** — ZoompanBuilder. Ken Burns slow-zoom / pan inside a fixed canvas. Emits BOTH `fps=<project_fps>` AND `settb=1/<project_fps>` after zoompan (verified mandatory). Explicit non-overlap with existing scale automation. **zoompan is NOT timeline-T capable**; windowed zoompan uses graph-level split/trim/concat fallback.
- [ ] **BL-508** — CurvesBuilder. Colour-grading preset + per-channel knee strings (typed `KneeString`, not generic expressions).
- [ ] **BL-509** — VignetteBuilder. Cinematic corner darkening with simpler v1 surface (`position: enum + offsets`).
- [ ] **BL-510** — HueRotationBuilder. Hue cycling. Emits `hue=H='<expr>'` with single-quote wrapping (no comma escape needed — verified for hue specifically; not universal).
- [ ] **BL-513** — Procedural shape builders. Spiral, RadialBurst, Checkerboard, ConcentricRings via the Rust `image = "0.25"` crate. All 4 shapes verified at 720×720 in 2.5-7.7 ms.

### Wave 3b — Asset library + image-as-clip

- [ ] **BL-515** — User-asset library. Upload + storage + REST CRUD for images, audio, subtitle, font, lut assets. Content-hash dedup. Security ACs: content-sniff validation, path-traversal hardening, `STOAT_ASSETS_DIR` documented in both setup + manual configuration references, migration idempotency.
- [ ] **BL-511** — Image-as-clip. `clip_type=image` with `source_asset_id` referencing the asset library. Loads via `-loop 1 -i <path>` (subprocess argv — NOT a filter-option path; BL-499 escape does NOT apply here).

### Wave 4 — Time-window dispatch (BL-512 reframed)

- [ ] **BL-512** — Renderer consumption of existing `WindowSpec` (already on `effect.py:109`). Per-builder `timeline_T_capable` flag drives dispatch:
  - T-capable filters: append `:enable='between(t,start_s,end_s)'`.
  - Non-T filters (scale, zoompan, format, fps, settb, subtitles, ass, amix, sidechaincompress, xfade): graph-level split/trim/concat fallback.
- Cross-check hygiene test against `ffmpeg -filters` output.

### Wave 5 — Multi-track audio (BL-517)

- [ ] **BL-517** — Project-level multi-track audio schema + renderer integration. Per-track: `track_id`, `kind` (music/voice/binaural/sfx), `volume_envelope`, `weight`. Per-ducking-pair: `ducked_track_id`, `sidechain_track_id`, sidechaincompress params. Renderer emits `aformat=channel_layouts=stereo` per input + `asplit` on the sidechain trigger + `amix=inputs=N`. Verified default parameters: threshold=0.02, ratio=8 → 9.68 dB attenuation in voice-burst window, zero quiet-window/binaural delta.

### Wave 6 — TTS narration (BL-516)

- [ ] **BL-516** — Configurable TTS backend with three options:
  - Backend C: Piper local (default). `piper-tts==1.4.2` from `OHF-Voice/piper1-gpl`. Verified latency 3.32 s for 11 s of speech. GPL-3.0; subprocess invocation pattern.
  - Backend A: OpenRouter Kokoro cloud (first-class optional). `hexgrad/kokoro-82m`, Apache 2.0. Works without OpenRouter privacy switch flip.
  - Backend B: OpenRouter commercial models (opt-in). Requires user to flip privacy switch.
- Format reconciliation: upsample 22-24 kHz mono → 48 kHz stereo via existing snf DSP chain.
- Pre-synthesis caching by `hash(text, voice, backend)`.

### Wave 7 — Subtitles

- [ ] **BL-518** — SubtitleScriptBuilder. N timed captions via N `drawtext` filters chained with `enable='between(t,s,e)'`. drawtext is timeline-T capable; no non-T fallback needed for this BL.
- [ ] **BL-519** — Burned-in subtitles from SRT or ASS sidecar (v1 scope; VTT deferred). `subtitles=filename=<escaped>` for SRT, `ass=filename=<escaped>` for ASS. force_style escape as contract test. CI bundle guard for libass presence.
- [ ] **BL-520** — Soft subtitles muxed into mp4 via `mov_text` encoder. BCP-47 → ISO-639-2/B mapping at output time. Subtitle source paths are subprocess argv (no BL-499 escape).

### Cross-cutting Wave V — Value-kind escape policy

- [ ] **EffectBuilderValueEscaping ticket** (separate from the 18 BL drafts). Codify per-value-kind helpers:
  - Expression: single-quote-wrap (works for hue, scale, gblur, geq; verified per-filter).
  - Path: `emit_filter_option_path` per BL-499 (filter option values only).
  - Text: drawtext-specific escape (already exists).
  - Numeric / enum / boolean: validate at API boundary, no FFmpeg escape.
- Audit and migrate the three current `escape_for_filter` call-sites (Blur, Opacity, Scale at `video.rs:79/199/255`).

### Cross-cutting Wave G — Generic procedural

- [ ] **BL-514** — GenericProceduralImageBuilder powered by the bespoke 352-line recursive-descent parser (spike-verified). Grammar: `x/y/t` variables, `sin/cos/tan/atan2/hypot/sqrt/exp/log/abs/floor/ceil/mod/pow`, comparisons, `if(cond,then,else)`. Safety bounds: AST depth ≤ 32, eval step budget ≤ 10k per pixel, `pow`/`^` exponent magnitude ≤ 100, per-render wall-clock timeout. Renders ONE frame at one t-value; per-frame 30-fps regeneration is out of scope. Output PNG flows through BL-511 image-as-clip.

### Cross-cutting Wave T — Test harness updates

- [ ] **Chatbot harness consumes the render evidence API** (Wave 1 dependency). Asserts non-empty `command_args`, `exit_code == 0`, `output_size_bytes > 0`. Fails loudly when evidence is absent.
- [ ] **SSIM-based clip-attribution test seed**. Every multi-clip render in the harness verifies SSIM > 0.99 against source clips at segment midpoints (pattern from PoC-0).
- [ ] **Render-evidence-artefact persistence integration test**. Submit job → wait → retrieve evidence → assert all fields populated.
- [ ] **UAT scenarios** for: multi-clip explainer, hypnotherapy session (matching the two use cases in `04-use-cases.md`).
- [ ] **Hygiene tests:** `timeline_T_capable` registry cross-check, `subtitles`/`ass` filter availability in bundled FFmpeg, `escape_for_filter` call-site audit (zero new uses).

### Cross-cutting Wave D — Doc updates

- [ ] **Smoke test harness guide.** Add chromatic_aberration, the new builders (curves/vignette/hue/zoompan), procedural shapes, TTS, multi-track audio rows.
- [ ] **Manual / configuration reference.** Document any new `STOAT_*` settings (asset library root, TTS backend selection, OpenRouter key handling).
- [ ] **Effect-builder guide.** Per-builder timeline-T capability + value-kind escape policy.
- [ ] **Architecture refresh.** Update Release 1+2 architecture diagrams with the multi-input render graph, asset library, TTS provider abstraction.
- [ ] **STATUS.md hygiene.** Resolve the duplicate root `STATUS.md` vs `docs/STATUS.md` (decision: `docs/STATUS.md` canonical).

## In scope / out of scope

### In scope for Release 3

- Multi-clip rendering with per-clip effects
- Image-as-clip and user-asset library
- TTS narration (local + cloud)
- Multi-track audio with sidechain ducking and per-track volume envelopes
- Burned and soft subtitles (SRT, ASS for burned; SRT/ASS sidecars for soft)
- Procedural shape generators + generic expression-driven image generator
- The four single-filter wrap builders
- Render preflight + render evidence artefact API
- Test-harness updates for all of the above

### Out of scope (deferred to v084+ or beyond)

- VTT subtitle format (needs verification pass first)
- Multi-language TTS catalogues (v1 ships English; voice picker exposes catalogue)
- Real-time TTS preview during editing (latency too high)
- Image sequences as clips (PNG-per-frame via concat demuxer)
- GPU acceleration for procedural images
- Per-frame regeneration at 30 fps for BL-514 (perf doesn't allow at 720p)
- Cloud-storage asset backend (S3/Azure Blob)
- HLS/DASH manifest-based subtitle delivery
- 5.1/7.1 surround audio
- More than 4 audio tracks in the multi-track schema
- Bitmap subtitles (PGS, DVB)

## Version mapping (proposed; subject to user approval)

| Version | Waves landed |
|---|---|
| v083 | Wave 0 carry-forwards (BL-499 + BL-502) + Wave 1 truth/evidence (BL-505A + BL-506-tech). Cheap, high-leverage. |
| v084 | Wave 2 render graph (BL-505B + BL-505C) + Wave V value-kind escape policy. |
| v085 | Wave 3a builder wishlist (5 BLs in parallel) + Wave 4 timeline windows (BL-512). |
| v086 | Wave 3b asset library + image-as-clip (BL-515 + BL-511) + Wave G generic procedural (BL-514). |
| v087 | Wave 5 multi-track audio (BL-517) + Wave 6 TTS (BL-516). |
| v088 | Wave 7 subtitles (BL-518 + BL-519 + BL-520) + Wave T/D test harness + doc cleanup. |

Six versions total. Each builds on the previous via the dependency spine. The auto-dev process will refine the wave-to-version mapping based on capacity.

## Success gates

Release 3 is **done** when:

1. A multi-clip project authored via API renders all clips with all per-clip effects applied.
2. A render job exposes `command_args` + `exit_code` + `stderr_tail` + `output_size_bytes` in its response.
3. The chatbot harness rejects renders where the evidence is missing.
4. The two use cases in `04-use-cases.md` (multi-clip explainer + hypnotherapy session) can be authored, rendered, and verified end-to-end with no manual workarounds.
5. Every BL in the 18-item set has its acceptance criteria machine-verified by a contract test, integration test, or UAT scenario.
6. The smoke harness has rows for every new effect builder and every new clip type.
7. The configuration reference + smoke harness guide + effect-builder guide are all updated.
8. `STATUS.md` duplication is resolved.

## Risks the release explicitly takes on

See `02-architecture.md` Section "Risks and mitigations" and the carried-forward `00-RISKS.md` from the PoC chain. Headline risks:

- **R11 (high):** the v082 OpacityBuilder runtime failure is the highest-priority carry-forward. Without BL-502, animated opacity is broken in production.
- **R12 (medium):** the path-escape policy must be consistently applied. The BL-499 helper covers only filter option values, not subprocess argv paths — easy to get wrong.
- **GPL-3.0 distribution constraint** for Piper Backend C. Product decision accepted; subprocess invocation pattern limits the surface.
- **Two-registry drift** between Rust `EffectDefinition` and Python AI hints. Mitigated by making Rust authoritative and Python derived.

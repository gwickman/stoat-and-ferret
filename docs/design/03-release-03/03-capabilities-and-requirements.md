# Release 3 — Capabilities and Requirements

**Audience:** customer / product / non-technical reviewer + implementer.
**Purpose:** describe Release 3's capabilities in plain language with measurable acceptance criteria.

## How to read this document

Each capability is described as: **what the user can do** → **why it matters** → **acceptance signal** → **backlog item(s)**.

The acceptance signals are written so a non-engineer can read them and judge whether the capability is real. Implementer-facing detail is in the architecture and backlog docs.

## Capability map

```
Release 3 capabilities
│
├─ Composition
│   ├─ C1  Multi-clip timeline
│   ├─ C2  Per-clip effects with timed windows
│   ├─ C3  Transitions between clips
│   └─ C4  Image-as-clip
│
├─ Assets
│   ├─ A1  User-uploadable image / audio / subtitle / font / lut assets
│   ├─ A2  Procedural shape library (Spiral / RadialBurst / Checkerboard / ConcentricRings)
│   └─ A3  Generic equation-driven procedural image generator
│
├─ Audio
│   ├─ AU1 Multi-track audio with per-track volume automation
│   ├─ AU2 Voice ducking music when narration plays
│   └─ AU3 Text-to-speech narration (local Piper + cloud Kokoro)
│
├─ Subtitles
│   ├─ S1  Burned-in subtitles from SRT or ASS sidecar
│   ├─ S2  Soft (toggleable) subtitle tracks embedded in mp4
│   └─ S3  Timed text captions from a script (helper)
│
├─ Effect builders
│   ├─ E1  Zoompan (Ken Burns) fixed-canvas pan/zoom
│   ├─ E2  Curves colour-grading preset
│   ├─ E3  Vignette corner darkening
│   └─ E4  Hue rotation
│
└─ Trust & verification
    ├─ T1  Render preflight rejects projects the worker can't render
    ├─ T2  Every render exposes its evidence (command + exit + stderr + size)
    └─ T3  Carry-forward fixes (BL-499 Windows paths, BL-502 animated opacity)
```

## Functional requirements

### Composition (C1-C4)

#### C1 — Multi-clip timeline rendering
**What.** A project with multiple video clips (clip 1, clip 2, clip 3, ...) renders all clips in their timeline order. Today only the first clip renders; clips 2 onward are silently dropped.
**Why.** Educational explainers, marketing reels, hypnotherapy sessions — all rely on multiple segments. The silent-drop bug means snf is currently unusable for any project with more than one clip.
**Acceptance.** A project with 3 clips at 5 s each renders a 15 s (or transition-adjusted) output. SSIM of the rendered frame at each clip's midpoint matches the source clip > 0.99.
**BL:** BL-505 (split into BL-505A preflight, BL-505B translator, BL-505C worker integration).

#### C2 — Per-clip effects with optional timed windows
**What.** A clip can have any number of effects (blur, hue, opacity, etc.). Each effect can optionally have a window — a start and end time during which the effect is active.
**Why.** Today the persisted effects array is silently dropped by the render path. A "fade in over the first 2 seconds" never actually fades. Windowed effects are how creators control attention and pacing.
**Acceptance.** An effect with window 1.0-3.0 s applied to a clip renders WITH the effect during t=1.5 and WITHOUT during t=0.5 / t=3.5. Verified by frame extraction and pixel-difference probe.
**BL:** BL-505 + BL-512 (renderer consumption of existing WindowSpec + per-builder timeline-T flag).

#### C3 — Transitions between clips
**What.** Clips can be joined by a transition (xfade). Today multi-clip itself doesn't work, so transitions don't either.
**Why.** Smooth dissolves are basic visual grammar.
**Acceptance.** A 1-second xfade between two 5 s clips produces a 9 s output (5 + 5 - 1). The midpoint of the xfade window has visible blending of both clips (pixel sample shows neither pure source A nor pure source B).
**BL:** part of BL-505.

#### C4 — Image as clip
**What.** Use a static PNG or JPEG as a clip in the timeline. The image plays for the clip's duration and supports the same effects (blur, opacity, scale) as a video clip.
**Why.** Logo intro/outro, title cards, hypnotherapy spiral overlay, branded watermark — none of these need a video file.
**Acceptance.** A project with one video clip + one image clip (with duration 3 s, opacity fade-in) renders the image visible at the right time with the fade actually visible to a viewer.
**BL:** BL-511 (depends on BL-515 asset library + BL-502 opacity redesign).

### Assets (A1-A3)

#### A1 — User asset library
**What.** Upload an image / audio file / subtitle sidecar / custom font / LUT cube file once; reference it by ID across multiple projects.
**Why.** Today there's no API path. Users have to drop files into the working folder manually, which doesn't scale to multi-project workflows.
**Acceptance.** `POST /assets` accepts a PNG, stores it, returns an asset ID. `GET /assets?kind=image` lists it. `GET /assets/{id}/file` downloads it. Uploading the same file twice deduplicates by content hash. Path-traversal attempts are rejected.
**BL:** BL-515.

#### A2 — Procedural shape library
**What.** Generate one of four built-in shapes — Spiral, RadialBurst, Checkerboard, ConcentricRings — as a PNG asset that the timeline can use like any uploaded image.
**Why.** Hypnotherapy spirals, attention-grabbing radial bursts for explainers, checkerboards for test patterns, concentric rings for meditation. Currently snf has no shape vocabulary.
**Acceptance.** Each of the four shape generators produces a 720×720 RGBA PNG in under 50 ms. Pixel content matches a pinned reference hash (decoded RGBA buffer, not PNG bytes — encoders vary).
**BL:** BL-513.

#### A3 — Generic equation-driven procedural image
**What.** A user supplies a math expression like `if(mod(atan2(y,x)*3/(2*PI)+hypot(x,y)*5,1)<0.5,1,0)`. The system renders that expression as a procedural image (one pixel per `(x,y,t)` evaluation).
**Why.** When the four built-in shapes don't cover the case (an unusual wellness pattern, a custom test pattern).
**Acceptance.** A 1280×720 procedural image renders in under 500 ms on the dev workstation. Pathological expressions (`pow(2, pow(2, 30))`, deeply nested `if`, multi-thousand step chains) are rejected with a clear error, not a hung worker.
**BL:** BL-514 (uses the bespoke parser from the BL-514 spike — NOT evalexpr because AGPL-3.0).

### Audio (AU1-AU3)

#### AU1 — Multi-track audio with per-track volume automation
**What.** A project has multiple parallel audio tracks (e.g. music track, voice track, binaural beats track). Each track has a weight (mix balance) and optionally a volume envelope expressed as a function of time.
**Why.** Wellness sessions, instructional content, podcast-style overlays — all need more than one audio source playing simultaneously with predictable balance.
**Acceptance.** A 3-track render (music + voice + binaural) produces a stereo (2-channel) output where each track's contribution is identifiable in the spectrogram. A track with `volume_envelope='0.5+0.5*sin(2*PI*t/15)'` audibly modulates.
**BL:** BL-517.

#### AU2 — Sidechain ducking (voice attenuates music when speaking)
**What.** When the voice track has signal (someone is speaking), the music track's volume is automatically reduced. When the voice is quiet, music returns to full volume.
**Why.** Standard wellness/podcast production technique. Without it, the music drowns the voice and the listener has to manually adjust.
**Acceptance.** With default parameters (threshold=0.02, ratio=8, attack=20 ms, release=300 ms — verified in T3 sweep), the music carrier band loses at least 6 dB of energy during voice intervals and 0 dB during quiet intervals. Binaural track stays untouched.
**BL:** BL-517.

#### AU3 — Text-to-speech narration
**What.** A user supplies a script and a voice choice; the system synthesises spoken audio that lives in the project's voice track.
**Why.** Wellness affirmations, explainer voiceovers, accessibility narration — synthesised voice removes a recording session from the workflow.
**Acceptance.** Both options work:
- **Local (Piper, default).** Install: `pip install piper-tts==1.4.2` + ~95 MB voice model. Latency for an 11 s script: ~3.3 s including cold start; ~1 s steady-state with long-lived subprocess.
- **Cloud (OpenRouter Kokoro).** Requires configured OpenRouter API key. No privacy switch needed for Kokoro. Latency: 146 s cold start for 14 s of speech.
- Both backends output mono ~22-24 kHz; the snf pipeline upsamples to 48 kHz stereo automatically.
- A commercial-model option (Gemini TTS / Mai Voice / Grok Voice) is available behind OpenRouter's privacy switch as an opt-in.
**BL:** BL-516.

### Subtitles (S1-S3)

#### S1 — Burned-in subtitles
**What.** Subtitles are baked into the video pixels using libass; visible in any player.
**Why.** Broadcast distribution, social-media short-form, places where soft subtitles aren't honoured.
**Acceptance.** A 5 s video with a 3-entry SRT renders with each text line visible at the expected timestamp. ASS sidecars are also supported. VTT is NOT in v1 (separate verification needed).
**BL:** BL-519.

#### S2 — Soft (toggleable) subtitles in mp4
**What.** Subtitles are embedded as a separate stream in the mp4; players display them when the user toggles them on.
**Why.** Modern distribution (YouTube, Vimeo) prefers soft subtitles for accessibility — the viewer chooses whether to see them, and search engines can index them.
**Acceptance.** A render with two soft subtitle tracks (e.g. en + es) produces an mp4 where ffprobe sees two subtitle streams with the correct language metadata (`eng`, `spa`). The first track is marked as default disposition. Language tags use BCP-47 input format (`en`, `es-ES`) and are mapped to ISO-639-2/B at output time.
**BL:** BL-520.

#### S3 — Subtitle script helper
**What.** A user provides a list of `(start_s, end_s, text)` tuples; the system emits N timed text overlays without the user having to chain N drawtext effects manually.
**Why.** Hypnotherapy / wellness scripts often have many timed affirmation captions. Today users would have to compose them by hand.
**Acceptance.** A 10 s clip with 3 script entries renders with each text visible at the right timestamp.
**BL:** BL-518.

### Effect builders (E1-E4)

#### E1 — Zoompan (Ken Burns)
**What.** Slow pan/zoom inside a fixed output canvas. Visually distinct from the existing scale automation, which changes stream dimensions.
**Why.** Standard documentary / explainer technique.
**Acceptance.** A 5 s zoompan effect on a static image produces visible pan/zoom in the output. The builder emits `fps,settb` pin (verified mandatory for xfade compatibility).
**BL:** BL-507.

#### E2 — Curves
**What.** Apply a colour-curve adjustment by preset name (`vintage`, `cross_process`, etc.) or custom knee strings (`"0/0 0.5/0.4 1/1"`).
**Why.** One-click colour grading for non-colourist users.
**Acceptance.** `preset=vintage` produces a visibly different output from the same clip rendered without curves.
**BL:** BL-508.

#### E3 — Vignette
**What.** Cinematic corner darkening.
**Why.** Common cinematic effect; currently has to be hand-rolled with `geq`.
**Acceptance.** Default vignette produces visibly darker corners than the centre of the frame.
**BL:** BL-509.

#### E4 — Hue rotation
**What.** Shift the hue of every pixel by a static amount or an animated expression.
**Why.** Mood shifts, attention cues, simple colour cycling.
**Acceptance.** `hue=H='2*PI*t/3'` produces an output where pixel hue rotates continuously over time. Comma-bearing expressions (`if(lt(t,1),0,PI)`) render without escape — single-quote wrapping is the policy.
**BL:** BL-510.

### Trust & verification (T1-T3)

#### T1 — Render preflight
**What.** When a user submits a render, the API first checks whether the worker can actually execute it. If not, the response is a clear 422 (or warning) explaining what's unrepresentable.
**Why.** Today a render that the worker can't represent silently completes "successfully" with wrong output. The chatbot QA harness was tricked by this for multiple rounds before the gap was discovered.
**Acceptance.** Submitting a multi-clip project to a worker that doesn't support multi-clip returns 422 (or `status=warning` event) explaining why. No more silent success.
**BL:** BL-505A.

#### T2 — Render evidence artefact
**What.** Every completed render exposes its actual FFmpeg command args, exit code, stderr tail and output file size via the job-response API.
**Why.** Without this, "the render succeeded" is unverifiable. The QA harness needs to assert what actually ran, not trust HTTP 200.
**Acceptance.** `GET /render/{job_id}` (or `GET /render/{job_id}/evidence`) returns the evidence fields populated. The chatbot harness fails loudly when they're missing.
**BL:** BL-506-tech (sibling under BL-506).

#### T3 — Carry-forward fixes (BL-499 + BL-502)
**What.** Two v082 bugs whose escape fixes shipped but whose runtime behaviour was either broken (BL-502) or under-verified (BL-499).
**Why.** BL-502: animated opacity literally doesn't render. BL-499: Windows-path LUTs may fail. These existed before Release 3 but block Release 3's image-overlay and asset workflows.
**Acceptance.** BL-499: Windows-absolute LUT paths render via the `emit_filter_option_path` helper (single-quoted + colon-escaped). BL-502: animated opacity renders through `geq` with uppercase `T` and the fade is user-visible after composition through final yuv420p.
**BL:** BL-499 + BL-502.

## Non-functional requirements

### Performance

| Requirement | Target | Source |
|---|---|---|
| Multi-clip render performance | within 20% of single-clip baseline per equivalent video duration | implied by no-regression UAT |
| Procedural shape generation (BL-513) | ≤ 50 ms at 720×720 RGBA single-threaded | PoC-5 measured 2.5-7.7 ms |
| Generic procedural image (BL-514) | ≤ 500 ms per frame at 1280×720 | bespoke parser spike measured ~390 ms |
| Render evidence retrieval | ≤ 50 ms per `GET /render/{id}/evidence` | normal DB-backed API budget |
| TTS Piper synthesis (CPU baseline) | ≤ 15 s for 30 s of speech on CPU dev workstation | Piper probe measured 3.32 s for 11 s including cold start; per `piper-fork-comparison.md` rough 8-15 s for 30 s on CPU. Codex `18` correctly flagged that the original ≤ 5 s target was GPU/optimised territory, not the CPU baseline. |
| TTS Piper synthesis (warmed / GPU stretch) | ≤ 5 s for 30 s in warmed long-lived subprocess OR with GPU | aspirational; benchmark in cold + warm states; record actuals before tightening the SLA |
| TTS Kokoro cloud synthesis | non-interactive only (≥10× real-time cold) | not suitable for live preview; pre-synthesise at render-prep time |
| Multi-track audio ducking | ≥ 6 dB attenuation on music carrier during voice intervals | T3 sweep verified 9.68 dB at default params |
| Render-graph translator overhead | ≤ 100 ms per render call vs raw FFmpeg subprocess | PyO3 boundary cost |

### Reliability

- Render preflight rejects unrepresentable projects 100% of the time (no silent success).
- Pathological procedural expressions abort with a clear error within 1 s.
- Asset uploads with MIME-vs-content mismatch are rejected.
- Path traversal attempts via the asset API are rejected.

### Security

- `STOAT_ASSETS_DIR` is documented; not in `KNOWN_UNDOCUMENTED_SETTINGS_VARS`.
- OpenRouter API keys are never logged in server output and are stripped from render evidence by a redaction pass (unit-tested).
- Render evidence full endpoint disabled by default outside local/test deployments; opt-in via `STOAT_RENDER_EVIDENCE_FULL_ACCESS=true`. **No admin role surface exists in current snf** (verified by codex `18` grep); the env-var gate is the only knob.
- Asset uploads are content-sniffed (not MIME-extension-trusted).

### Per-BL config variable ownership (per codex `18` Major Risk)

Every `STOAT_*` env var introduced in Release 3 has an owning BL whose ACs document the variable in BOTH `docs/setup/04_configuration.md` AND `docs/manual/configuration-reference.md`, and assert `KNOWN_UNDOCUMENTED_SETTINGS_VARS` stays empty.

| Variable | Owning BL | Purpose |
|---|---|---|
| `STOAT_RENDER_EVIDENCE_FULL_ACCESS` | BL-506-tech | Gates full evidence endpoint |
| `STOAT_ASSETS_DIR` | BL-515 | Asset library root path |
| `STOAT_ASSETS_MAX_SIZE_BYTES` | BL-515 | Max upload size |
| `STOAT_OPENROUTER_API_KEY` | BL-516 | OpenRouter auth (Kokoro + commercial) |
| `STOAT_TTS_DEFAULT_BACKEND` | BL-516 | Default TTS backend (`piper_local` | `openrouter_kokoro` | `openrouter_commercial`) |
| `STOAT_TTS_PIPER_MODELS_DIR` | BL-516 | Piper ONNX model cache location |
| `STOAT_TTS_CACHE_DIR` | BL-516 | Synthesised audio cache (asset-library-owned or sidecar) |

### Compatibility

- All rendered outputs use `format=yuv420p` for Windows Media Foundation compatibility.
- Every named filter chain feeding xfade is normalised to project `fps,settb`.
- Default voice catalogue is licensed CC-BY-4.0 (commercial-use OK).
- GPL-3.0 disclosure for bundled Piper documented in `NOTICE`.

### Observability

- Every render job persists evidence (`command_args`, `exit_code`, `stderr_tail`, `output_size_bytes`).
- A new structured log event **`render.evidence_persisted`** fires at job completion. **Namespace `render.*` per codex `18` Major Risk** — `render_executor.*` is NOT an approved namespace; `render.*` is. Other new events: `render.preflight_warning`, `render.preflight_reject`.
- TTS / asset events are API/WebSocket event-payload names (not structured logs) — see `06-gui-integration.md`. If any of them later need to be structured logs, the namespaces (`asset.*`, `tts.*`) get declared in `docs/design/FRAMEWORK_CONTEXT.md` before use.
- The `timeline_T_capable` hygiene test runs in CI on every PR touching `EffectDefinition`.

### Documentation

Documentation is a release deliverable, not an afterthought:

- `docs/manual/04_effects-guide.md` updated for every new builder (BL-507/508/509/510).
- `docs/manual/configuration-reference.md` + `docs/setup/04_configuration.md` updated for new `STOAT_*` settings (asset library root, TTS backend selection).
- `docs/manual/smoke-test-harness.md` gains rows for every new builder and clip type.
- `docs/manual/07_rendering-guide.md` documents the new evidence API surface.
- A new `docs/manual/tts-guide.md` covers Backend selection (Piper vs Kokoro), voice picker, GPL implications.
- A new `docs/manual/asset-library.md` covers upload + reference workflow.
- Architecture diagrams in `docs/architecture/` (if extant) refreshed to include multi-input render path, asset library, TTS abstraction.

## What this release is NOT

- Not a UI redesign. GUI touchpoints (06-gui-integration.md) are additive: new pages for the asset library, voice picker, evidence inspector — but no overhaul.
- Not an editing-tools release. No timeline scrubbing, no razor cuts, no waveform display upgrades.
- Not a streaming release. HLS preview stays as-is.
- Not a project-template / preset-library release.
- Not a multi-user / collaboration release.

## Open product / scope questions

These are decisions for the user / product direction during design review:

1. **Default voice catalogue.** Ship 1 voice (en_US-lessac-medium) or 3 (en_US + en_GB + 1 more)? Affects install size.
2. **Asset library quota.** Per-user / per-project / unlimited? Implies user-management work either way.
3. **Soft subtitles in non-mp4 containers.** Reject with clear error or auto-route to a codec the container accepts (srt for matroska, etc.)?
4. **BL-514 ship priority.** It's the most deferrable wave per the original PoC plan. Ship in v086 (proposed) or v088?
5. **Commercial TTS models.** Should snf ship documentation telling users how to flip the OpenRouter privacy switch, or leave it implicit?
6. **AGPL vs MIT for the bespoke parser.** The parser is snf-original code; what licence does snf attach to it?

# Release 3 — Architecture

**Audience:** implementer, reviewer, future maintainer.
**Scope:** the new and changed subsystems Release 3 introduces, and how they fit alongside the Release 1 (effect-builder + render path) and Release 2 (keyframe compiler, QC/verification, delivery profiles) foundations.

## High-level architecture

```
                  ┌──────────────────────────────────────────────────────┐
                  │                       GUI                            │
                  └──────────────────────────────────────────────────────┘
                                          │
                                          ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      FastAPI HTTP / WS layer                             │
│  /projects /clips /clips/{id}/effects /effects /render /render/preview    │
│  + NEW: /assets (BL-515)  /render/{id}/evidence (BL-506-tech)             │
└──────────────────────────────────────────────────────────────────────────┘
                                          │
                       ┌──────────────────┼──────────────────┐
                       ▼                  ▼                  ▼
              ┌────────────────┐ ┌────────────────┐ ┌────────────────┐
              │ Render service │ │ Asset library  │ │  TTS service   │
              │ + preflight    │ │   (NEW)        │ │  (NEW)         │
              │   (BL-505A)    │ │   (BL-515)     │ │ (BL-516)       │
              └────────────────┘ └────────────────┘ └────────────────┘
                       │                                     │
                       ▼                                     ▼
              ┌────────────────────────────────────────────────────────┐
              │              Rust core (PyO3)                          │
              │                                                        │
              │  Effect-builder registry (extended metadata, R3)       │
              │  Render-graph translator (BL-505B, NEW)                │
              │  Bespoke expression parser (BL-514, NEW, 352 lines)    │
              │  emit_filter_option_path helper (BL-499, NEW)          │
              │  geq opacity emit (BL-502 redesign)                    │
              │  Per-value-kind escape helpers (WaveV, NEW)            │
              └────────────────────────────────────────────────────────┘
                       │                                     │
                       ▼                                     ▼
              ┌────────────────┐                  ┌────────────────────┐
              │   FFmpeg       │                  │  Piper subprocess  │
              │  (subprocess)  │◄─────────────────┤  (Backend C, NEW)  │
              │                │                  └────────────────────┘
              │  ─────────     │
              │  Records       │                  ┌────────────────────┐
              │  evidence      │◄─────────────────┤  OpenRouter        │
              │  (BL-506-tech) │                  │  (Backends A/B,    │
              └────────────────┘                  │   NEW HTTP client) │
                                                  └────────────────────┘
```

Bold borders mark NEW subsystems. Everything else extends an existing Release 1-2 component.

## Subsystem details

### 1. Render-graph translator (BL-505B)

**Location:** `rust/stoat_ferret_core/src/render/graph.rs` (new module alongside the existing `plan.rs` and `compose/graph.rs`).

**Inputs:** a `ProjectRenderSpec` dataclass deserialised from:
- `clips: list[ClipResponse]` (existing schema at `src/stoat_ferret/api/schemas/clip.py:53-83`, including the populated `effects: list[dict]` per clip and optional `WindowSpec` per effect).
- `transitions: list[Transition]` (xfade source + target clip ids + duration + offset).
- Output framerate, dimensions, pixel format.

**Outputs:** an `EmittedCommand` containing:
- `args: list[str]` — full FFmpeg subprocess args ready for `asyncio.create_subprocess_exec`.
- `filter_graph: str` — the `-filter_complex` value emitted (for evidence/debug).
- Optional `filter_script_path: PathBuf` if using `-filter_complex_script`.

**Algorithm:**

```
for clip in clips:
    label = f"[c{clip.index}]"
    chain = f"[{input_idx}:v]trim=start=...,setpts=PTS-STARTPTS"
    for effect in clip.effects:
        defn = registry.get(effect.effect_type)
        body = defn.build_fn(effect.parameters)   # existing build_fn per builder
        if effect.window:
            if defn.timeline_T_capable:
                body = f"{body}:enable='between(t,{w.start_s},{w.end_s})'"
            else:
                # graph-level split/trim/concat fallback
                body = wrap_with_split_trim_concat(body, w.start_s, w.end_s)
        chain = f"{chain},{body}"
    if defn.timebase_mutating for any effect in chain:
        chain = f"{chain},fps={project_fps},settb=1/{project_fps}"
    chain = f"{chain}{label}"
    segment_chains.append(chain)

for transition in transitions:
    # xfade [c0][c1]xfade=...[xf]
    segment_chains.append(compose_transition(transition))

final = f"{last_label}format=yuv420p[out]"
```

**Path handling:** the translator distinguishes two path categories:
- **Subprocess argv paths** (`-i <input>`, `-y <output>`, `-i <subtitle_for_soft_mux>`): passed as separate argv elements. **Opaque to FFmpeg's filter parser; no escape needed.**
- **Filter-graph option-value paths** (`lut3d=file=...`, `subtitles=filename=...`, `ass=filename=...`, `movie=filename=...`): embedded inside `-vf`/`-filter_complex`. **Apply `emit_filter_option_path` from BL-499.**

**Acceptance:** PoC-0 at `<gw-test>/snf-showcase-20260614/gaps-identified/poc-work/poc-0-render-graph/` proved the concept end-to-end. The Rust implementation is a direct port of that translator's algorithm.

### 2. Render preflight + evidence (BL-505A + BL-506-tech)

**Location:**
- Preflight: `src/stoat_ferret/api/routers/render.py` (extends the existing `POST /render` handler).
- Evidence: `src/stoat_ferret/render/executor.py` (existing) writes evidence per job; `src/stoat_ferret/api/schemas/render.py::RenderJobResponse` (existing) gets new fields; OR a new `GET /render/{job_id}/evidence` endpoint.

**Preflight rules (BL-505A):**

Before submitting a render job, validate that the persisted project state can be represented by the current worker. Reject with 422 (or warning event) when:
- The project has multi-clip timelines (until Wave 2 lands; warning then).
- Any clip has persisted effects in the new metadata fields the current worker version cannot consume.
- A generator/image clip is referenced before BL-511 + BL-515 ship.
- A multi-track audio spec is present before BL-517 ships.

**Evidence fields (BL-506-tech):**

```
RenderEvidence:
  command_args:        list[str]      # exact argv
  command_build_error: str | None     # if command never spawned
  exit_code:           int | None
  stderr_tail:         str            # last 16 KB
  output_path:         str
  output_size_bytes:   int | None
  filter_script_path:  str | None
```

**Redaction policy (corrected per codex `18` Major Risk):** snf does not currently have an admin/role authentication surface (codex `18` verified by grep — no `admin/require_admin/current_user` matches in `src/stoat_ferret/api/`). Calling the full-evidence endpoint "admin-only" would imply a new auth feature that is out of scope for Release 3.

The actual model:

- **Default-public surface** (returned in `GET /render/{job_id}`): `exit_code`, `output_size_bytes`, `command_build_error`. Sanitised, no absolute paths, no env-derived values.
- **Full evidence endpoint** (`GET /render/{job_id}/evidence`): **disabled by default outside local/test deployments unless `STOAT_RENDER_EVIDENCE_FULL_ACCESS=true`**. When disabled, returns 403/404. When enabled, returns full `command_args` + `stderr_tail` + `output_path` + `filter_script_path`. No role check — the env var IS the gate.
- **Redaction pass on full evidence:** even when enabled, `command_args` and `output_path` strip any value matching the OpenRouter API key prefix (`sk-or-v1-*`) or env-var patterns (`$STOAT_*`) before serialisation. The redaction pass is unit-tested.
- A future BL (post-Release 3) introduces a role-based auth surface; until then, the `STOAT_RENDER_EVIDENCE_FULL_ACCESS` env-var gate is the only knob.

**Implementation tests prove:**
- Public response contains no absolute local paths and no env-derived values.
- Full-evidence response with the gate disabled returns 403/404.
- Full-evidence response with the gate enabled never includes a redacted-prefix value (negative test seeds an API key into command_args, asserts it's stripped).

### 3. Asset library (BL-515)

**Location:** new `src/stoat_ferret/assets/` package + new DB table `assets`.

**Schema:**

```
assets:
  id           UUID PK
  kind         enum: image | audio | subtitle | font | lut
  file_path    str        # content-addressed under STOAT_ASSETS_DIR
  original_filename str
  mime_type    str
  size_bytes   int
  licence      str | None
  tags         list[str]
  uploaded_by_user_id UUID | None
  created_at   timestamp
  deleted_at   timestamp | None  # soft delete
```

**Endpoints:**
- `POST /assets` — multipart upload.
- `GET /assets?kind=image&tag=...` — paginated list.
- `GET /assets/{id}` — metadata.
- `GET /assets/{id}/file` — download.
- `DELETE /assets/{id}` — soft delete.

**Storage:** under `STOAT_ASSETS_DIR` (configurable env var, default `working/assets/`). Filenames are content-hashed (e.g. SHA-256 prefix) to deduplicate.

**Security:**
- Content-sniff validation via `python-magic` or `infer`; rejects MIME-extension-vs-content mismatch with 415.
- All filesystem ops resolved under `STOAT_ASSETS_DIR` root; reject computed paths that escape (test `../`, absolute paths, symlinks).
- `STOAT_ASSETS_DIR` documented in both `docs/setup/04_configuration.md` and `docs/manual/configuration-reference.md`; not added to `KNOWN_UNDOCUMENTED_SETTINGS_VARS`.

**Resolution policy:** asset retrieval returns raw paths. The renderer applies BL-499's `emit_filter_option_path` only when the path flows into a filter option value (lut3d/subtitles/ass/movie); subprocess argv paths (`-i <image>`) get the raw path.

### 4. Image-as-clip (BL-511)

**Location:** schema extension in `src/stoat_ferret/api/schemas/clip.py` + render handling in the translator.

**Schema:**

```
clip_type:        Literal["file", "generator", "image"]   # ADDED "image"
source_video_id:  UUID | None      # existing, for file clips
source_asset_id:  UUID | None      # NEW, for image clips (resolves via BL-515)
generator_params: dict | None      # existing, for generator clips
```

**Render handling:** the translator emits `-loop 1 -i <image_path>` for image clips. Path passed as argv (no escape). Duration controlled by `timeline_end - timeline_start`; the trim filter enforces it.

**Effect compatibility:** image clips accept the same per-clip video effects as file clips. Audio effects on image clips are no-ops.

### 5. Bespoke expression parser + procedural image builders (BL-514, BL-513)

**Location:**
- BL-513 four built-in shapes: `rust/stoat_ferret_core/src/effects/procedural_shapes.rs`.
- BL-514 generic parser: `rust/stoat_ferret_core/src/effects/procedural_parser.rs`. **352 lines** ported directly from the spike at `<gw-test>/snf-showcase-20260614/gaps-identified/poc-work/poc-1-parser-langfit/bespoke-spike/`.

**Why bespoke instead of evalexpr:** evalexpr is AGPL-3.0-only — viral copyleft on the snf binary. Bespoke parser uses only `std`, no upstream maintenance, no licence drag. Verified per-pixel eval cost ~0.42 µs.

**Grammar (locked):**

```
expr     := equality
equality := comparison (('==' | '!=') comparison)*
comparison := term (('<' | '<=' | '>' | '>=') term)*
term     := factor (('+' | '-') factor)*
factor   := unary (('*' | '/' | '%') unary)*
unary    := '-' unary | power
power    := primary ('^' unary)?
primary  := number | ident | ident '(' args ')' | '(' expr ')'
```

Built-ins: `sin cos tan atan2 hypot sqrt exp log abs floor ceil mod pow if`. Variables: `x y t`. Safety: AST depth ≤ 32, eval step budget ≤ 10k per pixel, `pow`/`^` exponent magnitude ≤ 100, per-render wall-clock timeout.

**Output:** PNG via the `image = "0.25"` crate. Flows through BL-511 image-as-clip.

### 6. Multi-track audio (BL-517)

**Location:** schema in `src/stoat_ferret/api/schemas/audio_track.py` (new) + renderer in `rust/stoat_ferret_core/src/ffmpeg/audio.rs` (existing — add `MultiTrackDuckingPattern` alongside the current `DuckingPattern`).

**Schema (per project, not per clip):**

```
audio_tracks: list[AudioTrack]
  AudioTrack:
    track_id:        str
    kind:            Literal["music", "voice", "binaural", "sfx"]
    volume_envelope: str | None     # expression in `t`, evaluated via volume='...':eval=frame
    weight:          float

ducking_pairs: list[DuckingPair]
  DuckingPair:
    ducked_track_id:    str
    sidechain_track_id: str
    threshold:          float       # default 0.02 (verified)
    ratio:              float       # default 8 (verified)
    attack_ms:          int         # default 20
    release_ms:         int         # default 300
    apply_pre_volume:   bool        # default True
```

**Renderer emit pattern (verified by PoC-3 stereo retest):**

```
[0:a]aformat=channel_layouts=stereo[m_st];
[1:a]aformat=channel_layouts=stereo,asplit=2[v_st1][v_st2];
[m_st][v_st1]sidechaincompress=threshold=0.02:ratio=8:attack=20:release=300[ducked_music];
[ducked_music][v_st2][2:a]amix=inputs=3:weights=1.0 1.5 0.6:duration=longest[out]
```

The `asplit` on the sidechain trigger lets the trigger feed both the compressor AND the final amix as a clean branch.

### 7. TTS narration (BL-516) — cue/track model

**Location:** new `src/stoat_ferret/tts/` package with provider abstraction; new `TtsCue` schema + per-project cue collection (NOT a per-clip effect). Per codex `18` Blocker 5, modelling TTS as a clip-level effect cannot represent the actual narration shape (many phrases at different timestamps on the voice track), and clip schema does not currently have an audio clip type. The cue/track model is the correct shape.

**Data model — TtsCue:**

```python
class TtsCue(BaseModel):
    cue_id: UUID
    project_id: UUID
    track_id: str                  # references an AudioTrack with kind="voice"
    start_s: float                 # placement on the timeline
    text: str
    voice: str                     # backend-specific catalogue voice id
    backend: Literal["piper_local", "openrouter_kokoro", "openrouter_commercial"]
    gain_db: float = 0.0
    pan: float = 0.0
    cache_key: str                 # derived hash(text, voice, backend); used by render preflight
    generated_asset_id: UUID | None = None    # populated when synth succeeds
    status: Literal["pending", "synthesising", "ready", "failed"] = "pending"
    error: str | None = None
    created_at: datetime
    updated_at: datetime
```

A project has zero or more TtsCues. Each cue references a voice track (via `track_id`); multiple cues can target the same track at different `start_s` values.

**Synthesis lifecycle:**

1. User creates a cue: `POST /projects/{p}/tts_cues` with text/voice/backend/start_s/track_id.
2. Render preflight (BL-505A) iterates project cues; for any cue without a `generated_asset_id`, calls the TTS service.
3. TTS service hashes (text, voice, backend) → cache_key. If cached asset exists, set `generated_asset_id` and `status=ready`. Otherwise:
   - Spawn provider (Piper subprocess OR OpenRouter HTTP call).
   - Apply format reconciliation: upsample 22-24 kHz → 48 kHz, pan mono → stereo via existing snf DSP.
   - Upload result as a new asset (kind=audio) via the asset library.
   - Update cue with `generated_asset_id` and `status=ready`.
4. Renderer (BL-505B) reads cues + tracks; emits per-cue input via `-i <asset_path>` with an `adelay=<start_s*1000>|<start_s*1000>` filter to place the cue on the timeline.

**Provider abstraction:**

```python
class TTSProvider(Protocol):
    def synthesise(self, text: str, voice: str, out_path: Path) -> None:
        """Synthesise and write to out_path."""
    def available_voices(self) -> list[str]:
        """Return the voice catalogue (refreshed at startup for cloud providers)."""
```

Three implementations:

1. **`PiperProvider`** (Backend C, default). Spawns `python -m piper --model <onnx> --output-file <wav> -- "<text>"` as a long-lived subprocess. Per codex `18` Major Risk: see `03-capabilities-and-requirements.md` for the corrected performance target — Piper's CPU baseline is 8-15 s for 30 s of speech, not 5 s.
2. **`OpenRouterKokoroProvider`** (Backend A). Calls `POST /api/v1/audio/speech` with `model=hexgrad/kokoro-82m`, `response_format=mp3` (wav rejected). Requires configured OpenRouter API key.
3. **`OpenRouterCommercialProvider`** (Backend B, opt-in). Same endpoint; **available_voices() queries OpenRouter's `/models?output_modalities=speech` at startup** to discover commercial models dynamically (per codex `18` smaller correction 5 — hard-coding `google/gemini-3.1-flash-tts-preview` etc. as ACs is fragile because OpenRouter's catalogue changes). The provider lists whatever the API returns gated by the privacy switch.

**Caching:** TTS results are cached as assets via BL-515. Cache_key is `sha256(text || "::" || voice || "::" || backend)`. Same cue text + voice + backend = same asset_id retrieved on subsequent renders. Editing iterations re-use cached output for free.

**Format reconciliation:** all providers produce 22-24 kHz mono. The TTS service upsamples to 48 kHz and pans to stereo before storing as an asset, so downstream the mixer treats it as normal stereo audio.

**Per-cue routing into the multi-track mixer:** the cue's `track_id` says which AudioTrack it belongs to; cues on a "voice" track participate in any DuckingPair where that track is `sidechain_track_id`. So the wellness affirmation cues at t=5, t=45, t=130 all participate in voice→music ducking automatically once the track configuration is in place.

**No per-clip TTS effect.** The TTS-as-clip-effect pattern from earlier drafts is dropped. The cue model is more accurate to how narration actually works.

### 8. Subtitles (BL-518 + BL-519 + BL-520)

**BL-518 — SubtitleScriptBuilder.** Emits N chained `drawtext` filters, each with `enable='between(t,s,e)'`. drawtext is timeline-T capable; no fallback needed.

**BL-519 — BurnedSubtitleBuilder.** Routes to `subtitles=filename=...` for SRT or `ass=filename=...` for ASS. Path via `emit_filter_option_path`. `force_style` wrapped in single quotes for ASS rendering of SRT input (e.g. `:force_style='Fontsize=32,PrimaryColour=&Hffffff&'`). VTT deferred.

**BL-520 — Soft subtitles.** Output-level option (not effect-level). Renderer adds `-i <subtitle_path>` per soft track (argv, no escape) plus `-c:s mov_text -metadata:s:s:N language=<iso639> [-disposition:s:N default]`. BCP-47 → ISO-639-2/B translation at output time via a vetted mapping table (e.g. `babel`'s data, or a hand-pinned dict for the v083 supported set).

### 9. Effect registry metadata extension

**Authority — Option A locked (per codex `18` Blocker 4):** the existing Python `EffectDefinition` at `src/stoat_ferret/effects/definitions.py:63-88` **remains authoritative for Release 3**. New fields are added to the Python dataclass:

```python
@dataclass(frozen=True)
class EffectDefinition:
    # existing fields ...
    name: str
    description: str
    parameter_schema: dict[str, object]
    ai_hints: dict[str, str]
    preview_fn: Callable[[], str]
    build_fn: Callable[[dict[str, Any]], str]   # may delegate to Rust via PyO3
    ai_summary: str = ""
    example_prompt: str = ""
    automatable: frozenset[str] = field(default_factory=frozenset)
    automation_filter_template: str | None = None

    # NEW in Release 3:
    stream_kind: Literal["audio", "video"] = "video"
    arity: tuple[int, int] = (1, 1)
    chain_safe: bool = True
    timebase_mutating: bool = False
    timeline_T_capable: bool = False
    requires_filter_option_path_escape: bool = False
    value_kind_per_option: dict[str, Literal["expression","path","text","numeric","enum","boolean"]] = field(default_factory=dict)
```

`build_fn` entries that emit non-trivial filter graphs (BL-505B translator interaction, BL-502 geq emit, BL-513 shape generators, BL-514 parser-driven generator) delegate to Rust through PyO3-exposed pure functions. The metadata itself stays in Python.

**No two-registry split inside Release 3.** A future substrate item migrates registry metadata authority to Rust:

- New BL filed (v084+): `Migrate effect-registry metadata authority to Rust`.
- Substrate work: expose `EffectDefinition` equivalent through PyO3; update `_core.pyi` append-only via `cargo run --bin stub_gen` then manual merge; add Python AI-hint derivation; ship drift tests that prove hand-authored Python hints stay in sync with Rust source.
- Until that substrate lands, every new Release 3 builder adds a Python `EffectDefinition` entry whose `build_fn` is the integration point with Rust pure functions where needed.

**Hygiene test** (added in Wave T) cross-checks the `timeline_T_capable` flag against `ffmpeg -filters` output. Fails CI if any Python `EffectDefinition` declares a capability its filter doesn't have.

### 10. Per-value-kind escape policy (Wave V cross-cutting)

```rust
// Expression value (hue, scale, gblur, geq, volume animation, etc.)
fn emit_expression(expr: &str) -> Result<String> {
    if expr.contains('\'') { return Err("embedded single quote"); }
    Ok(format!("'{}'", expr))
}

// Path value (lut3d.file, subtitles.filename, ass.filename, movie.filename)
fn emit_filter_option_path(p: &Path) -> Result<String> {
    let fwd = p.to_string_lossy().replace('\\', "/");
    if fwd.contains('\'') { return Err("apostrophe in path"); }
    Ok(format!("'{}'", fwd.replace(':', r"\:")))
}

// Text value (drawtext text)
fn emit_drawtext_text(s: &str) -> String {
    // existing escape_drawtext + wrap
    format!("'{}'", drawtext_escape(s))
}

// Numeric / enum / boolean: validate at API; emit bare
```

The three current `escape_for_filter` call-sites (Blur, Opacity, Scale at `video.rs:79/199/255`) migrate to `emit_expression`. The legacy `escape_for_filter` is kept as a private helper through the migration then removed.

## Data flow changes

### Render request → output (Release 3)

```
1. POST /render → API handler
2. Render preflight (NEW, BL-505A): validate persisted state vs worker capability
3. RenderService.submit_job → RenderQueue
4. Worker pulls job → build_command_for_job
5. build_command_for_job calls Rust render-graph translator (NEW, BL-505B)
   - Translator reads project clips + effects + transitions
   - Emits multi-input filter_complex with per-clip sub-chains
   - Applies path-escape policy per value kind
   - Terminates with format=yuv420p
6. RenderExecutor spawns FFmpeg subprocess with translator's args
7. RenderExecutor captures: command_args, exit_code, stderr_tail, output_size
8. Evidence persisted to job record (NEW, BL-506-tech)
9. Job status → completed; evidence retrievable via GET /render/{id}/evidence
```

### Asset upload → use in clip

```
1. POST /assets (multipart) → AssetService
2. Content-sniff validation → reject mismatched MIME
3. Hash + write under STOAT_ASSETS_DIR
4. Record persisted to assets table
5. POST /projects/{p}/clips with clip_type=image, source_asset_id=<id>
6. At render time, translator resolves asset_id → file_path
7. For image clips: emit -loop 1 -i <file_path> (argv; no escape)
8. For lut3d/subtitles: emit lut3d=file='<escaped>' (filter option; escape applied)
```

### TTS narration in a project

```
1. User adds a tts_narration effect to a voice-track clip
   - text="Find a comfortable position..."
   - voice="en_US-lessac-medium"
   - backend="piper_local"
2. Render preflight resolves TTS spec → synthesise via Piper subprocess
3. Output WAV cached at working/tts-cache/<hash>.wav
4. Renderer treats the cached WAV as a normal audio input alongside music + binaural
5. Multi-track schema routes voice through sidechain ducking against music
```

## Risks and mitigations

| Risk | Severity | Mitigation |
|---|---|---|
| Two-registry drift (Rust EffectDefinition vs Python AI hints) | High | Rust authoritative; Python derived via PyO3 binding. CI test asserts they match. |
| BL-499 escape misapplied to argv paths | Medium | Helper renamed `emit_filter_option_path` (scope in the name). Path-handling rule documented in BL-505B and BL-511. |
| GPL-3.0 distribution constraint (Piper) | Medium | Subprocess invocation pattern bounds the surface. Product decision recorded in BL-516. |
| OpenRouter privacy switch may block commercial models | Low | Backend B opt-in; Kokoro (Backend A) works without the switch. |
| Bespoke parser missing safety budget edge cases | Medium | AST depth + step budget + pow clamp combined. Spike validated all three; add a fuzz test in Wave T. |
| TTS cold-start latency (Piper 1.5-3 s, Kokoro 146 s on first call) | Low | Long-lived Piper subprocess; pre-synthesis caching. Kokoro warm-state benchmark needed in Wave T. |
| Asset library path traversal | High | Server resolves all paths under STOAT_ASSETS_DIR root; test suite includes `../`, absolute, symlink probes. |
| BL-512 timeline-T misclassification leading to broken renders | Medium | Hygiene test cross-checks registry against `ffmpeg -filters`. zoompan was misclassified once; codex caught it; same test prevents recurrence. |

## What does NOT change

Release 3 keeps:

- Release 1 effect-builder pattern (builders + JSON schema + AI hints + preview_fn + build_fn).
- Release 1 render-service queue model.
- Release 1 HLS preview path (unchanged for now).
- Release 2 keyframe→expression compiler (BL-507/510/etc. animations route through it).
- Release 2 QC/verification + delivery profile pass.
- Release 2 markers / regions.
- Existing `WindowSpec` schema (BL-446 v080 PR #581).
- Existing audio mixing primitives (`AmixBuilder`, `AudioMixSpec`, `DuckingPattern` — extended, not replaced).

## Reading order for implementers

1. This doc (`02-architecture.md`).
2. The wave the implementer is starting (`01-roadmap.md`).
3. The PoC artefact for that wave (under `<gw-test>/snf-showcase-20260614/gaps-identified/poc-work/`).
4. The BL draft for the specific item (`backlog/BL-DRAFT-bl<N>-...md`).
5. `07-test-strategy.md` for the acceptance approach.

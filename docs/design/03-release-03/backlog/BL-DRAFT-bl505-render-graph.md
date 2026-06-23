# BL-DRAFT-bl505-render-graph

**Status:** drafted, not filed
**Supersedes / amends:** BL-505 (currently "Render pipeline ignores multi-clip timeline and per-clip effects")
**Evidence:** `poc-work/poc-0-render-graph/`, `poc-work/explores/T7c-render-pipeline-shape.md`, `09-action-plan-2-execution-results.md`
**Why now:** PoC-0 proved an out-of-tree translator pattern works end-to-end with SSIM-confirmed clip attribution. The v083 design can now commit the architecture with confidence rather than speculation.

## Problem statement

Confirmed at `src/stoat_ferret/render/worker.py:107`:

```python
first_clip = clips[0]   # all subsequent clips are silently dropped
```

Plus `worker.py:123-128` — multi-segment WARNING but still uses `segments[0]`.

Plus `worker.py` never reads `clips[i].effects` — the persisted effects array is invisible to the worker.

Plus the Rust `CompositionClip` in `rust/stoat_ferret_core/src/render/plan.rs::build_render_plan` carries no effects field — even if the worker forwarded them, the Rust layer has nowhere to put them.

## Proposed architecture (validated by PoC-0)

Render pipeline rewrite touches three layers:

### Layer 1 — schema additions to EffectDefinition

`src/stoat_ferret/effects/definitions.py:63-88` adds:

```python
stream_kind: Literal["audio", "video"]
arity: tuple[int, int] = (1, 1)
chain_safe: bool = True
timebase_mutating: bool = False
timeline_T_capable: bool = False
requires_path_escape: bool = False
value_kind_per_option: dict[str, Literal["expression","path","text","numeric","enum","boolean"]]
```

Plus hygiene test cross-checking `timeline_T_capable` against `ffmpeg -filters` output.

**Single source of truth (corrected 2026-06-16 per codex `18` Blocker 4):** the **Python `EffectDefinition`** at `src/stoat_ferret/effects/definitions.py` **remains authoritative for Release 3**. New metadata fields are added to the Python dataclass. `build_fn` entries delegate to Rust pure functions where compute-bound (translator, geq emit, shape generators, parser). A future v084+ substrate BL — "Migrate effect-registry metadata authority to Rust" — owns the eventual move. **No two-registry split inside Release 3.** This avoids the migration-in-flight risk codex `18` flagged.

**Path scope note (added per codex `14`):** the path-handling rules below distinguish two cases:
- **Argv paths** (`-i <path>`, `-y <output_path>`): opaque to FFmpeg's filter-graph parser. Passed as separate argv elements via `asyncio.create_subprocess_exec`. **No escape needed.**
- **Filter-graph option-value paths** (`lut3d=file=...`, `subtitles=filename=...`, `ass=filename=...`, `movie=filename=...`): embedded inside `-vf` / `-filter_complex`. Parsed by FFmpeg's filter lexer. **Apply BL-499 `emit_filter_option_path` helper.**

The translator must NOT path-escape `-i` inputs. Only paths flowing into filter option values get the helper.

### Layer 2 — render-graph translator

Pattern proven in `poc-work/poc-0-render-graph/translate.py`. The Rust implementation (in `rust/stoat_ferret_core/src/render/`) walks per clip:

1. Per clip: build a named filter sub-chain starting with `[<idx>:v]trim=...,setpts=PTS-STARTPTS`.
2. For each effect on the clip, emit the effect filter via the builder, gated on `window`:
   - If `effect.timeline_T_capable`: append `:enable='between(t,start_s,end_s)'`.
   - Else: route through a split/trim/concat fallback (Rust composition primitive).
3. Apply the fps,settb normalisation pin at every segment boundary feeding xfade (BL-507 + the boundary rule lives here, not in ZoompanBuilder).
4. Compose segments via transitions list (xfade or other).
5. Terminate with `format=yuv420p`.

### Layer 3 — worker integration

`src/stoat_ferret/render/worker.py::build_command_for_job`:

1. Loop over ALL clips (not just `clips[0]`).
2. For each clip, fetch its `effects` array (already there in the DB).
3. Hand the clips + effects + transitions list to the Rust translator.
4. Receive back the filter_complex string + list of `-i` arguments.
5. Assemble the final command.

The existing `RenderJobResponse` schema does not change (the user sees the same job state). The internal render path goes from one-input to N-input.

## Proposed acceptance criteria

1. **Multi-clip render.** A project with N>1 clips renders all clips. SSIM at each clip's midpoint > 0.99 against the source clip. (Pattern: poc-0 measured 0.999999 for the 2-clip case.)
2. **Per-clip effects.** An effect persisted on a clip is reflected in the rendered output. For an effect with `timeline_T_capable=True` and a window, the effect is active only inside the window (verify via frame-extract pixel sampling).
3. **fps,settb normalisation.** Mixed-framerate inputs render without xfade timebase errors. Negative-control: removing the rule produces a 0-byte output (Verification-1 pattern).
4. **format=yuv420p terminal.** Output is Windows-Media-Foundation compatible. ffprobe asserts pix_fmt is yuv420p.
5. **Hygiene test.** A test that cross-checks `EffectDefinition.timeline_T_capable` against `ffmpeg -filters` output (the T flag). Fails if any builder declares timeline support its filter doesn't actually have.
6. **Render evidence.** The render job exposes `command_args`, `exit_code`, `stderr_tail`, `output_size_bytes` per `BL-DRAFT-bl506-render-evidence.md`.
7. **Integration test.** End-to-end test that POSTs a multi-clip project, renders it, and asserts clip attribution + effect presence. Uses real `GET /clips` shape, not handcrafted fixtures.

8. **OpenAPI freshness (per codex `18` Major Risk):** PR includes regenerated `gui/openapi.json` (via `uv run python -m scripts.export_openapi`) + `gui/src/generated/api-types.ts` (via `cd gui && npm run generate:types`). CI freshness checks pass.

9. **PyO3/stub workflow (per codex `18` Major Risk):** BL-505B introduces new Rust functions called from Python (translator). The PR:
   - Adds PyO3 bindings in the same feature.
   - Regenerates the stub via `cargo run --bin stub_gen`.
   - Updates `src/stoat_ferret_core/_core.pyi` **append-only** (never overwrites with the generated output).
   - Runs `uv run python scripts/verify_stubs.py` and that passes.

### Concept vs integration acceptance split (added per codex `12` / `14`)

PoC-0 demonstrated **concept acceptance** — a handcrafted JSON fixture shaped by T7c's source-map translated into a working FFmpeg command with SSIM-confirmed clip attribution. PoC-0 did NOT exercise a live `GET /clips` response from a running snf instance. For v083 sizing:

- **Concept acceptance (proven by PoC-0):** translator emits a deterministic filter graph from a clip+effects+transitions dataclass. The pattern works.
- **Integration acceptance (required for BL-505 ship):** the translator consumes a real `GET /clips` API response without ad-hoc shape adapters in tests. The schema must match end-to-end.

## Out of scope

- Generator-clip type rendering (clip_type=generator) — separate BL.
- Audio mixing graph at multi-track level — that's BL-517.
- Live preview (HLS) — separate concern.
- Variable-speed clips spanning a transition — edge case, separate BL.

## Decomposition

Per codex `07`'s recommendation, BL-505 splits into:

- **BL-505A — render preflight truthfulness.** Independent of the full rewrite. Adds a preflight check on `POST /render` that returns a warning or 422 when the persisted project state cannot be represented by the current worker. Stops the silent-success failure mode while the full rewrite is being built. Size: m.
- **BL-505B — render-graph translator (Rust).** Implements layers 1-2 above. Size: l.
- **BL-505C — worker integration.** Implements layer 3 above. Size: m.

Recommended sequence: A first (stops the silent failure mode in production); then B; then C.

## Unit test seeds

```python
# Translator concept test
def test_translator_emits_multi_input_filter_complex():
    fixture = {
        "fps": 30, "width": 640, "height": 360,
        "clips": [
            {"id": "a", "source_video_id": "v1", "clip_type": "file",
             "in_point": 0, "out_point": 150,
             "effects": [{"effect_type": "blur", "parameters": {"sigma": 2.0, "blur_type": "gaussian"},
                          "window": {"start_s": 1.0, "end_s": 3.0}}]},
            {"id": "b", "source_video_id": "v2", "clip_type": "file",
             "in_point": 0, "out_point": 150, "effects": []},
        ],
        "transitions": [{"from_clip": "a", "to_clip": "b", "kind": "xfade",
                         "duration_s": 1.0, "offset_s": 4.0}],
        "video_path_map": {"v1": "red.mp4", "v2": "blue.mp4"},
    }
    cmd = translate(fixture)
    assert cmd.count("-i") == 2
    assert "gblur=sigma=2.0:enable='between(t,1.0,3.0)'" in cmd
    assert "fps=30,settb=1/30" in cmd
    assert "xfade" in cmd
    assert cmd.endswith("format=yuv420p[out]")  # or similar
```

## Risks / open questions

- **PyO3 boundary cost.** Calling the Rust translator from Python adds a marshalling cost on every render. Probably negligible; verify on a 50-clip project.
- **The translator must reject N-input projects where N > some practical limit** (e.g. 100) to avoid pathological filter graphs.
- **Generator clip rendering** is out of scope but interacts with this BL — the schema must allow generators to be referenced even if the current translator branch only handles file clips.

## Evidence pointers

- `poc-work/poc-0-render-graph/notes.md` — full T4 writeup
- `poc-work/poc-0-render-graph/translate.py` — reference implementation
- `poc-work/poc-0-render-graph/fixture.json` — example input shape
- `poc-work/poc-0-render-graph/out.mp4` — verified render (9 s, 640×360, yuv420p, SSIM 0.999999 vs source)
- `poc-work/explores/T7c-render-pipeline-shape.md` — current snf source path map
- `poc-work/explores/T7a-ffmpeg-filter-capabilities.md` — timeline-T capability table

# Release 2 — Architecture

Release 2 adds capability without changing the Release 1 shape: Python/FastAPI orchestrates and serves; Rust pure functions do compute-bound work via PyO3; effects are registry entries with JSON-schema validation and AI hints; storage stays SQLite (metadata/audit) + JSON (projects/versions). This document describes the **four new subsystems** and how they slot in.

```
┌──────────────────────────────────────────────────────────────────────┐
│  Python / FastAPI (orchestration, validation, serving)               │
│   effects registry · render service · NEW: QC service · delivery svc │
└───────────────┬──────────────────────────────────────────────────────┘
                │ PyO3
┌───────────────┴──────────────────────────────────────────────────────┐
│  Rust core (pure functions)                                          │
│   filter builders · timeline math · render plan                      │
│   NEW: keyframe→expression compiler                                  │
│   NEW: QC measurement parsers (ebur128/astats/silencedetect output)  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Subsystem 1 — Keyframe → Expression compiler (Rust)

**Problem it solves:** Release 1 has a working expression engine (`Expr` AST → FFmpeg `expr` strings) but no way to author *time-varying parameter automation* from user-facing keyframes. Several Release 2 capabilities (volume/EQ/pan automation, variable speed, tone-frequency sweeps, keyframed opacity/scale) are the same problem: a curve over time compiled to an FFmpeg expression.

**Design:** a single Rust pure function and shared schema.

```rust
pub enum CurveKind { Hold, Linear, Exponential, EaseInOut /* bezier */ }

pub struct Keyframe { pub t: f64, pub value: f64, pub curve: CurveKind } // curve = interp INTO this kf

pub struct Automation { pub keyframes: Vec<Keyframe>, pub default: f64 }

/// Compile an automation envelope to an FFmpeg expression string in variable `t`.
/// Pure function — deterministic, no side effects.
pub fn compile_automation(a: &Automation) -> String;
```

- Output is a nested `if(lt(t,k1), <ramp>, if(lt(t,k2), <ramp>, …))` expression reusing the existing `Expr` machinery.
- Consumers inject the compiled string into the parameter position their filter expects: `volume='<expr>'`, `pan` weights, `drawtext:alpha='<expr>'`, `scale` with expression eval, `aevalsrc` frequency term, etc.
- **Section-aware automation:** markers (Subsystem 4) can be referenced as keyframe anchors so the level/tonal arc snaps to Induction/Deepening/Suggestion/Emergence boundaries.

**Tests:** proptest (never panics; monotonic-time invariants; value bounds), contract tests rendering a short clip and asserting the measured curve via the QC pass.

---

## Subsystem 2 — QC / Compliance verification pass (Python service + Rust parsers)

**Problem it solves:** the release's acceptance criteria (loudness, peak, clipping, silence, loop-seam, A/V sync, decode integrity, embedded metadata) must be *machine-verifiable*. snf's render pipeline is the right place to measure.

**Design:** a `QCService` that runs analysis passes over a rendered artifact and returns a structured report of assertions.

| Check | Mechanism | Asserts |
|-------|-----------|---------|
| Integrated loudness + LRA + true peak | `ebur128` / `loudnorm` (print JSON) | LUFS target, true-peak ceiling |
| Peak / clipping | `astats`, `volumedetect` | no clipped samples; headroom |
| Unintended silence / gaps | `silencedetect` | continuity (OC-2, OC-12) |
| Loop seam | boundary-sample comparison | seamless bed (OC-7) |
| Tone presence / evolution | `aspectralstats` | entrainment tones present & changing (OC-8) |
| Ducking | per-track level vs voice-activity gate | background recedes under voice (OC-9) |
| Section levels | per-region integrated LUFS | intensity arc ordering (OC-10) |
| Video defects | `blackdetect`, `freezedetect` | no unintended black/freeze |
| A/V sync | known-offset probe | frame-accurate sync (OC-13) |
| Decode integrity | `ffmpeg -v error -f null -` | plays start-to-finish (OC-17) |
| Embedded metadata / chapters | `ffprobe` | labels + identifying info (OC-16) |

- **Rust** parses the noisy FFmpeg stderr/JSON into typed measurements (pure functions, proptest-covered) — the same boundary used for render progress parsing in Release 1.
- **Python** orchestrates the passes, compares against targets (from the active delivery profile or an explicit assertion set), and emits a `QCReport { checks: [{id, measured, target, pass}], overall }`.
- The QC report is exposed via API and consumed by both the GUI (results panel) and the test layer (assertions). This is the bridge that makes outcomes testable.

---

## Subsystem 3 — Delivery profiles (Python)

**Problem it solves:** "produce every required format, normalized to target loudness, correctly labelled" (OC-11/15/16/17) is currently three unrelated features (export presets, loudnorm, metadata). A delivery profile fuses them and makes export *self-verifying*.

**Design:** a `DeliveryProfile` value object + batch export that validates against it.

```
DeliveryProfile {
  name, outputs: [{container, video_codec, audio_codec, ...}],
  loudness: { target_lufs, true_peak_ceiling_dbtp },
  metadata: { title, identifiers..., embed_chapters_from_markers: bool },
}
```

- Export produces each output, runs the QC pass against the profile's targets, and fails the deliverable if any assertion fails (exception flow A3/A5 — retained editable state, re-master, re-verify).
- Builds directly on Release 1 batch render + audio export; adds the loudness/metadata binding and the QC gate.

---

## Subsystem 4 — Markers / Regions model (Python + storage)

**Problem it solves:** the session structure (Induction→Deepening→Suggestion→Emergence) must be authorable, drive automation, and be embedded as chapters.

**Design:** named, ordered, typed regions on the project timeline, persisted with the project (and versioned like the rest of project state).

- Feed **section-aware automation** (Subsystem 1 keyframe anchors).
- Export to **chapter metadata** via `ffmetadata` (Subsystem 3).
- Provide the QC pass its per-section boundaries (OC-1, OC-10, OC-16).

---

## What does NOT change

- Timeline math (frame-accurate `Position`/`Duration`/`FrameRate`) — reused as-is.
- Effect registry, JSON-schema validation, AI hints — new effects follow the existing pattern.
- Render coordinator, encoder detection, job queue (asyncio + SQLite), WebSocket event push — extended, not replaced.
- Storage model — markers and delivery profiles persist with projects; QC reports persist alongside render job records.

## Boundaries explicitly NOT crossed (see roadmap "Out of scope")

No realtime capture, no DAW bus/submix graph, no bezier mask authoring, no Ambisonic/HRTF, no MOGRT engine, no live monitoring. These would change the paradigm and are deferred.

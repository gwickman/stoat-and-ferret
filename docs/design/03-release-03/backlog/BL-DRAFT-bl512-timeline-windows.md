# BL-DRAFT-bl512-timeline-windows

**Status:** drafted, not filed (REFRAMED per `02-review-1-response.md`)
**Supersedes / amends:** BL-512 (Time-window parameter on per-clip effects)
**Evidence:** `02-review-1-response.md`, `00-RISKS.md` R8, `poc-work/explores/T7a-ffmpeg-filter-capabilities.md`
**Why now:** the original BL-512 substantially duplicated existing work (`WindowSpec` from BL-446 v080 PR #581 already exists). The actual gap is two-part and must be reframed.

## Problem statement (reframed)

The original BL-512 proposed adding `enable_start_s`/`enable_end_s` to effect schemas. That work already shipped as `WindowSpec` with `start_s`/`end_s` at `src/stoat_ferret/api/schemas/effect.py:109` in v080 PR #581.

The actual gaps are:

1. **Renderer consumption** — `WindowSpec` is persisted on the effect record but never consumed by the worker (because BL-505 ignores per-clip effects entirely). Once BL-505 lands, the translator must read `effect.window` and emit `:enable='between(t,start,end)'` for filters that support timeline-T.
2. **Per-builder timeline-T capability flag** — `enable=` only works on filters with FFmpeg's `T` flag. Per T7a (corrected 2026-06-15 per codex `14`), these include `hue`, `drawtext`, `curves`, `vignette`, `gblur`, `colorchannelmixer`, `volume`, `geq`, `lut3d`, `overlay`. These do NOT: `scale`, `format`, `fps`, `settb`, **`zoompan`**, `subtitles`, `ass`, `amix`, `sidechaincompress`, `xfade`. Wrapping a non-T filter with `enable=` either fails or is semantically wrong. Note: `zoompan` has its own internal expressions (`z`, `x`, `y`, `d`, `zoom`, `on`, `in`) — that is NOT the same contract as accepting `enable=`. Verified via `ffmpeg -filters | grep zoompan` returning `.. zoompan`.

## Proposed acceptance criteria

1. **EffectDefinition.timeline_T_capable: bool** field added per BL-DRAFT-bl505 metadata schema.
2. **Renderer dispatch:** when an effect has a window AND the effect is timeline_T_capable, emit `:enable='between(t,start_s,end_s)'`. Otherwise, route through split/trim/concat fallback at the graph level.
3. **Hygiene test:** cross-check the `timeline_T_capable` flag against `ffmpeg -filters | grep <filter>` T flag. Fails if any builder declares a capability its filter doesn't have.
4. **Test the fallback:** an effect with a window on a non-T filter (e.g. `scale`) renders correctly via the split/trim/concat path. Compare frames at t inside and outside the window.
5. **Backward compatibility:** the existing `WindowSpec` schema is unchanged. This BL is purely renderer-side.

## Out of scope

- New schema fields. WindowSpec already exists.
- The split/trim/concat fallback implementation in the Rust composition graph (overlaps with BL-505).

## Dependencies

- **BL-505** must land first (otherwise WindowSpec is unread).
- BL-DRAFT-bl505-render-graph carries the EffectDefinition metadata addition that BL-512 consumes.

## Unit test seeds

```python
def test_timeline_T_enable_on_hue():
    # hue has T flag, so enable= should land directly on the filter
    e = hue_effect(H="2*PI*t/3", window=WindowSpec(start_s=1.0, end_s=3.0))
    s = build_filter_string(e)
    assert ":enable='between(t,1.0,3.0)'" in s

def test_non_T_window_uses_split_trim_concat_on_zoompan():
    # zoompan lacks T flag; window must produce a graph-level fallback
    e = zoompan_effect(z="zoom+0.001", d=1, window=WindowSpec(start_s=1.0, end_s=3.0))
    plan = build_render_plan([e])
    assert "split" in plan.filter_graph
    assert "trim=start=1.0:end=3.0" in plan.filter_graph
    assert "concat" in plan.filter_graph
    assert ":enable=" not in plan.filter_graph  # must NOT use enable= on non-T filter
```

## Risks

- The split/trim/concat fallback for non-T filters increases graph complexity quadratically with the number of windowed effects per clip. Add a guard that warns if a clip has > N windowed effects on non-T filters.

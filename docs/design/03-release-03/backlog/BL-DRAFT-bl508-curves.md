# BL-DRAFT-bl508-curves

**Status:** drafted, not filed
**Supersedes / amends:** BL-508 (CurvesBuilder — colour curves preset effect)
**Evidence:** `poc-work/explores/T7a-ffmpeg-filter-capabilities.md` (curves filter has T flag, takes expressions and presets)
**Why now:** mechanical single-filter wrap; bundles into v083 small-builders wave.

## Problem statement

snf lacks a colour-grading builder. Users routinely want a one-click "cinematic teal-and-orange" or "warm vintage" colour preset. FFmpeg's `curves` filter supports both presets (`preset=vintage|cross_process|...`) and per-channel knee-string expressions.

## Proposed acceptance criteria

1. **CurvesBuilder** registered with parameter schema accepting:
   - `preset: Literal["none","color_negative","cross_process","darker","increase_contrast","lighter","linear_contrast","medium_contrast","negative","strong_contrast","vintage"]` — wraps `curves=preset=<x>`.
   - `master: KneeString | None`, `red: KneeString | None`, `green: KneeString | None`, `blue: KneeString | None`, `all: KneeString | None` — per-channel knee strings like `"0/0 0.5/0.4 1/1"`. **NOT generic time expressions** (per codex `14`); typed as `KneeString` with its own filter-specific validator (sequence of `x/y` pairs, monotonic `x` in [0,1], `y` in [0,1]). Single-quote-wrap on emit (`red='0/0 0.5/0.4 1/1'`) because the value contains whitespace.
2. **Emit policy.** When `preset` is set, emit `curves=preset=<preset>`. Otherwise emit per-channel knee strings.
3. **Static-only for v083.** Per-channel expressions in the knee form, no time-dependent expression (curves has timeline-T capability but per-knee animation is out of scope).
4. Three contract tests: preset rendering, custom knee rendering, no-op (preset=none with no per-channel) error.
5. **Effect registry** declares `timeline_T_capable=True, requires_path_escape=False, stream_kind="video"` per BL-DRAFT-bl505 metadata schema.

## Out of scope

- Time-animated curves.
- LUT-based grading (BL-499 ColorLutBuilder covers that).
- Per-shot grading sidecar files (.cube via lut3d).

## Unit test seeds

```rust
#[test]
fn curves_preset_vintage() {
    let f = CurvesBuilder::with_preset("vintage").build().unwrap();
    assert_eq!(f.to_filter_string(), "curves=preset=vintage");
}

#[test]
fn curves_custom_knee() {
    let f = CurvesBuilder::new()
        .red("0/0 0.5/0.4 1/1")
        .build().unwrap();
    assert_eq!(f.to_filter_string(), "curves=red='0/0 0.5/0.4 1/1'");
}
```

## Dependencies

- BL-505 render-graph rewrite (effects consumed per clip).
- BL-512 timeline-T capability flag.

## Risks / open questions

- The knee string format (`x/y x/y ...`) needs to be wrapped in single quotes when passed through `-vf`; BL-DRAFT-bl510's escape policy applies.

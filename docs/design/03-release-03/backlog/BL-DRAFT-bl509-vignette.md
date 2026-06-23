# BL-DRAFT-bl509-vignette

**Status:** drafted, not filed
**Supersedes / amends:** BL-509 (VignetteBuilder — cinematic corner darkening)
**Evidence:** `poc-work/explores/T7a-ffmpeg-filter-capabilities.md` (vignette filter: T flag, S flag, takes expression args)
**Why now:** mechanical single-filter wrap; bundles into v083 small-builders wave.

## Problem statement

snf lacks a vignette builder. Common cinematic effect that darkens frame corners. FFmpeg `vignette` filter is well-supported (timeline T, sliced threads).

## Proposed acceptance criteria

1. **VignetteBuilder** registered with parameter schema:
   - `angle: float` (default PI/5, range 0..PI/2)
   - `x0: str | int` (default expression `"w/2"`; int → emit as int; str → validate as FFmpeg expression and single-quote-wrap) — corrected per codex `14`: the default IS an expression, not an int
   - `y0: str | int` (default expression `"h/2"`; same treatment)
   - `mode: Literal["forward","backward"]` (default `forward`)
   - `eval: Literal["init","frame"]` (default `init` — animated only if needed)
   - **v1 alternative (simpler):** expose `position: Literal["centre","top_left","top_right","bottom_left","bottom_right"]` plus numeric `x_offset`/`y_offset`. Resolves to the appropriate expression string under the hood; avoids exposing FFmpeg-expression strings as a user-facing surface for v1.
2. **Emit:** `vignette=angle=<a>:x0=<x>:y0=<y>:mode=<m>:eval=<e>`.
3. **Three contract tests:** default render produces darker corners than centre; backward mode produces inverse; init vs frame mode renders differ when angle is automated.
4. **Effect registry** declares `timeline_T_capable=True, stream_kind="video"`.

## Out of scope

- Soft-edged custom-shape vignettes (use `geq` + `overlay` instead).
- Per-corner asymmetric darkening.

## Unit test seeds

```rust
#[test]
fn vignette_default() {
    let f = VignetteBuilder::new().build().unwrap();
    assert!(f.to_filter_string().contains("vignette="));
    assert!(f.to_filter_string().contains(":mode=forward"));
}
```

## Dependencies

- BL-505, BL-512.

## Risks

- The expression option case (e.g. animated `angle`) uses the same single-quote-wrap policy as `hue` per BL-DRAFT-bl510.

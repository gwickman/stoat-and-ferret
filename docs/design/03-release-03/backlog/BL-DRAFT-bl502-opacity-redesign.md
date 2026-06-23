# BL-DRAFT-bl502-opacity-redesign

**Status:** drafted, not filed
**Supersedes / amends:** BL-502 (currently "open — escape landed, FFmpeg discharge unverified")
**Evidence:** `poc-work/poc-4-escape-policy/retest-native/`, `09-action-plan-2-execution-results.md` Section "Side-effect finding", `10-codex-response.md` Section 4
**Why now:** BL-502 is more broken than "escape unverified" — the v082 OpacityBuilder emits a filter graph that FAILS at runtime on FFmpeg 8.0.1 regardless of escape policy. The deferred FFmpeg-discharge would have caught this. A different filter strategy is needed.

## Problem statement

The v082 OpacityBuilder emits:

```
format=rgba,colorchannelmixer=aa='if(lt(t,1),0.5,1.0)':eval=frame
```

This fails on FFmpeg 8.0.1 with:

```
[Parsed_colorchannelmixer_1] [Eval] Undefined constant or missing '(' in 't,1),0.5,1.0)'
Unable to parse option value "if(lt(t,1),0.5,1.0)"
Error applying option 'aa' to filter 'colorchannelmixer': Invalid argument
```

Tested with single-quote-wrap, with `\,` comma-escape, and with both combined. All fail with the same eval-engine error. `ffmpeg -h filter=colorchannelmixer` confirms `aa` is `<double>`, not an expression slot; `eval=frame` doesn't change this.

The v082 `escape_for_filter` helper at `rust/stoat_ferret_core/src/ffmpeg/video.rs:23` makes the filter string LOOK escaped correctly, but the underlying filter does not accept expressions on `aa`.

## Candidate fix

`geq` with the alpha-output channel. Codex `10` verified:

```
format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(T,1),128,255)'  -- WORKS (uppercase T)
format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='if(lt(t,1),128,255)'  -- FAILS (lowercase t)
```

So the time variable inside `geq` is uppercase `T`, not lowercase `t`. This is different from `hue`'s `H='...t...'`, scale's `'...t...':eval=frame`, and the `enable=` clause — all of which use lowercase `t`.

## Proposed acceptance criteria

Three proofs required (none alone is sufficient):

1. **Parse proof.** `format=rgba,geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='<user-expr-translated-to-uppercase-T>'` parses on FFmpeg 8.0.1 with exit 0.
2. **Alpha-changes-over-time proof.** Render an animated-alpha clip for 5 s. Extract frames at t=0.5, t=2.5, t=4.5. Assert alpha plane values differ across the three timestamps (e.g. via `ffmpeg -i out.png -vf extractplanes=a stats`).
3. **Composition survival proof.** Render the animated-alpha layer overlaid on a known background (e.g. `color=red`) using `overlay`, then flatten to `format=yuv420p`. Extract frames at t=0.5 and t=4.5. Assert the visible pixel colour at the center differs between the two timestamps (proving the user actually sees the fade).

**Important:** proof 3 is non-negotiable. `format=yuv420p` DROPS the alpha channel. A redesign that keeps alpha animating internally but loses it at the final flatten produces no user-visible effect.

## Dependency on BL-505 ordering (added per codex `14`)

T1's composition-survival proof established that animated alpha is only user-visible if the render graph composites through an `overlay` (alpha-aware) stage BEFORE the final `format=yuv420p` flatten (yuv420p drops alpha by definition). This is not just an OpacityBuilder concern; it is a **render-graph ordering requirement**.

Concretely:
- ✓ `[bg][fg with animated alpha]overlay,format=yuv420p` — works (T1 verified center pixel transitions blue→red across the fade).
- ✗ `[fg with animated alpha]format=yuv420p[flatfg];[bg][flatfg]overlay` — animated alpha lost at the flatten before overlay sees it.

BL-505 must understand "this clip wants its alpha preserved into composition" vs "this clip is opaque, flatten anywhere". Without that distinction, OpacityBuilder's geq output silently disappears at the wrong point in the graph.

## Out of scope

- Replacing `escape_for_filter` (call-sites in Blur / Scale still depend on it; only OpacityBuilder needs to switch).
- The other 33 effect builders.
- Re-architecting the value-kind escape policy (separate BL-DRAFT under value-kind-escaping work; see Track F of `08`).

## Unit test seeds

```rust
// rust/stoat_ferret_core/src/ffmpeg/video.rs
#[test]
fn opacity_builder_emits_geq_with_uppercase_t() {
    let b = OpacityBuilder::new()
        .with_automation(Automation::linear_t_to(0.5, 1.0, /*start=*/0.0, /*end=*/1.0));
    let f = b.build().unwrap();
    let s = f.to_filter_string();
    assert!(s.starts_with("format=rgba,geq="));
    assert!(s.contains(":a='"));
    // user expression contains lowercase t; emit converts to T
    assert!(s.contains("lt(T,") || s.contains("lt(T\\,"));
    assert!(!s.contains("colorchannelmixer"));
}
```

## Risks / open questions

- `geq` performance vs `colorchannelmixer` — `geq` evaluates an expression per pixel per frame. May be slower for non-animated opacity. Solution: keep static-opacity path on `colorchannelmixer=aa=<float>` (which works); only animated opacity uses `geq`.
- Whether other builders that currently route through `colorchannelmixer` have the same problem. Need an audit (Track 7b of `11`).

## Evidence pointers

- `poc-work/poc-4-escape-policy/retest-native/test_lut3d.py` (also tests colorchannelmixer)
- `09-action-plan-2-execution-results.md` Section "Side-effect finding"
- `10-codex-response.md` Section 4 — codex's verified `geq` with uppercase T

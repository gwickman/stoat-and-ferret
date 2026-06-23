# BL-DRAFT-bl507-zoompan

**Status:** drafted, not filed
**Supersedes / amends:** BL-507 (currently "ZoompanBuilder — Ken Burns slow-zoom / pan motion graphics effect")
**Evidence:** `poc-work/verification-1-zoompan-xfade/`, codex `07` Section 7
**Why now:** Verification-1 proved the timebase pin is mandatory (not optional). The current AC does not say so. The graph-boundary normalisation rule is separately the responsibility of BL-505.

## Problem statement

Verification-1 ran two cases:

- WITH `fps=30,settb=1/30` after zoompan: output 16072 bytes, exactly 9.000000 seconds, exit 0.
- WITHOUT the pin: output 0 bytes, exit -22 "Invalid argument".

Without the pin, zoompan defaults to 25 fps and a timebase mismatch with the downstream xfade causes the encoder to never see a valid frame.

## Proposed acceptance criteria

1. **ZoompanBuilder emits BOTH `fps=<project_fps>` AND `settb=1/<project_fps>` after the zoompan filter.** Not just `fps`. Pin in the format string and in the unit test.
2. **Scope:** ZoompanBuilder is for fixed-canvas pan/zoom inside a window. It is NOT a duplicate of the existing scale automation at `src/stoat_ferret/effects/definitions.py:2032` (which changes stream dimensions for slow-zoom Ken Burns). The BL description must state the non-overlap explicitly.
3. **Negative-control contract test.** A test that asserts the emitted graph WITHOUT the pin fails to render (proves the pin is load-bearing).
4. **Graph-boundary normalisation lives in BL-505, not BL-507.** Every named chain feeding xfade must have compatible fps and tbn, even when zoompan is not in the chain. BL-507 owns its filter-local pin; BL-505 owns the cross-segment rule.
5. **zoompan is NOT timeline-T capable** (verified codex `14`: `ffmpeg -filters | grep zoompan` returns `.. zoompan` with no T flag). The filter has its own internal `z/x/y/d/on/in/iw/ih/zoom` expressions, but that is NOT the same contract as FFmpeg timeline `enable=` support. A windowed zoompan effect must go through BL-512's graph-level split/trim/concat fallback, not a filter-level `enable=` clause.

## Out of scope

- Cross-segment normalisation (BL-505).
- The other effect builders that may have similar timebase issues (audit separately).

## Unit test seeds

```rust
#[test]
fn zoompan_emits_fps_and_settb() {
    let b = ZoompanBuilder::new(/*pan params*/);
    let s = b.build().unwrap().to_filter_string();
    assert!(s.contains("fps=30"));
    assert!(s.contains("settb=1/30"));
}
#[test]
fn zoompan_without_pin_fails_xfade_negative_control() {
    // verifies the pin is load-bearing
    let s = "[0:v]zoompan=z='zoom+0.001':d=1:s=1280x720[a];[a][1:v]xfade=...";
    assert!(ffmpeg_dry_run(s).is_err());
}
```

## Evidence pointers

- `poc-work/verification-1-zoompan-xfade/zoompan-xfade-out.mp4` (positive, 9 s)
- `poc-work/verification-1-zoompan-xfade/zoompan-xfade-NEGATIVE.mp4` (0 bytes, control)
- `poc-work/verification-1-zoompan-xfade/negative-control.log` (stderr)

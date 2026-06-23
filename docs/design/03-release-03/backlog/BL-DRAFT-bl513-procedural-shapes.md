# BL-DRAFT-bl513-procedural-shapes

**Status:** drafted, not filed
**Supersedes / amends:** BL-513 (currently "Procedural shape builders — Spiral, RadialBurst, Checkerboard, ConcentricRings")
**Evidence:** `poc-work/poc-5-rust-image-spike/`, codex `05` Section "PoC-5 performance conclusion should be narrowed"
**Why now:** the dependency choice is now verified (image = "0.25") but the perf framing in poc-results.md needs sharpening to distinguish static vs animated regeneration.

## Problem statement

PoC-5 generated a 720×720 spiral via the Rust `image = "0.25"` crate in 8.9 ms. SSIM 1.0 vs the existing Python PIL implementation. The crate has no PyO3 binding conflicts with snf's existing scaffolding.

## Proposed acceptance criteria

1. **Dependency:** add `image = "0.25"` (or current stable) to `rust/stoat_ferret_core/Cargo.toml`.
2. **Four shape generators implemented:** Spiral, RadialBurst, Checkerboard, ConcentricRings. Each exposes a Python-callable constructor with parameters appropriate for the shape (e.g. Spiral takes turn_count + thickness; ConcentricRings takes ring count + spacing).
3. **Generation budget:** ≤ 100 ms for 1080×1080 RGBA on the dev workstation. (PoC measured 8.9 ms for 720×720; linear scaling predicts ~20 ms for 1080×1080.)
4. **Output format:** RGBA PNG. Files written to a snf-managed temp/asset path (depends on how BL-511 image-as-clip handles asset paths).
5. **Contract tests:** for each shape, render once with fixed params, **hash the decoded RGBA pixel buffer** (NOT the file bytes — per codex `14`, PNG encoders can vary in compression/metadata without changing pixel content). Assert the hash matches a pinned reference. Defends against accidental math regressions.

## Out of scope

- **Per-frame regeneration.** This BL covers STATIC asset generation. 8.9 ms per frame at 30 fps is 27 % of the real-time budget — not negligible. Per-frame regeneration would be a different shape (BL-514 territory) and needs its own perf budget.
- Generic equation-driven shape generator — that is BL-514.
- Animated parameter envelopes (rotating spiral over time, etc.) — possible follow-up but not in scope.

## Unit test seeds

```rust
#[test]
fn spiral_720x720_under_50ms() {
    let t = std::time::Instant::now();
    let img = Spiral::new(/*params*/).render(720, 720);
    assert!(t.elapsed().as_millis() < 50);
    assert_eq!(img.width(), 720);
    assert_eq!(img.height(), 720);
}
#[test]
fn spiral_bytes_match_reference() {
    let img = Spiral::new(/*fixed-params*/).render(720, 720);
    let mut bytes = vec![];
    img.write_to(&mut std::io::Cursor::new(&mut bytes), image::ImageFormat::Png).unwrap();
    let hash = sha256(&bytes);
    assert_eq!(hash, "<pinned-reference-hash>");
}
```

## Risks / open questions

- Where do generated assets live? Bundled with snf? Generated per-project into a `working/` folder? This couples to BL-511 (image-as-clip) and BL-515 (user-asset library).
- Whether the four shapes cover 80% of user wellness/hypno use cases — codex `07` flagged this is more of a product call than a technical one.

## Evidence pointers

- `poc-work/poc-5-rust-image-spike/spiral-rust.png` (Rust output)
- `poc-work/poc-5-rust-image-spike/python-ref.png` (Python PIL reference)
- `poc-work/poc-5-rust-image-spike/notes.md` (SSIM measurement)

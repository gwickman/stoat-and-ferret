# BL-DRAFT-bl519-burned-subtitles

**Status:** drafted, not filed
**Supersedes / amends:** BL-519 (Subtitle support — burn in subtitles from SRT and ASS sidecar files; v1 scope)
**Evidence:** Verification-2 confirmed libass is present; T2 verified `subtitles=filename=<path>` escape policy.
**Why now:** for distribution platforms that want hard-burned subtitles (broadcast, social-media short-form), this is a routine need.

## V1 scope (per codex `14` + `16`)

**SRT and ASS sidecar files only.** VTT is a candidate future format but not verified in this PoC chain — see the "Future verification" section below.

## Problem statement

snf can't burn-in subtitles from a sidecar `.srt` or `.ass` file. FFmpeg's `subtitles` and `ass` filters are both available (Verification-2 confirmed libass present), but no builder wraps them.

## Proposed acceptance criteria

1. **BurnedSubtitleBuilder** registered with parameters:
   - `source_asset_id: UUID` (referencing an SRT or ASS asset from BL-515) OR `inline_text: str` (small overlays).
   - `style: dict | None` — optional `force_style` overrides for ASS rendering (`Fontname`, `Fontsize`, `PrimaryColour`, `Outline`, etc.).
2. **Emit:**
   - For SRT: `subtitles=filename=<escaped-path>[:force_style=...]`.
   - For ASS: `ass=filename=<escaped-path>` (ASS does not honour force_style; styles are inline).
3. **Path escape:** apply BL-499 policy — `filename='<colon-escaped-forward-slash-path>'`.
4. **Style escape:** `force_style` is a comma-separated KEY=VALUE list. Use a force-style-specific escape (different from path escape). Document the per-filter rule.
5. **CI bundle guard:** add a test that asserts `subtitles` and `ass` filters are listed in `ffmpeg -filters` output against the bundled FFmpeg. Prevents future "lite" bundle regressions.
6. **Contract test:** burn a 5 s SRT (3 entries) onto a `color=blue` test clip; extract frames at each entry's midpoint; assert text presence (OCR or pixel-difference).
7. **`force_style` escape contract test (added per codex `14`):** `force_style` is a comma-delimited `KEY=VALUE` list embedded inside a filter option. Promote this from a risk note to an AC. Test: render with `force_style=Fontsize=32,PrimaryColour=&Hffffff&` wrapped in single quotes (`:force_style='Fontsize=32,PrimaryColour=&Hffffff&'`); assert exit 0 and visible style change in the output frame.

## Out of scope

- Soft subtitles (mov_text track in mp4 container) — that's BL-520.
- Subtitle-file format conversion (SRT → ASS in-place). Use ffmpeg's subtitle muxer separately.
- Bitmap-format subtitles (PGS, DVB).

## Unit test seeds

```rust
#[test]
fn burned_subtitle_srt_path_escape() {
    let f = BurnedSubtitleBuilder::from_path(r"C:\Users\foo\bar.srt").build().unwrap();
    let s = f.to_filter_string();
    assert!(s.starts_with("subtitles=filename='C\\:/Users/foo/bar.srt'"));
}

#[test]
fn burned_subtitle_with_force_style() {
    let f = BurnedSubtitleBuilder::from_path(r"/abs/p.srt")
        .force_style("Fontsize", "32")
        .force_style("PrimaryColour", "&Hffffff&")
        .build().unwrap();
    let s = f.to_filter_string();
    assert!(s.contains(":force_style="));
}
```

## Dependencies

- BL-515 asset library.
- BL-499 escape policy (path escape).

## Risks

- ~~`force_style` escape~~ — promoted to AC #7 (above) per codex `14`.
- Font availability on the host — if a subtitle references a font not installed, libass may silently substitute. CI test should pin the default font.

## Future verification (deferred — not v1)

**VTT format support.** WebVTT (`.vtt`) is a candidate addition. Before promising VTT, a verification pass must confirm:
- FFmpeg's libass path correctly demuxes VTT in the bundled build.
- The escape policy (`subtitles=filename='C\:/path/file.vtt'`) renders without parse errors.
- Cue settings and inline styling round-trip cleanly through libass rendering.

This work belongs in a follow-up BL filed for v084 or later.

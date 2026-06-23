# BL-DRAFT-bl511-image-as-clip

**Status:** drafted, not filed
**Supersedes / amends:** BL-511 (Image-as-clip support, clip_type=image)
**Evidence:** `poc-work/explores/T7c-render-pipeline-shape.md` (current clip_type is `file|generator`; need third option)
**Why now:** wellness/hypnotherapy showcase needed static images as overlays; current snf has no path.

## Problem statement

snf supports `clip_type=file` (video files) and `clip_type=generator` (lavfi sources like gradient, noise). A static PNG (logo, hypnotherapy spiral, branded overlay) cannot be a clip today — must be wrapped in an external video transcode first.

## Proposed acceptance criteria

1. **Schema:** add `clip_type=image` to the existing `Literal["file","generator"]` at `src/stoat_ferret/api/schemas/clip.py`.
2. **Persistence:** clips of type `image` store `source_asset_id` (NOT `source_image_id` — the asset library at BL-515 uses one polymorphic asset record with `kind=image|audio|subtitle|font|lut`, so a single `source_asset_id` field reads cleaner than per-kind fields). Asset records resolved by the renderer.
3. **Render path:** the BL-505 translator emits `-loop 1 -i <image_path>` for image clips. Apply effects (overlay, scale, crop) per existing per-clip-effects chain. Trim by `timeline_end - timeline_start` to get the desired duration.
4. **Duration:** image clips must have a `timeline_end` — no infinite loop renders.
5. **Format:** support PNG, JPEG. Reject TIFF, HEIC (FFmpeg may not have demuxers for all builds).
6. **Effect compatibility:** image clips can have all the same per-clip effects that file clips have (blur, scale, opacity, hue, etc.). Audio effects on image clips are no-ops.
7. **Contract test:** image clip + animated opacity (via BL-DRAFT-bl502 geq path) fades in and out cleanly when composed against a file-clip background.

## Out of scope

- Image sequences (e.g. PNG-per-frame). That's the `concat` demuxer pattern, separate BL.
- Animated GIF — needs different demuxer flags.

## Unit test seeds

```python
def test_image_clip_renders_with_duration():
    proj = make_project()
    img = upload_image_asset("logo.png")
    clip = create_clip(proj, clip_type="image", source_asset_id=img.id,
                       timeline_position=0, timeline_end=3.0)
    out = render(proj)
    assert ffprobe_duration(out) == pytest.approx(3.0, abs=0.1)
```

## Dependencies

- **BL-505** render-graph (per-clip processing must exist).
- **BL-515** asset library (image storage + retrieval).
- **BL-DRAFT-bl502** if animated alpha is needed on image clips.

## Risks

- ~~PNG path-escape through the BL-499 helper.~~ **Corrected 2026-06-15 per codex `14`:** image clips load via `-loop 1 -i <image_path>`, which is a subprocess argv element — NOT a filter-graph option. Argv paths are opaque to FFmpeg's filter parser, so no path-escape is needed. BL-499's `emit_filter_option_path` applies only to paths embedded INSIDE filter option strings (lut3d/subtitles/ass/movie filename), not to `-i` arguments.

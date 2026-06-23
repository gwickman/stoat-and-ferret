# BL-DRAFT-bl520-soft-subtitles

**Status:** drafted, not filed
**Supersedes / amends:** BL-520 (Soft subtitles — embed user-toggleable subtitle track in output MP4)
**Evidence:** modern distribution (YouTube, Vimeo, broadcast STB) consumes soft subtitles for accessibility; hard-burn loses that toggle.
**Why now:** pairs naturally with BL-519; same SRT/VTT source asset; different output path.

## Problem statement

snf can render burned subtitles (BL-519 once it lands) but cannot embed an MP4-native soft subtitle track that players display/hide on user toggle. Output MP4s are inaccessible without text.

## Proposed acceptance criteria

1. **Output-level option** placed inside the existing serialised `render_plan.settings` block (per codex `18` Major Risk: `CreateRenderRequest` uses `model_config = ConfigDict(extra="forbid")` — verified — so new render-time options go into `render_plan.settings`, NOT new top-level request fields). A new `RenderPlanSettings` Pydantic model parses the JSON and validates `soft_subtitles: list[SoftSubtitleSpec]` where:
   - `source_asset_id: UUID` (SRT/ASS — VTT deferred per BL-519)
   - `language: str` (BCP-47 input, e.g. `"en"`, `"es-ES"`, `"zh-Hant"`)
   - `is_default: bool` (default false; first track defaults true if any present)
2. **BCP-47 → ISO-639 mapping (added per codex `14`):** snf accepts BCP-47 language tags on the input but FFmpeg's mp4 muxer writes ISO-639-2/B 3-letter codes into the container metadata (`eng`, `spa`, `zho`). The renderer MUST translate at output time:
   - `"en"` → `eng`, `"es-ES"` → `spa`, `"zh-Hant"` → `zho`, etc.
   - Use a vetted mapping table (e.g. `babel`'s language-data, or a small hand-pinned dict for the v083-supported set).
   - For unsupported BCP-47 tags, reject at API boundary with a clear 422 listing the supported set.
3. **Renderer integration:** for each soft subtitle, add `-i <subtitle_path>` (subprocess argv, no escape — per codex `14`'s argv-vs-filter-option distinction) and `-c:s mov_text` plus `-metadata:s:s:N language=<iso639>` and `-disposition:s:N default` if `is_default`.
4. **Container constraint:** mov_text only works in mp4. For other containers, route the subtitle through a converted codec (`srt` for matroska, etc.) or reject with clear error.
5. **Path handling (corrected per codex `16`):** subtitle source paths are passed as subprocess argv inputs (`-i <path>`). They do NOT flow through the BL-499 filter-option escape policy. Apply standard asset-root and path-traversal validation from BL-515 (which already validates uploaded asset paths); no FFmpeg filter-graph escape is applied here.
6. **Contract test:** render with 2 soft subtitle tracks (en + es); ffprobe asserts 2 subtitle streams with the correct language metadata.

## Out of scope

- Live-stitched subtitle editing within snf's effect chain (you don't author subs — you reference an asset).
- Subtitle-OCR from burned-in source (different feature entirely).
- HLS / DASH manifest-based subtitle delivery (different output path).

## Unit test seeds

```python
def test_two_soft_subtitle_tracks_mp4():
    # BCP-47 input ("en", "es") → ISO-639-2/B output in mp4 metadata ("eng", "spa")
    plan = {
        "settings": {"output_format": "mp4"},
        "soft_subtitles": [
            {"source_asset_id": en_srt.id, "language": "en", "is_default": True},
            {"source_asset_id": es_srt.id, "language": "es", "is_default": False},
        ],
    }
    job = submit_render(plan)
    wait(job)
    probe = ffprobe_streams(job.output_path)
    sub_streams = [s for s in probe if s["codec_type"] == "subtitle"]
    assert len(sub_streams) == 2
    assert sub_streams[0]["tags"]["language"] == "eng"  # BCP-47 "en" → ISO-639 "eng"
    assert sub_streams[1]["tags"]["language"] == "spa"  # BCP-47 "es" → ISO-639 "spa"
    assert sub_streams[0]["disposition"]["default"] == 1

def test_bcp47_iso639_mapping_unknown_rejected():
    plan = {
        "settings": {"output_format": "mp4"},
        "soft_subtitles": [{"source_asset_id": x.id, "language": "xx-INVALID", "is_default": True}],
    }
    r = client.post("/render", json=plan)
    assert r.status_code == 422
    assert "language" in r.json()["detail"]
```

## Dependencies

- BL-515 asset library.
- BL-505 render-graph (adding additional `-i` inputs requires multi-input awareness).

## Risks

- `mov_text` encoder only handles plain text. ASS-rich-styled subtitles flatten to plain text when written to mp4. Document this.
- Player support varies — VLC honours `default` disposition reliably; web players may not.

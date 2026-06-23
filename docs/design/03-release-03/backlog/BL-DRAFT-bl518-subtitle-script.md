# BL-DRAFT-bl518-subtitle-script

**Status:** drafted, not filed
**Supersedes / amends:** BL-518 (Subtitle helper — burned-in text overlays from a script)
**Evidence:** wellness/hypnotherapy showcase had timed-caption needs; current workflow requires hand-built `drawtext` per caption.
**Why now:** mechanical wrap over existing `drawtext` primitives; bundles with v083 wishlist wave.

## Problem statement

Users frequently want N timed captions ("affirmation 1 at t=0, affirmation 2 at t=4, ..."). Today this requires manually composing N `drawtext` filters with `enable='between(t,start,end)'` clauses. Tedious and error-prone.

## Proposed acceptance criteria

1. **SubtitleScriptBuilder** — single effect that takes a list of `(start_s, end_s, text)` tuples and emits N `drawtext` filters chained.
2. **Schema:** `entries: list[ScriptEntry]` where `ScriptEntry = {start_s: float, end_s: float, text: str, position: Literal["bottom","top","center"], font_size: int, font_color: str}`.
3. **Defaults:** position=bottom, font_size=24, font_color=white, optional `font_file` for custom typography.
4. **Emit:** a comma-separated chain of `drawtext=fontfile=...:fontsize=...:fontcolor=...:text='<escaped>':x=...:y=...:enable='between(t,s,e)'` filters.
5. **Text escape:** use existing `escape_drawtext` helper (T7b confirmed); wrap the text value in single quotes per BL-DRAFT-bl510 policy.
6. **Contract test:** render a 10 s clip with 3 captions at t=0-2, 3-5, 6-8; extract frames at each midpoint; assert each frame has the expected text via OCR or pixel-difference probe.

## Out of scope

- ASS-format styling (use BL-519 for `.ass` sidecar sources).
- Animated transitions between captions (fade-in/out — could be a separate enhancement).
- Internationalisation (RTL languages, complex scripts beyond what drawtext+fontconfig already handles).

## Unit test seeds

```python
def test_subtitle_script_chains_drawtext_per_entry():
    spec = SubtitleScriptSpec(entries=[
        ScriptEntry(start_s=0.0, end_s=2.0, text="Hello", position="bottom"),
        ScriptEntry(start_s=3.0, end_s=5.0, text="World", position="bottom"),
    ])
    s = build_filter_string(spec)
    assert s.count("drawtext=") == 2
    assert "enable='between(t,0.0,2.0)'" in s
    assert "enable='between(t,3.0,5.0)'" in s
    assert "text='Hello'" in s
    assert "text='World'" in s
```

## Dependencies

- BL-505 (per-clip effects consumed) — the load-bearing dependency.
- BL-512 — **only for the per-builder timeline-T flag declaration** (drawtext IS T-capable, so this BL does NOT need the non-T split/trim/concat fallback machinery). Per codex `14`: drawtext+enable= is sufficient for simple timed captions; no graph-level gating needed for this builder specifically.
- DrawtextBuilder text-escape helper already exists.

## Risks

- Font availability — `drawtext=fontfile=...` needs a real font path. If unset, FFmpeg falls back to fontconfig; on Windows this may warn or fail. Bundle a default font as an asset (BL-515 dependency).

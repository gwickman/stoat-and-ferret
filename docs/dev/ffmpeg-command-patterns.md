# FFmpeg Command Construction Patterns

Reference for the invariants that govern all FFmpeg command construction in `src/stoat_ferret/render/worker.py` and the Rust `translate.rs` translator. Three v100 bugs (BL-618, BL-578, BL-616) arose from violations of these patterns. This document is the canonical source; reference it in design ACs for any feature touching the render pipeline.

## Invariant 1: All `-i` Inputs Before Any Output Options

FFmpeg processes command-line arguments in order. All `-i input` flags must appear **before** `-filter_complex`, `-map`, and output-path arguments.

```bash
# Correct — all inputs first
ffmpeg -i video.mp4 -i audio.mp3 -i subtitle.srt \
  -filter_complex "[0:v]..." \
  -map "[out]" output.mp4

# Wrong — subtitle -i after output options (BL-618)
ffmpeg -i video.mp4 -i audio.mp3 \
  -filter_complex "[0:v]..." \
  -map "[out]" \
  -i subtitle.srt output.mp4  # FFmpeg rejects -map here
```

**Where in code:** `worker.py` — build the `inputs` list first, then `filter_complex`, then `map`, then output path.

## Invariant 2: Single-Clip and Multi-Clip Paths Must Be Symmetric

Whenever `worker.py` has a multi-clip dispatch branch, it must have an equivalent single-clip branch with the **same logic**. Skipping the single-clip branch silently omits the feature for single-clip renders.

Features affected:
- Audio mixing (BL-578): multi-clip path amixed TTS + source audio; single-clip path did not → silent audio loss
- Windowed effects dispatch (BL-616): multi-clip path checked `windowed_custom`; single-clip path did not → windowed effects always applied full-clip

**Checklist when adding to worker.py:**
- [ ] Multi-clip branch handles the feature
- [ ] Single-clip branch handles the feature identically
- [ ] Test covers both paths

## Invariant 3: Audio Mixing Covers All Four Cases

Any code that mixes audio must enumerate all four input combinations:

| TTS present | Source audio present | Expected output |
|-------------|---------------------|-----------------|
| Yes | Yes | amix(TTS, source) |
| Yes | No | TTS only |
| No | Yes | Source only |
| No | No | No audio stream |

Omitting the "both present" case (BL-578) causes silent data loss of the source audio track in TTS renders.

## Invariant 4: amix Input Count Must Match `inputs=N`

`amix` requires `inputs=N` to match the actual number of streams fed into it. Mismatch causes FFmpeg to hang or produce silence.

```
# Correct — 2 streams, inputs=2
amix=inputs=2:duration=first:dropout_transition=0
```

## Invariant 5: filter_complex → map → output Ordering

Within the output section, the order must be: `-filter_complex` string → `-map` arguments → codec/format options → output path. Never interleave `-i` flags with `-map` flags.

## Applying These Invariants in Design ACs

When writing ACs for any BL item that modifies `worker.py` or `translate.rs`:

1. Include an explicit AC: "Single-clip and multi-clip dispatch branches both implement this feature."
2. Include an explicit AC: "Static test (no FFmpeg) asserts the FFmpeg command structure: input ordering, filter_complex string, map arguments."
3. If audio mixing is involved: include an AC covering all four TTS/source-audio combinations.

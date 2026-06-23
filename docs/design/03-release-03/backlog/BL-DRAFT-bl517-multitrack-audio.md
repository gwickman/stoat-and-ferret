# BL-DRAFT-bl517-multitrack-audio

**Status:** drafted, not filed. Track 3 cleaner-fixture retest COMPLETE 2026-06-15 (defaults verified at 9.68 dB attenuation with threshold=0.02, ratio=8; binaural-safe and quiet-window-clean across the parameter sweep).
**Supersedes / amends:** BL-517 (currently "Multi-track audio mixer with per-track volume automation envelopes")
**Evidence:** `poc-work/poc-3-multi-track-audio/retest-stereo/`, codex `10` Section 7
**Why now:** the original AC was ambiguous on which track is ducked vs which triggers; the PoC retest proved the stereo + attenuation mechanism works; production parameter tuning is still needed.

## Problem statement

The current `DuckingPattern` in `rust/stoat_ferret_core/src/ffmpeg/audio.rs:611-635` is one-input-against-itself (splits one input with asplit, sidechain compresses one branch against the other). That is NOT the wellness music+voice case, which needs two distinct input streams: voice triggers ducking on music while binaural and voice itself remain undisturbed.

The PoC retest in `09` proved the two-input compose pattern works on FFmpeg 8.0.1 and produces measurable attenuation. Parameters under-duck; default tuning needs improvement.

## Proposed acceptance criteria

### Schema

1. Per-track:
   - `track_id`: stable identifier
   - `kind`: `music` | `voice` | `binaural` | `sfx` | generic
   - `volume_envelope`: optional expression in `t` (rendered as `volume='...':eval=frame`)
   - `weight`: float for amix weighting
2. Per-ducking-pair:
   - `ducked_track_id`: the track whose gain is reduced
   - `sidechain_track_id`: the trigger track (passed through clean into amix)
   - `threshold`, `ratio`, `attack_ms`, `release_ms`: sidechaincompress params
   - `apply_pre_volume` (bool): whether volume envelope wraps before or after the compressor

Note: the field naming uses `ducked_track_id` and `sidechain_track_id` explicitly. Do NOT use ambiguous wording like "ducking_source = another_track_id" (codex `10` flagged this was reversed in the live BL).

### Renderer

3. Emit per-input `aformat=channel_layouts=stereo` before sidechaincompress and amix. PoC verified this is required to preserve stereo through the ducking pipeline.
4. Use `asplit` on the sidechain trigger so the trigger can feed both sidechaincompress AND the final amix as a clean branch.
5. Emit `amix=inputs=N:weights=<list>:duration=longest`.

### Contract tests

6. Final output has `channels=2` when any input is stereo or any track is `kind=binaural`.
7. Left and right channels are not identical for a binaural fixture (sine 440 L, sine 448 R) — confirms stereo carries through.
8. The clean voice branch is present in the final amix (voice spectrogram in the final WAV matches the source voice spectrogram, modulo the volume weight).
9. Music branch is measurably attenuated during voice intervals: render the same mix with sidechaincompress and without; assert at least 6 dB attenuation difference on the music carrier band in the voice window. (PoC measured 2.4 dB with threshold=0.05 ratio=8 — too gentle for wellness. Default parameters should target 6-12 dB.)
10. Quiet-window control: music carrier energy is unchanged between with-ducking and no-ducking renders during voice-silent windows.

### Defaults

11. **Evidence-backed default ducking parameters (2026-06-15, from T3):** `threshold=0.02, ratio=8, attack=20 ms, release=300 ms`. Measured 9.68 dB music-band attenuation during voice presence using non-overlapping cleaner fixtures (music 200 Hz / voice 1500 Hz / binaural 440-448 Hz). Quiet-window delta and binaural-band delta both 0.00 dB across the entire parameter sweep, proving the mechanism is voice-triggered and binaural-safe.
12. **Wellness-target contract test:** production renders with default parameters MUST show ≥6 dB attenuation on the music carrier band during voice intervals. Failing this is a regression.

## Out of scope

- 5.1 / 7.1 audio.
- More than 4 tracks in the schema.
- Real-time ducking preview during editing.

## Unit test seeds

```python
def test_three_track_mix_preserves_stereo(tmp_path):
    spec = MultiTrackSpec(
        tracks=[
            Track(id="music", kind="music", weight=1.0),
            Track(id="voice", kind="voice", weight=1.5),
            Track(id="binaural", kind="binaural", weight=0.6),
        ],
        ducking=[Ducking(ducked_track_id="music", sidechain_track_id="voice",
                         threshold=0.05, ratio=8, attack_ms=20, release_ms=300)],
    )
    out = render_audio(spec, tmp_path / "out.wav")
    probe = ffprobe(out)
    assert probe["channels"] == 2
    # binaural carries through
    assert not channels_identical(out)
```

## Evidence pointers

- `poc-work/poc-3-multi-track-audio/retest-stereo/3track-stereo.wav` (working two-input ducking)
- `poc-work/poc-3-multi-track-audio/retest-stereo/3track-NO-DUCKING.wav` (control)
- `09-action-plan-2-execution-results.md` Section "B1" — measured 2.4 dB attenuation
- `10-codex-response.md` Section 7 — codex's reproduction and measurement-method caveat

## Open work

Track 3 of `11-autonomous-derisking-plan.md` re-runs the measurement with cleaner non-overlapping frequencies (music 200 Hz, voice 1500 Hz, binaural 440-448 Hz) and a parameter sweep across threshold ∈ {0.05, 0.1, 0.2} and ratio ∈ {4, 8, 12}. Result feeds the "defaults" AC above.

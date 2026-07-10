# Theme 02 Retrospective — Mixer + TTS Discharge (v103)

## Theme Summary

Theme 02 discharged two deferred FFmpeg-gated ACs for the TTS→mixer pipeline (BL-516-AC-4 and BL-517 re-verification) via STOAT_TEST_FFMPEG=1 runs. PR #791 merged, confirming TTS audio routes correctly to the mixer.

## Features

### BL-516-AC-4 — TTS-to-Mixer Routing Integration Test (PR #791)
Ran `STOAT_TEST_FFMPEG=1 pytest tests/integration/test_tts_mixer_routing.py` — all assertions green. Confirmed TTS narration clips are correctly routed through the mixer at render time. AC discharged.

### BL-517 — Re-verification
Re-verified BL-517 (quiet-window test for TTS). The existing test coverage was confirmed adequate.

## Execution-Time Defect Found

During Theme 02 execution, a defect was discovered: when the source audio clip is mono (single-channel), the `amix` filter silently downmixes the TTS narration to mono regardless of the target output format. This was not a pre-existing known defect. Tracked as BL-631 (P2, unassigned).

## Status

BL-516-AC-4: discharged. BL-517: re-verified. BL-631: new defect raised (P2, not yet scheduled).

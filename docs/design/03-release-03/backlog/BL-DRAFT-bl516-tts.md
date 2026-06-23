# BL-DRAFT-bl516-tts

**Status:** drafted, **listening pass complete (2026-06-15) — both backends pass**
**Supersedes / amends:** BL-516 (currently "Text-to-speech narration — configurable local or cloud backend")
**Evidence:** `poc-work/poc-2-tts/`, `13-response-to-codex-review-12.md` Section 0
**Decision locked 2026-06-15:** Both Backend A (Kokoro cloud) and Backend C (Piper local) ship in v083. **Default backend = Piper local.** Backend B (commercial via OpenRouter) opt-in, requires the privacy switch flip (user has chosen to leave it as-is for now).

**Architectural correction 2026-06-16 (per codex `18` Blocker 5):** TTS narration is modelled as a **cue/track data structure**, NOT a per-clip effect. Wellness/explainer narration has many phrases at different timestamps on a voice track; one effect per clip cannot represent that. See the new TtsCue schema below and `02-architecture.md` Section 7 + `05-api-specification.md` "TTS narration via cue model" + `06-gui-integration.md` Section 3.

## TtsCue data model

```python
class TtsCue(BaseModel):
    cue_id: UUID
    project_id: UUID
    track_id: str                  # references an AudioTrack with kind="voice"
    start_s: float                 # placement on the timeline
    text: str
    voice: str
    backend: Literal["piper_local", "openrouter_kokoro", "openrouter_commercial"]
    gain_db: float = 0.0
    pan: float = 0.0
    cache_key: str                 # sha256(text || "::" || voice || "::" || backend)
    generated_asset_id: UUID | None = None
    status: Literal["pending", "synthesising", "ready", "failed"] = "pending"
    error: str | None = None
```

Cues are created via `POST /projects/{p}/tts_cues`. Render preflight synthesises unresolved cues into cached audio assets. The renderer (BL-505B) reads cues + tracks and emits `-i <asset_path>` per cue with `adelay=<ms>|<ms>` to place on the timeline. Cues on a `kind=voice` track automatically participate in DuckingPairs where that track is `sidechain_track_id`.

## Problem statement

snf has no TTS. The 2026-06-14 hypnotherapy showcase synthesised voiceover manually via external tools — not a sustainable workflow. v083 needs a configurable TTS backend usable within the render pipeline.

## Proposed backends

### Backend A — OpenRouter / Kokoro (cloud, first-class optional — NOT default)

- **Auth:** requires a configured OpenRouter API key (deployment-managed; not a stored draft-artifact dependency).
- **Model:** `hexgrad/kokoro-82m`, open-weight Apache 2.0.
- **Voices:** 30+, prefixed by accent + gender (`af_*` American Female, `am_*` American Male, `bf_*` British Female, `bm_*` British Male).
- **Pricing:** $0.00000062/prompt-token, $0 completion. Negligible cost for typical scripts.
- **Format:** outputs 24 kHz mono MP3 (also supports PCM). Snf renderer must upsample to 48 kHz and pan to stereo.
- **Latency:** measured 146 s for 14 s of speech (cold start; needs steady-state benchmark).
- **No privacy switch needed.** Available without commercial-model gate.

### Backend B — OpenRouter / commercial models (opt-in)

- **Voice catalogue discovered dynamically** at startup via `GET https://openrouter.ai/api/v1/models?output_modalities=speech` (per codex `18` smaller correction 5; do NOT hard-code commercial model slugs as ACs — the catalogue changes).
- **Requires flipping privacy setting at https://openrouter.ai/settings/privacy** (one-click but user action).
- Use case: if Kokoro quality is insufficient for wellness content.

### Backend C — Local Piper (offline, FIRST-CLASS)

- Fork choice: **`OHF-Voice/piper1-gpl` 1.4.2** (active; rhasspy is archived and redirects). GPL-3.0-or-later.
- Install: `pip install piper-tts==1.4.2` (~30 MB) + voice model download (~63 MB for en_US-lessac-medium).
- **Verified latency**: 3.32 s synthesis for an 11 s wellness affirmation script (T6 probe). Cold start dominates; with a pre-loaded long-lived subprocess, steady-state drops to ~1 s.
- **Performance target (corrected per codex `18` Major Risk):** ≤ 15 s for 30 s of speech on CPU dev workstation (the ≤ 5 s number was GPU/optimised territory and not established by the PoC). Stretch target ≤ 5 s warmed/GPU. BL acceptance includes a 30 s benchmark in both cold and warm states with actual numbers recorded.
- Output: 22050 Hz mono 16-bit WAV — same upsample-to-48-kHz + pan-to-stereo treatment as Kokoro.
- Voice catalogue: 80+ languages × multiple speakers at `huggingface.co/rhasspy/piper-voices`. Most CC-BY-4.0.
- Bundling recommendation: ship 1 default voice (en_US-lessac-medium ~95 MB total install); first-use-download for other voices.
- GPL-3.0 disclosure required in NOTICE. **Product decision (2026-06-15):** invoke piper as a subprocess (not Python import). This is an engineering posture that limits the licensing surface to the binary itself — not a legal proof. The user has accepted the GPL distribution tradeoff for v083; if a future legal review pushes back, the licence question is bounded to "should snf ship Piper at all" rather than "is the whole snf codebase GPL by linkage".

**Backends A and C are both first-class.** They cover different scenarios:

| Scenario | Recommended backend |
|---|---|
| Quick iteration / editing | C (Piper local — 3 s vs 146 s for cloud cold start) |
| Offline-only deployment | C |
| Cloud-native, no install | A (Kokoro) |
| Apache-2.0-only distribution | A (Kokoro) |
| Premium commercial voices | B (commercial via OpenRouter, privacy gate must be flipped) |

Backend B is opt-in (privacy gate). Backends A and C ship together in v083.

## Proposed acceptance criteria

1. **TTS cue model (per codex `18` Blocker 5).** New `TtsCue` record + endpoints `POST /projects/{p}/tts_cues`, `GET /projects/{p}/tts_cues`, `GET/DELETE /projects/{p}/tts_cues/{cue_id}`, `POST /projects/{p}/tts_cues/{cue_id}/synthesise`, `GET /tts/voices`. NOT a per-clip effect. Default backend: `piper_local`.

1a. **Config variables owned by this BL (per codex `18` Major Risk):**
   - `STOAT_OPENROUTER_API_KEY` — required for backends A and B.
   - `STOAT_TTS_DEFAULT_BACKEND` — default `piper_local`.
   - `STOAT_TTS_PIPER_MODELS_DIR` — Piper ONNX cache location.
   - `STOAT_TTS_CACHE_DIR` — synthesised audio cache directory.
   - All four documented in BOTH `docs/setup/04_configuration.md` AND `docs/manual/configuration-reference.md`.
   - `KNOWN_UNDOCUMENTED_SETTINGS_VARS` stays empty.

1b. **OpenAPI freshness:** PR includes regenerated `gui/openapi.json` (via `uv run python -m scripts.export_openapi`) + `gui/src/generated/api-types.ts` (via `cd gui && npm run generate:types`).
2. **Renderer integration.** TTS output is decoded, upsampled to project sample rate, pan-converted to stereo, and inserted as a new audio track in the multi-track mixer (BL-517 dependency).
3. **Caching.** Synthesised audio cached by `hash(text, voice, backend)` so editing iterations do not re-synthesise.
4. **Latency budget.** TTS synthesis runs asynchronously; render does not block on it. A pre-render step synthesises all TTS clips first, fills the cache, then the actual render reads cached audio.
5. **Format reconciliation acceptance:** generated audio is verified as 48 kHz stereo after the snf processing chain — ffprobe asserts `channels=2, sample_rate=48000`.
6. **Error handling:** Kokoro 429 (rate-limited) and 400 (bad request) are surfaced as render-job errors with clear stderr messages. No silent fallback.

## Out of scope

- Multi-language. Kokoro supports 8 languages but BL-516 v1 ships English only.
- Voice cloning / fine-tuned voices. Use the catalogue voices.
- Real-time preview synthesis during editing (latency too high).
- TTS quality metrics (objective). Use the listening pass + user verdict.

## Dependencies

- **BL-517** (multi-track mixer) for inserting TTS as a track.
- **BL-505** (render-graph rewrite) for the renderer to consume multi-clip + multi-audio inputs.
- **BL-DRAFT-bl506-render-evidence** for surfacing TTS errors in the render evidence artefact.

## Unit test seeds

```python
def test_tts_builder_emits_input_for_synth_path(tmp_path):
    spec = TtsNarration(text="hello world", voice="af_bella", backend="openrouter_kokoro")
    audio_path = synthesise(spec, cache_dir=tmp_path)
    assert audio_path.exists()
    probe = ffprobe(audio_path)
    assert probe["channels"] == 1  # raw Kokoro output
    assert probe["sample_rate"] == 24000
    # post-pipeline conversion
    norm_path = normalise_to_project(audio_path, target_sr=48000, target_channels=2)
    probe2 = ffprobe(norm_path)
    assert probe2["channels"] == 2
    assert probe2["sample_rate"] == 48000
```

## Decisions locked (2026-06-15)

1. ✅ **Both Backend A (Kokoro cloud) and Backend C (Piper local) ship in v083.**
2. ✅ **Default backend = Piper local.** Offline-friendly, ~50× faster than cloud cold start, no rate-limit risk.
3. ✅ **GPL-3.0 distribution accepted** via subprocess-invocation pattern for Piper. NOTICE file discloses the binary's licence.
4. ✅ **Privacy switch stays as-is.** Backend B (commercial models) remains opt-in pending future flip.

## Remaining open items (none blocking)

- Bundled default voices: ship `en_US-lessac-medium` (CC-BY-4.0, ~95 MB install) as the default. Other voices download on first use.
- Long-lived Piper subprocess pattern: snf spawns a persistent piper process and pipes synthesis requests via stdin, eliminating cold-start cost on every call. Acceptance criterion for the renderer integration.

## Evidence pointers

- `poc-work/poc-2-tts/kokoro-af_bella.mp3` — Backend A synthesis (cloud, 91 KB, 14.37 s)
- `poc-work/poc-2-tts/piper-en_US-lessac-medium.wav` — Backend C synthesis (local, 479 KB, 10.87 s)
- `poc-work/poc-2-tts/objective-metrics.md` — Backend A metrics
- `poc-work/poc-2-tts/piper-objective-metrics.md` — Backend C metrics + comparison table
- `poc-work/poc-2-tts/piper-fork-comparison.md` — fork choice + licence analysis
- `poc-work/poc-2-tts/listening-pass-queue.md` — user listening checklist
- `13-response-to-codex-review-12.md` Section 0 — OpenRouter TTS ground truth

# Release 3 — Use Cases

**Audience:** customer / product / non-technical reviewer.
**Purpose:** ground every Release 3 requirement in two concrete creator workflows. Anything snf cannot do in service of these use cases is a defect.

The two use cases were chosen because they exercise every Release 3 capability between them. They aren't hypothetical — they came directly from the 2026-06-14 showcase round that surfaced the original 22-item gap list.

---

## Persona A — Maya, wellness/hypnotherapy practitioner

**Context.** Maya runs a small online practice. She records short guided sessions (5-15 min) and publishes them to her membership site and YouTube. She is not a video editor; she uses snf because it's API-driven and her assistant can author sessions from a template.

**Goals.**
- Compose a guided session that combines: spoken affirmations (her own voice OR synthesised), calming music, binaural beats, an attention-fixing visual (spiral / radial burst), occasional on-screen text captions, and a fade in/out at the start and end.
- Repeat the template for new sessions with minimal manual work.
- Captions accessible for hearing-impaired members.

**Today's pain.** Cannot do any of it through snf because:
- Multi-clip timelines silently drop everything after clip 1.
- Animated opacity (the spiral fade-in) is runtime-broken.
- No TTS path.
- No multi-track audio mixer.
- No image-as-clip.
- No procedural shape library.
- No subtitle support.

She currently glues this together with ffmpeg directly. Painful and error-prone.

---

## Persona B — Devon, educational explainer producer

**Context.** Devon writes scripted explainers for a documentary YouTube channel. Each video is 5-10 segments with cross-fades, b-roll, on-screen titles, colour grading and music ducking under narration.

**Goals.**
- Author a multi-segment timeline programmatically (he generates the segment list from a script).
- Apply colour grading per segment.
- Add a logo intro/outro from a static PNG.
- Narrate using TTS during draft iteration; replace with his recorded voice for the final render.
- Burn in subtitles for social-media short-form distribution.
- Soft subtitles for YouTube upload.

**Today's pain.** Same as Maya — multi-clip rendering doesn't work, and most of the wishlist items don't exist. Devon currently uses a desktop editor and only uses snf for the QC pass that Release 2 added.

---

## Use Case 1 — Hypnotherapy session (Maya)

### Session structure (template)

```
0:00 - 0:30   Intro: spiral image, fade in, soft instrumental music
0:30 - 5:00   Induction:
              - voice narration ("Find a comfortable position. Breathe in...")
              - music ducked under voice
              - binaural beats (440/448 Hz) at low volume
              - captions sync'd to each affirmation line
5:00 - 8:00   Deepening: same audio bed, different visual (concentric rings instead of spiral)
8:00 - 9:30   Suggestion: voice narration over music+binaural; captions
9:30 - 10:00  Emergence: fade back to spiral, music swells, voice trails off
```

### Step-by-step (API-driven; assistant authors this from a template)

| Step | snf API call | Release 3 capability exercised |
|---|---|---|
| 1 | `POST /projects` with `width=1280, height=720, fps=30` | Release 1 (existing) |
| 2 | `POST /assets` (multipart) for `spiral.png` (or generate via BL-513 procedural shape) | A1, A2 |
| 3 | `POST /assets` for `concentric-rings.png` | A1, A2 |
| 4 | `POST /assets` for `calm-music.mp3` | A1 |
| 5 | `POST /projects/{p}/clips` with `clip_type=image, source_asset_id=<spiral>, timeline_position=0, timeline_end=300` | C4 |
| 6 | `POST /projects/{p}/clips/{c}/effects` with opacity fade-in (0→1 over 2 s) | C2 + T3 (BL-502 fix) |
| 7 | `POST /projects/{p}/clips` with `clip_type=image, source_asset_id=<concentric>, timeline_position=300, timeline_end=480` | C4 |
| 8 | `POST /projects/{p}/clips` for emergence segment (spiral again) | C4 |
| 9 | Configure project audio tracks: music + voice + binaural; ducking pair (music ducked by voice) | AU1 + AU2 |
| 10 | For each affirmation line: `POST /projects/{p}/clips/{c}/effects` with `tts_narration` (text, voice="en_US-lessac-medium", backend="piper_local") + scheduled on the voice track | AU3 |
| 11 | For each affirmation line: also add a SubtitleScriptBuilder entry | S3 |
| 12 | `POST /render` with the project id, `output_format="mp4"` | C1 + T1 + T2 |
| 13 | `GET /render/{job_id}/evidence` — assert `exit_code=0, output_size_bytes > 0, command_args` non-empty | T2 |
| 14 | Verify output: ffprobe duration matches expected 600 s; spectrogram shows music ducking during voice intervals; spot-check frames show spiral with fade-in at t=1.0, concentric rings at t=400 | C1, C4, AU2, T3 |

### Why this use case matters

Every step from 1-14 fails today. Multi-clip is the root blocker; everything else stacks on top. The hypnotherapy showcase from 2026-06-14 had to be hand-built outside snf with raw ffmpeg, exactly because none of this exists.

### Acceptance signal

The Maya use case is **done** when:

- The full session renders end-to-end via a single `POST /render` call.
- Total render time is reasonable (target: ≤ 5× real-time for offline render, i.e. a 10-min session renders in ≤ 50 min).
- All assertions in step 14 pass.
- The same session can be re-rendered with a different voice (`piper_local en_GB-alan-medium`) without re-authoring.
- Soft subtitles for the affirmation script are present in the output mp4 (toggleable in players).

---

## Use Case 2 — Multi-segment educational explainer (Devon)

### Project structure

```
Seg 1 (0:00-0:08)  Logo PNG, fade in, soft motion (zoompan / Ken Burns)
Seg 2 (0:08-1:00)  B-roll video clip, vignette + warm curves grade, voiceover, music
Seg 3 (1:00-2:00)  Second b-roll, cross-fade transition from seg 2, drawtext title overlay
Seg 4 (2:00-3:30)  Third b-roll, curves + hue rotation for mood shift
Seg 5 (3:30-4:30)  Recap: pixelated radial-burst overlay (procedural), voiceover summary
Seg 6 (4:30-5:00)  Outro logo, fade out

Audio:  music ducked under voice, voice as TTS in draft iteration
Subs:   burned-in for social-media short-form; soft for YouTube upload
```

### Step-by-step

| Step | snf API call | Release 3 capability exercised |
|---|---|---|
| 1 | `POST /assets` for logo.png, b-roll video files | A1 |
| 2 | `POST /projects` | Release 1 |
| 3 | Seg 1: image clip with zoompan effect | C4, E1 |
| 4 | Seg 2: video clip with vignette + curves effects | C2, E2, E3 |
| 5 | Seg 3: video clip with cross-fade transition from Seg 2; drawtext title via SubtitleScriptBuilder | C3, S3 |
| 6 | Seg 4: video clip with curves + hue rotation effects | C2, E2, E4 |
| 7 | Seg 5: procedural radial-burst PNG generated via BL-513; loaded as image clip with opacity | A2, C4, T3 |
| 8 | Seg 6: logo image clip with fade out | C4, T3 |
| 9 | Audio: music track + voice track (TTS); ducking pair | AU1, AU2, AU3 |
| 10 | Soft subtitle track (en) embedded for YouTube version; same SRT burned-in for short-form version | S1, S2 |
| 11 | `POST /render` for the YouTube version (soft subtitles, no burn-in) | C1, T1, T2 |
| 12 | `POST /render` for the short-form version (burned subtitles) | C1, S1, T2 |
| 13 | Verify both outputs via render evidence + QC pass from Release 2 | T2 |

### Acceptance signal

The Devon use case is **done** when:

- Both renders complete via two `POST /render` calls with no manual re-authoring.
- Each render's `GET /render/{id}/evidence` shows `exit_code=0` and the actual `command_args` used.
- Frame extraction at each segment midpoint shows the expected visual (vignette in seg 2, hue rotation in seg 4, etc.).
- YouTube version has the soft subtitle track present (ffprobe).
- Short-form version has the same captions burned in (OCR or pixel-presence test).
- The Release 2 QC pass passes (loudness compliant, true-peak under limit, no clipping).

---

## Cross-cutting use case — Trust & verification (any user)

### Story

A new operator runs the chatbot-driven harness against snf. They submit a multi-clip project. The harness asserts:

1. `POST /render` returned 200 → real, not silent success.
2. `GET /render/{job_id}/evidence` returned populated fields → no silent drop.
3. `evidence.exit_code == 0` → FFmpeg actually succeeded.
4. `evidence.output_size_bytes > 50_000` → file is not a 0-byte stub.
5. Optional: SSIM of extracted frames vs source clips > 0.99 → clips are actually where they should be.

Today this story is fictional because snf has no evidence API. The operator can only trust the HTTP status code, which lies (returns 200 even when the worker dropped 9 of 10 clips).

### Acceptance signal

After T1 + T2 ship:

- Every multi-round chatbot session attaches the evidence JSON for each render.
- The harness fails loudly when evidence is missing.
- Past silent-success regression modes are impossible.

---

## Use-case-to-capability matrix

| Capability | Maya (UC1) | Devon (UC2) | Trust (cross) |
|---|---|---|---|
| C1 Multi-clip timeline | required | required | required |
| C2 Per-clip effects + windows | required | required | — |
| C3 Transitions | optional | required | — |
| C4 Image-as-clip | required | required | — |
| A1 Asset library | required | required | — |
| A2 Procedural shapes | required | optional | — |
| A3 Generic procedural | optional | optional | — |
| AU1 Multi-track audio | required | required | — |
| AU2 Sidechain ducking | required | required | — |
| AU3 TTS | required (or recorded voice) | required (draft iteration) | — |
| S1 Burned subtitles | optional | required (short-form) | — |
| S2 Soft subtitles | required (accessibility) | required (YouTube) | — |
| S3 Subtitle script helper | required | required | — |
| E1 Zoompan | optional | required | — |
| E2 Curves | optional | required | — |
| E3 Vignette | optional | required | — |
| E4 Hue rotation | optional | required | — |
| T1 Render preflight | implicit | implicit | required |
| T2 Render evidence | implicit | implicit | required |
| T3 BL-499 + BL-502 carry-forwards | required (fade-in spiral) | required (fade-out logo) | — |

**"Required" means the use case is incomplete without it.** "Optional" means the use case works but is weaker without it.

Two capabilities are NOT in either use case: A3 generic procedural (BL-514) and the commercial TTS comparison row (Backend B). Both are scoped as opt-in / future. That's intentional — they're flexibility surface, not the core deliverable.

## What if a use case grows?

These two scenarios are deliberately small. Real users will assemble bigger projects. The release is sized so that **scaling up doesn't require new capabilities** — a 50-segment explainer is the same code path as a 6-segment one; a 30-min hypnotherapy session is the same as a 5-min one.

The only practical limits are perf (rendering a 30-min 1080p session takes longer) and the asset library quota question (open question 2 in `03-capabilities-and-requirements.md`).

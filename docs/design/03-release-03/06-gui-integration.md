# Release 3 — GUI Integration

**Audience:** GUI implementer + product reviewer.
**Scope:** UI touchpoints for Release 3 capabilities. Release 3 is API-driven; the GUI surface is additive and minimal.

## What the GUI needs to add

Release 3 has five new GUI affordances. The rest of the GUI (Release 1 + 2 surface) is unchanged.

### 1. Asset library page (BL-515)

A new top-level page `Assets` listing the user's uploaded files.

**Components:**
- **Upload control.** Drag-drop or file picker. Kind selector (image/audio/subtitle/font/lut). Optional licence + tags fields.
- **Asset grid.** Thumbnails for images; filename + metadata for others. Filter by kind + tags.
- **Asset detail panel.** Filename, size, MIME, licence, references (which projects use it), delete button.
- **Delete confirmation.** Soft-delete only; shows referenced projects before allowing delete.

**API used:** `POST /assets`, `GET /assets`, `GET /assets/{id}`, `DELETE /assets/{id}`.

**Empty state.** A "Why use assets?" link to the BL-515 docs.

### 2. Clip type selector (BL-511)

The existing clip-creation flow gets a `clip_type` selector at the top: **File / Image / Generator**.

**Behaviour:**
- `File`: the existing flow (pick a video file).
- `Image`: surface an asset picker filtered to `kind=image`; require a duration.
- `Generator`: the existing flow (gradient_generator, noise_generator).

**Asset picker reuses the Asset library** (component, not a new page).

### 3. TTS cue editor (BL-516)

Per codex `18` Blocker 5, TTS narration is modelled as cues on an audio voice track, NOT a per-clip effect. The GUI surfaces a cue editor under the multi-track inspector (Section 4 below).

**Add-cue form** (opens when the user clicks an empty slot on a voice track at a timeline position):

- **Backend selector.** Three options shown as cards:
  - **Local (Piper)** — recommended, offline, 30+ voices. Latency badge: `~3 s` cold-start, `~1 s` warm.
  - **Cloud (Kokoro)** — requires OpenRouter key, 30+ voices. Latency badge: non-interactive (≥ 10× real-time cold).
  - **Commercial (advanced)** — requires OpenRouter privacy setting to be enabled AND a configured key. Hidden by default; visible via a settings toggle.
- **Voice picker.** Filtered by backend. Catalogue fetched from `GET /tts/voices`. Shows accent + gender. **Preview button** synthesises a 2-second sample via `POST /projects/{p}/tts_cues/{cue_id}/synthesise` against a temporary cue id, plays via the existing audio preview path.
- **Text input.** Multi-line textarea. Character count + provider limit badge.
- **Start time picker.** Defaults to the timeline click position.
- **Cue list panel.** Shows all cues on the voice track in order, with status badges (`pending`, `synthesising`, `ready`, `failed`). Allows reorder by dragging start times.

**API used:**
- `POST /projects/{p}/tts_cues` to create.
- `GET /projects/{p}/tts_cues` to list.
- `POST /projects/{p}/tts_cues/{cue_id}/synthesise` to eager-trigger.
- `DELETE /projects/{p}/tts_cues/{cue_id}` to remove.
- `GET /tts/voices` for the catalogue.

**Synth progress.** Each cue card shows a per-cue spinner / progress bar driven by polling `GET /projects/{p}/tts_cues/{cue_id}` (or a `tts.synthesis.progress` WebSocket event payload if/when that namespace is added).

### 4. Multi-track audio inspector (BL-517)

A new panel (sibling to the existing timeline) lists the project's audio tracks.

**Components:**
- **Track list.** Music / Voice / Binaural / SFX. Per-track: weight slider, volume envelope editor (reuses Release 2's keyframe UI), kind label.
- **Ducking pair editor.** "Music ducked by Voice" style toggles with the threshold/ratio/attack/release sliders. Defaults pre-filled with the verified values (threshold=0.02, ratio=8, attack=20 ms, release=300 ms).
- **Visual.** Stacked block representation of each track over the timeline.

**API used:** `POST /projects/{p}/audio_tracks`, `POST /projects/{p}/audio_tracks/ducking`.

### 5. Render evidence inspector (BL-506-tech)

After a render completes, the existing job-detail page shows a new "Evidence" section.

**Components:**
- **Summary line.** `exit_code: 0 · output: 12.4 MB · stderr: 0 warnings`.
- **Expand for full evidence.** Reveals `command_args` (formatted as a multi-line code block), `stderr_tail` (collapsible), `filter_script_path` if any.
- **Copy button.** Copies command_args as a single-line shell-quoted string for local debugging.

**API used:** `GET /render/{job_id}` (summary fields) + `GET /render/{job_id}/evidence` (full evidence; admin-only by default).

**Permission gate:** if the user lacks admin, the full evidence section is hidden with a "Contact admin for full render details" placeholder.

## Touchpoints that DON'T need GUI changes

| Capability | Why no GUI change |
|---|---|
| Multi-clip rendering | The timeline already supports multi-clip authoring. The fix is server-side. |
| Per-clip effects with windows | The effect form already accepts a `window` field (Release 2 WindowSpec). The fix is renderer consumption. |
| Render preflight | Surfaces as a 422 or warning in the existing job-creation flow. The error message guides the user. |
| Carry-forwards BL-499 / BL-502 | Invisible at the GUI level — the runtime fix doesn't change the API surface. |
| Subtitle script helper | Uses the existing effect-creation form with the new `subtitle_script` effect type. |
| Curves / Vignette / Hue rotation / Zoompan | Use the existing effect-creation form. New effect types in the registry; GUI auto-picks up the parameter schema. |
| Burned + soft subtitles | Burned: existing effect form. Soft: a new section on the render-request form (small, 1 row per track). |
| Procedural shapes / generic procedural | Use the existing effect-creation form for `procedural_shape` and `procedural_image` effect types. The resulting PNG asset gets referenced as an image clip via the asset picker. |
| AGPL / GPL disclosures | Appears in the existing About / NOTICE page. |

## Settings page additions

The settings page (existing) gains three new sections:

1. **Assets.** Shows the configured `STOAT_ASSETS_DIR` (display-only; env-driven, the GUI does NOT mutate env vars) and `STOAT_ASSETS_MAX_SIZE_BYTES`.
2. **TTS.** Shows the configured-or-not status of `STOAT_OPENROUTER_API_KEY` (masked badge: `configured` / `not configured` per codex `18` Major Risk — a running process cannot persistently mutate its own environment for future restarts; the GUI must NOT claim it can save the env var). For deployments that need runtime key management, a future BL adds a secret-store backend (out of scope for Release 3).
3. **Render evidence.** Shows the value of `STOAT_RENDER_EVIDENCE_FULL_ACCESS` (display-only; env-driven). No GUI toggle — this is an operator decision per deployment.

## State management

- **Asset upload progress.** New WebSocket event `asset.upload.progress` (% complete) and `asset.upload.complete` (asset id). GUI subscribes during upload.
- **Render evidence ready.** Existing render job-completed event includes a flag indicating whether evidence is populated. GUI re-fetches the job to surface the evidence section.
- **TTS synthesis status.** New event `tts.synthesis.progress` (cache hit | synthesising | complete). Surfaces in the effect-form save flow.

## Accessibility

Release 3 adds accessibility surface area:

- The soft-subtitle render output is itself an accessibility feature.
- The TTS narration capability supports accessible audio descriptions.
- Voice picker preview button has keyboard activation.
- Asset library page is keyboard-navigable (existing pattern).
- Render evidence inspector uses semantic HTML (`<details>` for expand, `<code>` for command args).

## Test coverage (Playwright UAT)

New UAT scenarios:

1. Upload an image asset → reference it as a clip → render → inspect evidence.
2. Add TTS narration to a clip → preview voice → save → render → assert audio is in output.
3. Configure music + voice + ducking → render → inspect spectrogram.
4. Add a soft subtitle track → render → assert subtitle stream in ffprobe.
5. Submit a render that needs a capability the worker doesn't have → assert 422 surface message.
6. Delete an asset referenced by a clip → assert 409 with referenced-projects list.

All Playwright scenarios run headed in the existing UAT harness.

## Out of GUI scope

- Editing TTS synthesis in real time (latency too high for live preview).
- A custom voice trainer / model importer (BL-516 ships catalogue voices only).
- A subtitle editor (snf imports SRT/ASS sidecars; doesn't author them).
- A bulk asset migration tool.
- A multi-tenant asset namespace UI.

# Release 2 — API Specification (new & changed)

All endpoints follow Release 1 conventions: base `/api/v1`, plural resources, nested routes, structured errors with `suggestion`, AI-discoverable schemas, generated filter/command previews for transparency. Only **new or changed** surface is listed.

---

## Effects (registry additions)

New effect types appear automatically in `GET /api/v1/effects` (with JSON schema + AI hints) and are applied via the existing `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects` flow. Release 2 adds:

**Audio:** `deesser`, `deplosive`, `noise_reduction`, `time_stretch`, `pitch_shift`, `pan`, `auto_pan`, `convolution_reverb`, `parametric_eq`, `multiband_compressor`, `limiter`, `loudness_normalize`, `sub_layer`, `sidechain_duck` (formalised).
**Generators (source clips):** `tone_generator` (isochronic/binaural/sine), `noise_generator`, `gradient_generator`.
**Video:** `color_lut`, `blur` (gaussian/directional), `sharpen`, `chroma_key`, `blend`, `lens_distortion`, `chromatic_aberration`.
**Time/edit:** `reverse`, `variable_speed`, `framerate_convert`, `freeze_frame`.

Each effect that supports automation accepts an **automation envelope** in place of a scalar parameter:

```json
POST /api/v1/projects/{pid}/clips/{cid}/effects
{
  "type": "volume",
  "params": {
    "level": { "automation": { "default": 1.0,
      "keyframes": [
        {"t": 0.0, "value": 0.0, "curve": "linear"},
        {"t": 3.0, "value": 1.0, "curve": "ease_in_out"},
        {"t": 30.0, "value": 0.6, "curve": "linear"}
      ] } }
  }
}
```

Response includes `filter_preview` with the **Rust-compiled expression** (transparency), e.g. `volume='if(lt(t,3),...)'`.

---

## Markers / Regions

```http
GET    /api/v1/projects/{pid}/markers
POST   /api/v1/projects/{pid}/markers        # {name, type, start, end}
PATCH  /api/v1/projects/{pid}/markers/{mid}
DELETE /api/v1/projects/{pid}/markers/{mid}
```

Regions are ordered, named, typed (e.g. `section`). Used by section-aware automation and chapter export. Validation (non-overlap for `section` type, in-bounds) is performed before persist.

---

## Editing primitives

```http
POST /api/v1/projects/{pid}/clips/{cid}/split     # {at_frame}  → returns two clips
POST /api/v1/projects/{pid}/clips/{cid}/reverse    # applies reverse effect (validates length<=buffer limit)
```

Range-bound effects use the existing effect endpoint with an added optional window:

```json
{ "type": "blur", "params": {...}, "window": { "start_frame": 120, "end_frame": 300 } }
```

The window compiles to an `enable='between(t,a,b)'` clause (shown in `filter_preview`).

---

## Delivery profiles

```http
GET    /api/v1/delivery-profiles
POST   /api/v1/delivery-profiles
GET    /api/v1/delivery-profiles/{name}
DELETE /api/v1/delivery-profiles/{name}
```

```json
POST /api/v1/delivery-profiles
{
  "name": "session-master",
  "outputs": [
    {"container": "wav", "audio_codec": "pcm_s24le"},
    {"container": "mp3", "audio_codec": "libmp3lame", "bitrate": "256k"},
    {"container": "mp4", "video_codec": "libx264", "audio_codec": "aac"}
  ],
  "loudness": { "target_lufs": -16.0, "true_peak_ceiling_dbtp": -1.0 },
  "metadata": { "title": "…", "embed_chapters_from_markers": true }
}
```

---

## Render & delivery (changed)

`POST /api/v1/render/start` accepts an optional `delivery_profile` and `run_qc` flag. When a profile is supplied, render produces every declared output, then runs the QC pass against the profile's targets; the job fails (with a QC report) if any assertion fails.

```http
POST /api/v1/render/start
{ "project_id": "...", "delivery_profile": "session-master", "run_qc": true }
```

---

## Quality Control (new)

```http
POST /api/v1/qc/run                         # {artifact_path | job_id, assertions? | profile?}
GET  /api/v1/qc/reports/{report_id}
GET  /api/v1/render/{job_id}/qc             # QC report for a render job
```

**QC report shape:**

```json
{
  "report_id": "qc_001",
  "overall": "pass",
  "checks": [
    {"id": "loudness_integrated", "measured": -16.1, "target": -16.0, "tolerance": 0.5, "unit": "LUFS", "pass": true},
    {"id": "true_peak", "measured": -1.3, "target": -1.0, "comparator": "<=", "unit": "dBTP", "pass": true},
    {"id": "clipping", "measured": 0, "target": 0, "unit": "samples", "pass": true},
    {"id": "unintended_silence", "measured": 0, "target": 0, "unit": "regions", "pass": true},
    {"id": "decode_integrity", "measured": "ok", "pass": true},
    {"id": "chapters_present", "measured": 4, "target": 4, "pass": true}
  ]
}
```

The QC report is the contract consumed by the GUI results panel **and** by the test layer (assertions). This is the bridge that makes use-case outcomes machine-testable.

---

## WebSocket events (additions)

`qc.started`, `qc.check_completed`, `qc.completed` (overall pass/fail), `render.qc_failed`. Existing `render.*` and `ai_action` events unchanged. All follow the Release 1 replay contract (resume via `Last-Event-ID`).

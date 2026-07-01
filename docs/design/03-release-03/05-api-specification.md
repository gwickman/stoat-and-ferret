# Release 3 — API Specification

**Audience:** API consumer, GUI implementer, harness author.
**Scope:** new and changed API surfaces in Release 3. Existing endpoints (Release 1 + 2) are referenced but not redocumented.

## Summary of changes

| Endpoint | Change | BL |
|---|---|---|
| `POST /render` | Preflight check; returns 422 / structured warning when project state is unrepresentable | BL-505A |
| `GET /render/{job_id}` | Adds sanitised evidence summary fields | BL-506-tech |
| `GET /render/{job_id}/evidence` | NEW — full evidence retrieval. Gated by `STOAT_RENDER_EVIDENCE_FULL_ACCESS` (no admin auth surface in current repo) | BL-506-tech |
| `POST /assets` | NEW — multipart asset upload | BL-515 |
| `GET /assets` | NEW — list assets | BL-515 |
| `GET /assets/{id}` | NEW — asset metadata | BL-515 |
| `GET /assets/{id}/file` | NEW — asset download | BL-515 |
| `DELETE /assets/{id}` | NEW — soft delete | BL-515 |
| `POST /projects/{p}/clips` | `clip_type` enum gains `"image"`; `source_asset_id` added | BL-511 |
| `POST /projects/{p}/clips/{c}/effects` | Existing endpoint; the new effects all use it. Schemas added in this release. | All builders except BL-516 |
| `POST /projects/{p}/audio_tracks` | NEW — project-level multi-track audio spec | BL-517 |
| `POST /projects/{p}/audio_tracks/ducking` | NEW — declare ducking pairs | BL-517 |
| `POST /projects/{p}/tts_cues` | NEW — create TTS narration cue on an audio track | BL-516 |
| `GET /projects/{p}/tts_cues` | NEW — list cues on a project | BL-516 |
| `GET /projects/{p}/tts_cues/{cue_id}` | NEW — fetch a cue (poll synth status) | BL-516 |
| `DELETE /projects/{p}/tts_cues/{cue_id}` | NEW — delete a cue | BL-516 |
| `POST /projects/{p}/tts_cues/{cue_id}/synthesise` | NEW — explicit synth trigger | BL-516 |
| `GET /tts/voices` | NEW — voice catalogue (Piper static + Kokoro static + commercial dynamic via OpenRouter models API) | BL-516 |
| Render request `render_plan.settings` extension | `soft_subtitles` added (NOT a new top-level field — render request keeps `extra="forbid"`) | BL-520 |

Existing endpoints not touched in Release 3:
- `POST /projects`, `GET /projects/{p}` (Release 1)
- `POST /render/preview` (Release 1)
- `GET /render/{job_id}/events` (Release 1)
- HLS preview session endpoints (Release 1)
- WebSocket event stream (Release 1)
- Delivery profiles / QC pass (Release 2)
- Markers / regions (Release 2)
- Keyframe automation (Release 2)

## Endpoint details

### Render preflight extension (BL-505A)

**Endpoint:** `POST /render` (existing handler at `src/stoat_ferret/api/routers/render.py:349`).

**Behaviour change:** before calling `render_service.submit_job`, run a preflight pass that validates the persisted project state against the current worker's capability matrix. The preflight is fast (O(clips + effects)) and DB-only — no FFmpeg invocation.

**Preflight check list:**
1. Project has > 1 clip but `RENDERER_VERSION` doesn't yet support multi-clip → warning OR 422 (configurable strict mode).
2. Any clip has `effects` array populated but `RENDERER_VERSION` is pre-BL-505B → warning OR 422.
3. Any clip has `clip_type=image` but BL-511 hasn't shipped in this version → 422.
4. Any clip references a `source_asset_id` but BL-515 hasn't shipped → 422.
5. Project has audio_tracks beyond Release 1/2's single-track baseline but BL-517 hasn't shipped → 422.
6. Project has TTS effect but BL-516 hasn't shipped → 422.

**Response (warning mode):** 200 with a `warnings: list[str]` field on the job-creation response.
**Response (strict mode):** 422 with `detail: {capability: <name>, reason: "current worker version does not support this"}`.

Strict mode is the default for production deployments; warning mode is for development.

### Render evidence (BL-506-tech)

**Endpoint A:** existing `GET /render/{job_id}` gets new fields.

```json
{
  "id": "...",
  "project_id": "...",
  "status": "completed",
  "output_path": "...",
  "output_format": "mp4",
  "progress": 1.0,
  "error_message": null,
  "created_at": "...",
  "completed_at": "...",

  // NEW
  "evidence": {
    "exit_code": 0,
    "output_size_bytes": 12345678,
    "command_build_error": null
  }
}
```

The top-level `evidence` field is the default-public surface (safe to return on any deployment).

**Endpoint B:** NEW `GET /render/{job_id}/evidence` — full evidence, admin/debug-only by default.

```json
{
  "job_id": "...",
  "command_args": ["ffmpeg", "-y", "-i", "/abs/path/clip1.mp4", "..."],
  "command_build_error": null,
  "exit_code": 0,
  "stderr_tail": "...last 16 KB of stderr...",
  "output_path": "/abs/path/output.mp4",
  "output_size_bytes": 12345678,
  "filter_script_path": null,
  "redacted_fields": []
}
```

**Auth:** `GET /render/{job_id}/evidence` defaults to admin-only on production deployments via a `STOAT_RENDER_EVIDENCE_FULL_ACCESS` setting. Local-dev mode exposes it without auth.

**Schema source:** `src/stoat_ferret/api/schemas/render.py::RenderEvidence`.

### Asset library (BL-515)

#### `POST /assets`

Multipart upload.

**Request fields:**
- `file` (multipart file part, required)
- `kind` (form field, required, one of `image|audio|subtitle|font|lut`)
- `licence` (form field, optional, free-text)
- `tags` (form field, optional, comma-separated)

**Validation:**
- Content-sniff: actual file type must match `kind`. Mismatch → 415.
- Size limit: 100 MB by default; configurable via `STOAT_ASSETS_MAX_SIZE_BYTES`.
- MIME allow-list per kind:
  - `image`: image/png, image/jpeg
  - `audio`: audio/mpeg, audio/wav, audio/x-wav, audio/ogg
  - `subtitle`: text/plain (extension `.srt`), application/x-subrip, text/vtt
  - `font`: font/ttf, font/otf
  - `lut`: text/plain (extension `.cube`)
- Path-traversal: server stores under `STOAT_ASSETS_DIR / hash[:2] / hash`. Reject names with `..`, leading `/`, absolute paths.

**Response: 201 Created.**

```json
{
  "id": "uuid",
  "kind": "image",
  "original_filename": "spiral.png",
  "mime_type": "image/png",
  "size_bytes": 23704,
  "licence": "CC-BY-4.0",
  "tags": ["hypnotherapy"],
  "created_at": "2026-..."
}
```

If a file with the same content hash already exists, returns 200 with the existing asset id (idempotent upload). Caller can distinguish via response status.

#### `GET /assets`

**Query params:**
- `kind` (optional, filter)
- `tag` (optional, filter)
- `limit` (default 50)
- `offset` (default 0)

**Response: 200.**

```json
{
  "items": [
    { "id": "...", "kind": "image", "original_filename": "...", "size_bytes": ..., ... }
  ],
  "total": 42,
  "limit": 50,
  "offset": 0
}
```

#### `GET /assets/{id}`

**Response: 200.** Same shape as the POST response. 404 if soft-deleted (configurable).

#### `GET /assets/{id}/file`

**Response: 200** with the file bytes and a `Content-Type` matching the asset's `mime_type`. `Content-Disposition: attachment; filename="<original_filename>"`.

#### `DELETE /assets/{id}`

Soft delete. **Response: 204** if successful.

**Constraint:** if the asset is referenced by any active clip (`source_asset_id`), the delete is rejected with 409 Conflict.

### Clip schema extension (BL-511)

**Endpoint:** `POST /projects/{p}/clips` (existing).

**Schema change at `src/stoat_ferret/api/schemas/clip.py:53-83`:**

```python
class CreateClipRequest(BaseModel):
    clip_type: Literal["file", "generator", "image"]   # ADDED "image"
    source_video_id: UUID | None = None               # existing
    source_asset_id: UUID | None = None               # NEW (used when clip_type=image)
    generator_params: dict | None = None              # existing
    in_point: int
    out_point: int
    timeline_position: int
    timeline_start: float | None = None
    timeline_end: float | None = None                 # REQUIRED when clip_type=image
```

**Validation:**
- `clip_type=image` requires `source_asset_id` (referencing an `image`-kind asset) and `timeline_end`.
- `clip_type=image` does NOT use `source_video_id` or `generator_params`.

### Audio track schema (BL-517)

#### `POST /projects/{p}/audio_tracks`

NEW. Declares the project-level audio track structure.

**Request body:**

```json
{
  "tracks": [
    {
      "track_id": "music",
      "kind": "music",
      "source_asset_id": "asset-uuid-or-null",
      "volume_envelope": null,
      "weight": 1.0
    },
    {
      "track_id": "voice",
      "kind": "voice",
      "source_asset_id": null,    // populated by TTS at render time
      "volume_envelope": null,
      "weight": 1.5
    },
    {
      "track_id": "binaural",
      "kind": "binaural",
      "binaural_params": { "left_hz": 440, "right_hz": 448 },
      "weight": 0.6
    }
  ]
}
```

**Validation:**
- `track_id` unique across the project.
- `kind=binaural` uses `binaural_params` instead of `source_asset_id`.
- `kind=voice` allows source_asset_id null (will be populated by TTS effect at render time).
- `weight` between 0 and 4 (inclusive).
- `volume_envelope`, if present, is a valid FFmpeg time-expression.

#### `POST /projects/{p}/audio_tracks/ducking`

NEW. Declares ducking pairs.

```json
{
  "ducking_pairs": [
    {
      "ducked_track_id": "music",
      "sidechain_track_id": "voice",
      "threshold": 0.02,
      "ratio": 8.0,
      "attack_ms": 20,
      "release_ms": 300,
      "apply_pre_volume": true
    }
  ]
}
```

**Validation:**
- Both track ids reference real tracks in the project.
- `threshold` in (0, 1].
- `ratio` in [1, 32].
- `attack_ms`, `release_ms` in (0, 5000].

### TTS narration via cue model (BL-516) — NEW endpoints

Per codex `18` Blocker 5, TTS narration is **NOT** a per-clip effect. Wellness/explainer narration has many phrases at different timestamps on a voice track; attaching one effect per clip cannot represent that, and clip schema does not have an audio clip type. The cue/track model is correct.

#### `POST /projects/{p}/tts_cues`

NEW. Creates a TTS cue.

**Request body:**

```json
{
  "track_id": "voice",
  "start_s": 5.0,
  "text": "Find a comfortable position. Breathe in slowly.",
  "voice": "en_US-lessac-medium",
  "backend": "piper_local",
  "gain_db": 0.0,
  "pan": 0.0
}
```

**Validation:**
- `track_id` references an existing AudioTrack on the project with `kind="voice"`.
- `start_s` ≥ 0 and within project duration.
- `voice` valid for the chosen backend (validated against catalogue at request time).
- `backend` ∈ `{piper_local, openrouter_kokoro, openrouter_commercial}`.
- `openrouter_commercial` requires the OpenRouter privacy setting to allow commercial models AND `STOAT_OPENROUTER_API_KEY` configured.
- `text` length ≤ 5000 chars (per provider limits; configurable).

**Response: 201 Created.**

```json
{
  "cue_id": "uuid",
  "project_id": "uuid",
  "track_id": "voice",
  "start_s": 5.0,
  "text": "...",
  "voice": "en_US-lessac-medium",
  "backend": "piper_local",
  "gain_db": 0.0,
  "pan": 0.0,
  "cache_key": "sha256-hex",
  "generated_asset_id": null,
  "status": "pending",
  "error": null,
  "created_at": "...",
  "updated_at": "..."
}
```

#### `GET /projects/{p}/tts_cues`

NEW. Lists cues for a project. Optional `?track_id=` filter.

#### `GET /projects/{p}/tts_cues/{cue_id}`

NEW. Returns a single cue with current status (useful for polling synth progress).

#### `DELETE /projects/{p}/tts_cues/{cue_id}`

NEW. Deletes a cue. If a generated asset exists for this cue's cache_key and is not referenced by other cues, the asset is also soft-deleted.

#### `POST /projects/{p}/tts_cues/{cue_id}/synthesise` (optional explicit trigger)

NEW. Triggers synthesis without rendering. Returns 202 Accepted. Status transitions: `pending → synthesising → ready` (or `failed`). The render preflight will also auto-trigger synthesis for any unresolved cues; this endpoint is for UI eager-loading.

#### Voice catalogue endpoint

#### `GET /tts/voices`

NEW. Returns the merged voice catalogue:

```json
{
  "piper_local": [
    { "id": "en_US-lessac-medium", "language": "en-US", "gender": "female", "size_bytes": 95000000, "licence": "CC-BY-4.0" },
    ...
  ],
  "openrouter_kokoro": [
    { "id": "af_bella", "language": "en-US", "gender": "female" },
    ...
  ],
  "openrouter_commercial": [
    // dynamically discovered via OpenRouter /api/v1/models?output_modalities=speech
    // gated by the privacy switch; empty list when disabled
  ]
}
```

Per codex `18` smaller correction 5: do NOT hard-code commercial model slugs (`google/gemini-3.1-flash-tts-preview`, etc.) as ACs. The commercial catalogue is discovered at runtime via OpenRouter's models API, gated by the user's privacy setting.

**TTS cue → mixer routing.** Cues land on their `track_id`. The renderer (BL-505B) places each cue at `start_s` via `adelay=<ms>|<ms>` on the cue's generated asset; the cue's `track_id` participates in any DuckingPair where it's the `sidechain_track_id`, so voice cues automatically duck music.

### Soft subtitle render extension via `render_plan.settings` (BL-520)

**Endpoint:** existing `POST /render`.

**Per codex `18` Major Risk (render request migration):** the existing `CreateRenderRequest` uses `extra="forbid"`. New render-time options go into `render_plan.settings` rather than top-level fields. So soft subtitles live inside the serialised `render_plan`:

```json
{
  "project_id": "...",
  "output_format": "mp4",
  "quality_preset": "standard",
  "render_plan": "{\"settings\": {\"soft_subtitles\": [{\"source_asset_id\": \"uuid\", \"language\": \"en\", \"is_default\": true}, {\"source_asset_id\": \"uuid\", \"language\": \"es-ES\", \"is_default\": false}]}}"
}
```

A new `RenderPlanSettings` Pydantic model parses the `render_plan` JSON's `settings` block and validates the `soft_subtitles` list:

**Validation:**
- `output_format` must be `mp4` if `soft_subtitles` is non-empty (otherwise 422).
- `language` is BCP-47; rejected at API boundary if not in the supported BCP-47 → ISO-639-2/B mapping table.
- `source_asset_id` references a subtitle asset (kind=subtitle).
- First track defaults to `is_default=true` if none specified.

## New effect types added in Release 3

These all use the existing `POST /projects/{p}/clips/{c}/effects` endpoint. Their parameter schemas are validated against the existing JSON-schema registry (Release 1 pattern).

| Effect type | BL | Parameters (summary) |
|---|---|---|
| `zoompan` | BL-507 | z (zoom expr), x, y, d (duration), s (size) |
| `curves` | BL-508 | preset OR master/red/green/blue/all (KneeString) |
| `vignette` | BL-509 | angle, x0/y0 (or position+offsets), mode, eval |
| `hue_rotation` | BL-510 | H (hue expression), s (saturation), b (brightness) |
| `procedural_shape` | BL-513 | shape (Spiral/RadialBurst/Checkerboard/ConcentricRings), shape-specific params, size |
| `procedural_image` | BL-514 | expression, width, height, output_format, at_time |
| `subtitle_script` | BL-518 | entries (list of {start_s, end_s, text}), position (bottom/top/center, spec-level), font_size (spec-level), font_color (spec-level), optional font_file |
| `burned_subtitle` | BL-519 | source_asset_id (SRT or ASS), style overrides |
| ~~`tts_narration`~~ | ~~BL-516~~ | **REMOVED — TTS is modelled as a TtsCue on an audio track, NOT a per-clip effect.** See the TTS section above. |

Each ships with a registry entry including a `preview_fn` (returning the emitted filter string for `/effects/preview`) and a `build_fn` (called by the render-graph translator).

## OpenAPI schema

A regenerated `openapi.json` ships with Release 3 (per codex `18` Major Risk). The actual repo workflow (verified):

```bash
uv run python -m scripts.export_openapi
cd gui && npm run generate:types
```

Both commands MUST run together after any API route or schema change. CI checks `gui/openapi.json` freshness and `gui/src/generated/api-types.ts` freshness — they fail the PR if either is stale relative to the source. `AGENTS.md` documents this rule.

**Every API-changing BL in Release 3 gets a contract AC:**

- regenerate `gui/openapi.json` via `uv run python -m scripts.export_openapi`
- regenerate `gui/src/generated/api-types.ts` via `cd gui && npm run generate:types`
- include both regenerated files in the same PR as the schema/route change
- CI freshness checks pass

This AC applies to BL-499 (no schema change but verify nothing drifted), BL-505A (preflight response), BL-506-tech (evidence endpoint), BL-511 (clip_type enum), BL-515 (assets endpoints), BL-516 (TTS cue endpoints), BL-517 (audio_tracks endpoints), BL-520 (render_plan.settings extension), every effect-builder BL (preview endpoint surface), and any other Release 3 BL that touches Pydantic models or FastAPI routes.

## Backwards compatibility

- Existing endpoints receive **additive request/response schema changes only** (per codex `18` smaller correction 4). The signatures still match in the sense that no field is removed and no required field is added without a default. URL paths and status codes are unchanged.
- `RenderJobResponse` adds an `evidence` field that is `null` for jobs created before BL-506-tech landed (graceful for in-flight rollouts).
- The `clip_type` enum gains a new value (`image`) but rejects the new value when the worker version doesn't support image clips (preflight from BL-505A).
- **`CreateRenderRequest` extension rule (per codex `18` Major Risk):** the request model uses `model_config = ConfigDict(extra="forbid")` (verified in `src/stoat_ferret/api/schemas/render.py`). Any new render-time option goes into **`render_plan.settings`** (the serialised JSON's typed extension point), NOT a new top-level field — top-level fields are the stable public surface and shouldn't churn.
  - Concretely: `soft_subtitles` is moved from the proposed top-level field to `render_plan.settings.soft_subtitles`, parsed via a new `RenderPlanSettings` pydantic model that owns this extension surface.
  - Existing `delivery_profile` and the other Release 2 settings already live inside `render_plan`; this rule preserves that pattern.
- The `extra="forbid"` constraint on `CreateRenderRequest` is preserved.

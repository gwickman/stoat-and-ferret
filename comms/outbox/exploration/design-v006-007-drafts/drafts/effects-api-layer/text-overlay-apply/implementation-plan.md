# Implementation Plan: text-overlay-apply

## Overview

Create a POST endpoint to apply text overlay parameters to a clip, validate via the Rust drawtext builder, store the effect configuration in the clip model, return the generated FFmpeg filter string for transparency, and emit WebSocket events. This is the final feature in v006, consuming all prior features.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|---------|
| `src/stoat_ferret/api/routers/effects.py` | Modify | Add POST endpoint for text overlay application |
| `src/stoat_ferret/api/schemas/effect.py` | Modify | Add request/response models for text overlay apply |
| `src/stoat_ferret/api/websocket/events.py` | Modify | Add effect.applied and effect.removed event types to EventType enum |
| `src/stoat_ferret/api/app.py` | Modify | Register effect event types if needed during lifespan |
| `tests/test_api/test_effects.py` | Modify | Add endpoint tests for text overlay apply |
| `tests/test_blackbox/test_text_overlay_apply.py` | Create | Black box test for apply → verify flow |

## Implementation Stages

### Stage 1: Request/Response Models

1. Update `src/stoat_ferret/api/schemas/effect.py` with:
   - `TextOverlayRequest` model: text, position, font_size, font_color, shadow, box, fade_in, fade_out, enable_start, enable_end
   - `EffectApplyResponse` model: effect_id, clip_id, effect_config, filter_string, applied_at
   - Validation constraints matching Rust builder expectations

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "test_schema"
```

### Stage 2: POST Endpoint

1. Update `src/stoat_ferret/api/routers/effects.py` with:
   - `POST /clips/{clip_id}/effects/text-overlay` endpoint
   - Validate parameters via Rust drawtext builder (import from stoat_ferret_core)
   - On validation success: store effect config on clip via clip repository
   - On validation failure: return 422 with structured error from Rust
   - Response includes generated FFmpeg filter string for transparency

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "test_apply"
```

### Stage 3: WebSocket Events

1. Update `src/stoat_ferret/api/websocket/events.py`:
   - Add `EFFECT_APPLIED = "effect.applied"` to EventType enum
   - Add `EFFECT_REMOVED = "effect.removed"` to EventType enum
2. Emit events in the POST endpoint after successful effect application
3. Use existing `ws_manager` from `app.state` for event dispatch

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "test_websocket"
```

### Stage 4: Black Box Test

1. Create `tests/test_blackbox/test_text_overlay_apply.py` with:
   - End-to-end test: create project → add video → add clip → POST text overlay → GET clip → verify effect stored → verify filter string correct
   - Error case: POST with invalid parameters → verify 422 response
   - Tests use `httpx.AsyncClient` with test app (following existing blackbox test patterns)

**Verification:**
```bash
uv run pytest tests/test_blackbox/test_text_overlay_apply.py -v
```

## Test Infrastructure Updates

- New blackbox test file follows existing patterns in `tests/test_blackbox/`
- May need test fixtures for pre-populated clips with effects

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
```

## Risks

- Depends on clip-effect-model feature being complete for effect storage. See `comms/outbox/versions/design/v006/006-critical-thinking/risk-assessment.md`.
- Depends on drawtext-builder (Theme 02 Feature 002) for Rust validation and filter generation.
- Rust validation error surfacing requires careful error mapping from PyO3 exceptions to HTTP 422 responses.

## Commit Message

```
feat: create text overlay apply endpoint with filter preview

Add POST endpoint to apply text overlay to clips with Rust validation,
effect persistence, FFmpeg filter string transparency, and WebSocket
events. Includes black box test for end-to-end flow. Covers BL-043 (partial).
```

# Compose Router

**Source:** `src/stoat_ferret/api/routers/compose.py`
**Component:** API Gateway

## Purpose

Layout preset discovery and application endpoints. Manages predefined multi-input layouts (PIP, side-by-side, grid) and custom position composition with FFmpeg filter generation.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/compose/presets | List all layout presets |
| POST | /api/v1/projects/{project_id}/compose/layout | Apply layout preset or custom positions |

### Functions

- `list_presets() -> LayoutPresetListResponse`: Lists all available layout presets (PipTopLeft, PipTopRight, PipBottomLeft, PipBottomRight, SideBySide, TopBottom, Grid2x2) with metadata including description, AI hints, and min/max input counts.

- `apply_layout(project_id: str, request: LayoutRequest, http_request: Request) -> LayoutResponse`: Applies layout preset or custom positions. Resolves preset name to LayoutPosition array (or validates custom positions). Builds FFmpeg filter chain via Rust build_overlay_filter() for each position. Returns positioned elements and filter preview. Broadcasts LAYOUT_APPLIED event. 422 if preset unknown, inputs insufficient, or positions invalid.

### Helper Functions

- `_build_preset_list() -> list[LayoutPresetResponse]`: Builds preset response list from Rust LayoutPreset enum variants with metadata
- `_resolve_preset(preset_name: str, input_count: int) -> list[LayoutPosition]`: Looks up preset by name, checks input count >= min_inputs, calls Rust variant.positions(input_count). 422 if preset unknown or inputs insufficient.
- `_resolve_custom(positions: list[PositionModel]) -> list[LayoutPosition]`: Validates custom positions by constructing LayoutPosition instances and calling validate() on each. 422 if validation fails.

## Key Implementation Details

- **Rust integration**: LayoutPreset variants are Rust enums accessed via PyO3. Each variant has a positions() method returning LayoutPosition array.
- **Preset metadata**: Stored as list of tuples (LayoutPreset variant, metadata dict) because PyO3 enums are not hashable; mapped to dict for O(1) lookup by name
- **Position validation**: Custom positions validated via Rust LayoutPosition.validate() which checks coordinate bounds
- **Filter generation**: Rust build_overlay_filter() generates FFmpeg filter string for each position (takes output dimensions and timing parameters)
- **Filter preview**: All filter strings concatenated with semicolon (FFmpeg filter chain syntax)
- **WebSocket broadcast**: LAYOUT_APPLIED event includes project_id and preset name
- **Response schema**: Returns list of positioned elements with x, y, width, height, z_index plus concatenated filter preview string

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.compose.*`: LayoutPresetListResponse, LayoutPresetResponse, LayoutRequest, LayoutResponse, LayoutResponsePosition, PositionModel
- `stoat_ferret.api.websocket.events.EventType, build_event`: Event types and builder
- `stoat_ferret.api.websocket.manager.ConnectionManager`: WebSocket manager
- `stoat_ferret_core.*`: LayoutPosition, LayoutPreset, build_overlay_filter, LayoutError (Rust bindings)

### External Dependencies

- `fastapi`: APIRouter, HTTPException, Request, status
- `structlog`: Structured logging

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Rust core for layout computation and filter generation, WebSocket manager for broadcasting

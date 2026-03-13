# Effects Router

**Source:** `src/stoat_ferret/api/routers/effects.py`
**Component:** API Gateway

## Purpose

Effect discovery, preview, and application endpoints. Manages the catalog of video effects and transitions with parameter validation, filter string generation, and per-clip/project effect storage.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/effects | List all available effects |
| POST | /api/v1/effects/preview | Preview effect filter string |
| POST | /api/v1/projects/{project_id}/clips/{clip_id}/effects | Apply effect to clip |
| PATCH | /api/v1/projects/{project_id}/clips/{clip_id}/effects/{index} | Update clip effect |
| DELETE | /api/v1/projects/{project_id}/clips/{clip_id}/effects/{index} | Delete clip effect |
| POST | /api/v1/projects/{project_id}/effects/transition | Apply transition between clips |

### Functions

- `list_effects(registry: RegistryDep) -> EffectListResponse`: Lists all registered effects with metadata, parameter schemas, AI hints, and filter previews

- `preview_effect(request: EffectPreviewRequest, registry: RegistryDep) -> EffectPreviewResponse`: Previews the filter string for given effect type and parameters without persisting. Validates parameters and returns generated filter. 400 if effect unknown or parameters invalid.

- `apply_effect_to_clip(project_id: str, clip_id: str, request: EffectApplyRequest, registry: RegistryDep, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> EffectApplyResponse`: Applies effect to clip. Validates project/clip exist, effect type exists, parameters valid against JSON schema. Generates filter string via effect registry. Appends effect entry to clip.effects array and persists. Returns 201 Created. 404 if project/clip not found, 400 if validation fails.

- `update_clip_effect(project_id: str, clip_id: str, index: int, request: EffectUpdateRequest, registry: RegistryDep, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> EffectApplyResponse`: Updates effect at index in clip.effects. Validates index in bounds, parameters valid. Replaces effect entry in-place. 404 if project/clip/index not found, 400 if validation fails.

- `delete_clip_effect(project_id: str, clip_id: str, index: int, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> EffectDeleteResponse`: Removes effect at index from clip.effects array. 404 if project/clip/index not found.

- `apply_transition(project_id: str, request: TransitionRequest, registry: RegistryDep, project_repo: ProjectRepoDep, clip_repo: ClipRepoDep) -> TransitionResponse`: Applies transition between two clips. Validates clips exist, are adjacent in timeline order, transition type exists, parameters valid. Generates filter string. Appends transition to project.transitions. Increments Prometheus counter. Returns 201 Created. 400 if clips not adjacent or parameters invalid, 404 if clips not found.

### Dependency Functions

- `get_effect_registry(request: Request) -> EffectRegistry`: Returns injected registry or lazily creates default via create_default_registry()
- `_get_project_repository(request: Request) -> AsyncProjectRepository`
- `_get_clip_repository(request: Request) -> AsyncClipRepository`

## Key Implementation Details

- **Effect registry**: Pluggable registry supporting custom effect definitions. Falls back to default registry on first use (lazy initialization)
- **Parameter validation**: JSON schema validation via registry.validate() returns ValidationError list with path and message
- **Filter string generation**: Registry-provided build_fn() generates FFmpeg filter strings from parameters
- **Effect storage**: Effects stored as dicts on clip.effects list with keys: effect_type, parameters, filter_string
- **Transition storage**: Transitions stored as dicts on project.transitions list with keys: source_clip_id, target_clip_id, transition_type, parameters, filter_string
- **Adjacency check**: For clip transitions, verifies clips on same track and clip_a.timeline_end == clip_b.timeline_start
- **Metrics**: Counter tracks effect and transition applications by type
- **WebSocket broadcast**: Not broadcast here (but could be added)
- **Error detail**: Parameter validation errors include path/message array for client-side highlighting

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.effect.*`: EffectApplyRequest, EffectApplyResponse, EffectDeleteResponse, EffectListResponse, EffectPreviewRequest, EffectPreviewResponse, EffectResponse, EffectUpdateRequest, TransitionRequest, TransitionResponse
- `stoat_ferret.db.clip_repository.AsyncClipRepository, AsyncSQLiteClipRepository`: Clip persistence
- `stoat_ferret.db.project_repository.AsyncProjectRepository, AsyncSQLiteProjectRepository`: Project persistence
- `stoat_ferret.effects.definitions.create_default_registry`: Default effect registry factory
- `stoat_ferret.effects.registry.EffectRegistry`: Effect registry interface

### External Dependencies

- `fastapi`: APIRouter, Depends, HTTPException, Request, status
- `prometheus_client.Counter`: Effect/transition application metrics
- `structlog`: Structured logging

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Effect registry, project/clip repositories

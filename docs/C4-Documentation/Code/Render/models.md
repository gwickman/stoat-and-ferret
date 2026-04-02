# Render Models

**Source:** `src/stoat_ferret/render/models.py`
**Component:** Render Engine

## Purpose

Defines the render domain model: job status state machine, output formats, quality presets, and the RenderJob dataclass with validated state transitions. Provides a standalone transition validator to enforce the state machine at both model and repository levels.

## Public Interface

### Enums

- `RenderStatus`: Job status state machine
  - `QUEUED` -> `RUNNING` -> `COMPLETED` | `FAILED` | `CANCELLED`
  - `FAILED` -> `QUEUED` (retry)

- `OutputFormat`: Supported output container formats
  - `mp4`, `webm`, `mov`, `mkv`

- `QualityPreset`: Render quality levels
  - `draft`, `standard`, `high`

### Classes

- `RenderJob`: Dataclass representing a render job
  - `id: str` — UUID identifier
  - `project_id: str` — Associated project
  - `status: RenderStatus` — Current state (enforced by state machine)
  - `output_path: str` — Destination file path
  - `output_format: OutputFormat` — Container format
  - `quality_preset: QualityPreset` — Quality level
  - `render_plan: str` — JSON string containing the render plan
  - `progress: float` — 0.0 to 1.0 progress ratio
  - `error_message: str | None` — Failure reason (if failed)
  - `retry_count: int` — Number of retry attempts
  - `created_at: datetime` — Job creation timestamp
  - `updated_at: datetime` — Last status update timestamp
  - `completed_at: datetime | None` — Completion timestamp (if completed)

  **Factory Method:**
  - `create(project_id, output_path, output_format, quality_preset, render_plan) -> RenderJob`: Create new job in QUEUED status with generated UUID

  **State Transition Methods:**
  - `update_progress(progress: float) -> None`: Validate bounds [0, 1.0], update progress and updated_at
  - `complete() -> None`: Validate transition, set progress=1.0, set completed_at
  - `fail(error_message: str) -> None`: Validate transition, store error message
  - `retry() -> None`: Reset progress and error_message, increment retry_count, transition to QUEUED
  - `cancel() -> None`: Validate transition to CANCELLED

### Functions

- `validate_render_transition(current: RenderStatus, new: RenderStatus) -> None`: Validate a state transition against the allowed transition map; raises ValueError on invalid transitions

## Dependencies

### External Dependencies

- `dataclasses`: Dataclass decorator
- `enum`: Enum base class
- `datetime`: Timestamps
- `uuid`: Job ID generation

## Key Implementation Details

### State Machine Enforcement

The allowed transitions map defines valid status changes:
```
QUEUED   -> RUNNING, CANCELLED
RUNNING  -> COMPLETED, FAILED, CANCELLED
FAILED   -> QUEUED (retry)
```

`validate_render_transition()` is called by both model methods and the repository layer, providing defense-in-depth against invalid state changes.

### Progress Bounds Validation

`update_progress()` clamps the value to [0.0, 1.0] and raises ValueError if the input is outside this range, preventing nonsensical progress reporting.

### Immutable Factory

`RenderJob.create()` generates a UUID, sets initial status to QUEUED, progress to 0.0, retry_count to 0, and timestamps to `datetime.now(timezone.utc)`.

## Relationships

- **Used by:** RenderService, RenderQueue, RenderExecutor, AsyncRenderRepository, API Gateway (render router schemas)
- **Uses:** Python stdlib only (no internal dependencies)

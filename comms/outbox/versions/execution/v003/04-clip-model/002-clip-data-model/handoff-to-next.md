# Handoff: 002-clip-data-model

## What Was Completed

The Clip data model with Rust validation is now in place. This provides the foundation for representing video segments on a timeline.

## Key Implementation Decisions

1. **ClipValidationError as Python Exception**: The Rust `ClipValidationError` is a data class (struct), not an exception. Created a Python exception class that wraps it, allowing standard Python exception handling.

2. **Validation via Rust Core**: Clip validation delegates to `validate_clip()` from the Rust core library. This ensures frame-accurate validation using the same logic as the timeline engine.

3. **Foreign Key Constraints**:
   - `project_id` -> CASCADE DELETE (clips deleted when project deleted)
   - `source_video_id` -> RESTRICT DELETE (can't delete video if clips reference it)

4. **Timeline Position**: The `timeline_position` field is in frames and represents where the clip starts on the timeline. Combined with `in_point` and `out_point`, this defines the complete clip placement.

## What the Next Feature Needs to Know

1. **Imports Available**:
   ```python
   from stoat_ferret.db import Clip, ClipValidationError
   ```

2. **Validation API**:
   ```python
   clip = Clip(...)
   try:
       clip.validate(source_path="/path/to/video.mp4", source_duration_frames=1000)
   except ClipValidationError as e:
       print(f"Field: {e.field}, Message: {e.message}")
   ```

3. **No Repository Yet**: A `ClipRepository` has not been implemented. The next feature should add this following the existing pattern (`AsyncSQLiteClipRepository`, `AsyncInMemoryClipRepository`).

## Integration Points for Next Features

- **Clip Repository**: Will need CRUD operations for clips
- **Timeline Model**: Will aggregate clips with ordering and collision detection
- **API Endpoints**: Will need clip CRUD endpoints using the repository
- **Clip Overlap Detection**: Use Rust `TimeRange` operations for detecting clip overlaps

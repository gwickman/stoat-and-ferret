# Handoff: 001-project-data-model

## What Was Completed

The Project data model and repository infrastructure is now in place. This provides the foundation for organizing video clips into projects.

## Key Implementation Decisions

1. **Dataclass over SQLAlchemy ORM**: Followed existing pattern of using plain Python dataclasses for models rather than SQLAlchemy ORM, keeping the codebase simple.

2. **Async-only repositories**: Only added async repository implementations (AsyncSQLiteProjectRepository, AsyncInMemoryProjectRepository) since the existing codebase already has the async pattern established for FastAPI integration.

3. **Output settings as integers**: Using integer types for `output_width`, `output_height`, and `output_fps` (not Fraction or complex frame rate types) to keep the model simple for the MVP.

## What the Next Feature Needs to Know

1. **Database migration**: The `projects` table exists and has defaults for output settings (1920x1080@30fps).

2. **Repository pattern**: Use `AsyncSQLiteProjectRepository` or `AsyncInMemoryProjectRepository` following the same pattern as the video repositories.

3. **Timestamps**: Projects track `created_at` and `updated_at` as ISO datetime strings in SQLite.

4. **Imports available**:
   ```python
   from stoat_ferret.db import (
       Project,
       AsyncProjectRepository,
       AsyncSQLiteProjectRepository,
       AsyncInMemoryProjectRepository,
   )
   ```

## Integration Points for Next Features

- **Clip model** (likely next): Will need a `project_id` foreign key to associate clips with projects
- **API endpoints**: Will need to create project CRUD endpoints using the repository
- **Timeline model**: Timeline should reference a project for output settings

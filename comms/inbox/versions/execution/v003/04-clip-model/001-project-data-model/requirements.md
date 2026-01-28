# Project Data Model

## Goal
Create minimal Project model for organizing clips.

## Requirements

### FR-001: Project Model
Create `src/stoat_ferret/db/models.py` with Project:
- id: str (UUID)
- name: str
- output_width: int (default 1920)
- output_height: int (default 1080)
- output_fps: int (default 30)
- created_at: datetime
- updated_at: datetime

### FR-002: Database Schema
Add projects table via Alembic migration.

### FR-003: Project Repository
Create async ProjectRepository with CRUD operations.

### FR-004: InMemory Implementation
Create AsyncInMemoryProjectRepository for testing.

## Acceptance Criteria
- [ ] Project model defined
- [ ] Alembic migration creates table
- [ ] AsyncProjectRepository protocol defined
- [ ] AsyncSQLiteProjectRepository implementation complete
- [ ] AsyncInMemoryProjectRepository implementation complete
- [ ] Contract tests pass
# Implementation Plan: Clips API

## Step 1: Create Schemas
Create `src/stoat_ferret/api/schemas/project.py` with ProjectCreate, ProjectResponse, ProjectListResponse.
Create `src/stoat_ferret/api/schemas/clip.py` with ClipCreate, ClipUpdate, ClipResponse, ClipListResponse.

## Step 2: Create Projects Router
Create `src/stoat_ferret/api/routers/projects.py` with:
- get_project_repository and get_clip_repository dependency functions
- Project CRUD endpoints (list, create, get, delete)
- Clip endpoints nested under projects (list, create, update, delete)
- Rust validation before clip save using FrameRate from project

## Step 3: Register Router
Update `src/stoat_ferret/api/app.py` to include projects router.

## Step 4: Update Test Fixtures
Update `tests/test_api/conftest.py` to include project and clip repository overrides.

## Step 5: Add Tests
Create `tests/test_api/test_projects.py` and `tests/test_api/test_clips.py`.

## Verification
- Project CRUD works
- Clip CRUD works
- Invalid clips rejected with validation error
- `uv run pytest tests/test_api/ -m api` passes
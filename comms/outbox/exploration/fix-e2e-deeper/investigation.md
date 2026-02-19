# Investigation Trail

## Starting Point

The E2E test `project-creation.spec.ts` line 41 fails with a `toBeHidden`
timeout on the `create-project-modal`. This happens consistently in CI
across multiple PRs and on main. Previous fix attempts (waitForResponse +
10s timeout) did not help.

## Step 1: Trace the E2E Test Flow

The test:
1. Navigates to `/gui/`, clicks Projects tab
2. Opens the create-project modal
3. Fills name, resolution, FPS
4. Clicks "Create" which fires `POST /api/v1/projects`
5. Waits for modal to become hidden

The modal (`CreateProjectModal.tsx`) calls `createProject()` from
`useProjects.ts`, which does a `fetch('/api/v1/projects', { method: 'POST' })`.
On success, it calls `onClose()` (modal hides). On error, it sets
`submitError` and the modal stays open.

**Key insight**: the modal stays open because the POST **fails**, not because
the server is slow.

## Step 2: Check the API Endpoint

`src/stoat_ferret/api/routers/projects.py` - the `create_project` handler
creates a `Project` dataclass, calls `repo.add(project)`. The repository is
`AsyncSQLiteProjectRepository`.

## Step 3: Check the Repository SQL

`src/stoat_ferret/db/project_repository.py` line 106-124:

```python
await self._conn.execute(
    """
    INSERT INTO projects (
        id, name, output_width, output_height, output_fps,
        transitions_json, created_at, updated_at
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """,
    (project.id, project.name, project.output_width, ...
     transitions_json, ...)
)
```

The INSERT references `transitions_json`.

## Step 4: Check the Migration

`alembic/versions/4488866d89cc_add_projects_table.py`:

```sql
CREATE TABLE projects (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    output_width INTEGER NOT NULL DEFAULT 1920,
    output_height INTEGER NOT NULL DEFAULT 1080,
    output_fps INTEGER NOT NULL DEFAULT 30,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
```

**No `transitions_json` column.** The column exists in `schema.py` (used for
local dev `create_tables()`) but was never added to the alembic migration.

Same issue: `clips` migration omits `effects_json` but
`AsyncSQLiteClipRepository` references it.

## Step 5: Verify the CI Path

CI E2E job:
1. `uv run alembic upgrade head` -> creates DB from migrations (no column)
2. Playwright starts uvicorn -> server connects to that DB
3. E2E test POSTs -> repository INSERT fails -> `OperationalError:
   table projects has no column named transitions_json`
4. FastAPI returns 500 -> modal stays open -> assertion times out

## Step 6: Why It Might Work Locally

Local development databases may have been created via `schema.py`'s
`create_tables()` function, which includes the columns. Or the dev may
have run the app before the column was added to the repository code and
never recreated the DB from scratch.

Confirmed: the local `data/stoat.db` was also missing the columns (it was
created via alembic too) and needed `alembic upgrade head` after the fix.

## Ruled Out

- **Timing/slowness**: Not the issue. The API returns 500 immediately.
- **Rust module**: `Project.new_id()` uses `uuid.uuid4()`, no Rust dependency.
  The Rust module is only used in `Clip.validate()`.
- **Database path**: CWD is correct; `cd .. && uv run uvicorn` from `gui/`
  resolves `data/stoat.db` to the repo root where alembic created it.
- **Missing `maturin develop` in E2E CI**: Not relevant for project creation.

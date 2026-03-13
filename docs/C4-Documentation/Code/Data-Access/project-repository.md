# Project Repository

**Source:** `src/stoat_ferret/db/project_repository.py`
**Component:** Data Access

## Purpose

Provides asynchronous repository pattern implementations for project metadata storage. Defines AsyncProjectRepository protocol and offers two implementations: AsyncSQLiteProjectRepository for production use and AsyncInMemoryProjectRepository for testing. Handles project CRUD operations including serialization of JSON fields (transitions and audio_mix).

## Public Interface

### Protocols

- `AsyncProjectRepository`
  - Abstract protocol defining asynchronous project repository operations
  - Methods:
    - `async add(project: Project) -> Project` — Add a new project, raises ValueError if duplicate ID
    - `async get(id: str) -> Project | None` — Get project by ID
    - `async list_projects(limit: int = 100, offset: int = 0) -> list[Project]` — Paginated list ordered by creation date descending
    - `async update(project: Project) -> Project` — Update existing project, raises ValueError if not found
    - `async delete(id: str) -> bool` — Delete project by ID, returns True if deleted
    - `async count() -> int` — Return the total number of projects in the repository (FR-002 requirement)

### Classes

- `AsyncSQLiteProjectRepository`
  - Async SQLite implementation of AsyncProjectRepository protocol
  - `__init__(conn: aiosqlite.Connection) -> None`
    - Initialize with async SQLite connection
  - `async add(project: Project) -> Project` — INSERT into projects table
    - Serializes transitions and audio_mix to JSON strings
    - Raises ValueError on IntegrityError (duplicate ID)
  - `async get(id: str) -> Project | None` — SELECT by id
  - `async list_projects(limit: int = 100, offset: int = 0) -> list[Project]` — SELECT with pagination, ordered by created_at DESC
  - `async update(project: Project) -> Project` — UPDATE all fields
    - Serializes transitions and audio_mix to JSON strings
    - Raises ValueError if project not found (rowcount == 0)
  - `async delete(id: str) -> bool` — DELETE by id, returns True if deleted
  - `async count() -> int` — SELECT COUNT(*) FROM projects, returns total count (FR-002)
  - `_row_to_project(row: Any) -> Project` — Convert database row to Project object (sync helper)
    - Deserializes JSON fields back to dicts

- `AsyncInMemoryProjectRepository`
  - Async in-memory test implementation
  - All public methods are async (return awaitable results)
  - Uses `copy.deepcopy()` to isolate internal state from caller mutations
  - Maintains single index: `_projects` (id → Project)
  - `__init__() -> None` — Initialize empty repository
  - `async add(project: Project) -> Project` — Store deepcopy in _projects
    - Raises ValueError if project ID already exists
  - `async get(id: str) -> Project | None` — Retrieve deepcopy from _projects
  - `async list_projects(limit: int = 100, offset: int = 0) -> list[Project]` — Return paginated deepcopies sorted by created_at DESC
  - `async update(project: Project) -> Project` — Update _projects with deepcopy
    - Raises ValueError if project not found
  - `async delete(id: str) -> bool` — Remove from _projects, returns True if deleted
  - `async count() -> int` — Return len(self._projects) (FR-002)
  - `seed(projects: list[Project]) -> None` — Populate repository with initial test data (deepcopies)

## Dependencies

- **stoat_ferret.db.models**: Project dataclass
- **aiosqlite**: Async SQLite wrapper providing aiosqlite.Connection and aiosqlite.Row
- **json**: For serializing/deserializing transitions_json and audio_mix_json
- **datetime**: For Project timestamp fields
- **copy**: For deepcopy isolation in in-memory repository
- **typing**: For type hints (Protocol, Any, TYPE_CHECKING)

## Key Implementation Details

### JSON Serialization

- **transitions** field: Serialized to `transitions_json` (TEXT column)
  - None is stored as NULL
  - Deserialized back to dict on retrieval
  - Example: `[{"type": "fade", "duration": 0.5}]`

- **audio_mix** field: Serialized to `audio_mix_json` (TEXT column)
  - None is stored as NULL
  - Deserialized back to dict on retrieval
  - Example: `{"master_volume": 1.0, "tracks": {...}}`
  - This column was added via migration in schema.py

### Async/Await Pattern

- All public methods are async and must be awaited
- Uses `await self._conn.execute()`, `await cursor.fetchone()`, `await cursor.fetchall()` for database operations
- Uses `await self._conn.commit()` to persist changes

### Count Operation (FR-002)

- `count()` method implements requirement FR-002 for project count tracking
- AsyncSQLiteProjectRepository: `SELECT COUNT(*) FROM projects` returns total count
- AsyncInMemoryProjectRepository: `len(self._projects)` returns total count
- Used by application code to track project inventory and enforce limits

### Deepcopy Isolation

- AsyncInMemoryProjectRepository stores and returns deepcopies to prevent external mutations
- Prevents bugs where test code modifies returned objects and affects internal state

### Cascade Delete

- When a project is deleted, all its clips and tracks cascade delete (defined in schema)
- Project versions remain but become orphaned (no CASCADE defined for project_versions at schema level)

### Pagination

- list_projects() returns projects ordered by created_at DESC (newest first)
- Supports limit and offset for pagination
- Consistent with other repository implementations

## Relationships

- **Used by:**
  - FastAPI application lifespan (dependency injection in app.state)
  - Async service layer for project metadata operations
  - API route handlers for project endpoints (async route handlers)
  - Tests that need async project repository behavior

- **Uses:**
  - models.Project — the primary data model
  - schema (indirectly) — depends on projects table schema definition
  - json — for serialization/deserialization of complex fields

- **Associated entities:**
  - clip_repository.AsyncSQLiteClipRepository — clips are deleted with project
  - timeline_repository.AsyncSQLiteTimelineRepository — tracks are deleted with project
  - version_repository.AsyncSQLiteVersionRepository — versions associated with project (not deleted)

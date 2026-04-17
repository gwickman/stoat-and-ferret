# Phase 6: Deployment & Testability Data Models

## Rust Structs

### Version Info (exposed via PyO3)

```rust
/// Build and version metadata exposed to Python via PyO3
#[pyclass]
pub struct VersionInfo {
    #[pyo3(get)]
    pub core_version: String,      // from Cargo.toml
    #[pyo3(get)]
    pub build_timestamp: String,   // compile-time env
    #[pyo3(get)]
    pub git_sha: Option<String>,   // compile-time env
}

#[pymethods]
impl VersionInfo {
    #[staticmethod]
    pub fn current() -> Self { /* read from build env */ }
}
```

### Schema Introspection

```rust
/// Describes a single parameter for AI discovery
#[pyclass]
pub struct ParameterSchema {
    #[pyo3(get)]
    pub name: String,
    #[pyo3(get)]
    pub param_type: String,        // "float", "int", "string", "enum"
    #[pyo3(get)]
    pub default_value: Option<String>,
    #[pyo3(get)]
    pub min_value: Option<f64>,
    #[pyo3(get)]
    pub max_value: Option<f64>,
    #[pyo3(get)]
    pub enum_values: Option<Vec<String>>,
    #[pyo3(get)]
    pub description: String,
    #[pyo3(get)]
    pub ai_hint: Option<String>,   // natural-language usage hint for AI agents
}
```

## Pydantic Models

### System State Snapshot

```python
class SystemStateSnapshot(BaseModel):
    """Denormalised read-only view of system state for external agents."""
    timestamp: datetime
    projects: list[ProjectSummary]
    active_jobs: list[JobSummary]
    preview_sessions: list[PreviewSessionSummary]
    queue_status: QueueStatus
    health: HealthStatus

class ProjectSummary(BaseModel):
    id: str
    name: str
    clip_count: int
    track_count: int
    last_modified: datetime

class JobSummary(BaseModel):
    id: str
    job_type: str          # "scan", "render", "proxy", "thumbnail", "waveform"
    status: str
    progress: float | None
    created_at: datetime

class PreviewSessionSummary(BaseModel):
    session_id: str
    project_id: str
    status: str
    created_at: datetime

class QueueStatus(BaseModel):
    pending: int
    running: int
    completed_last_hour: int
```

### Seed Fixture

```python
class SeedFixtureRequest(BaseModel):
    """Request to seed test data. Only available when STOAT_TESTING_MODE=true."""
    fixture_name: str              # "minimal", "full", "render-ready"
    project_count: int = 1
    videos_per_project: int = 2
    include_render_jobs: bool = False
    include_proxy_files: bool = False

class SeedFixtureResponse(BaseModel):
    seeded: bool
    project_ids: list[str]
    video_ids: list[str]
    message: str
```

### Version Endpoint

```python
class VersionResponse(BaseModel):
    app_version: str               # from pyproject.toml
    core_version: str              # from Rust VersionInfo
    build_timestamp: str | None
    git_sha: str | None
    python_version: str
    database_version: int          # current migration number

class HealthStatus(BaseModel):
    live: bool
    ready: bool
    database: str                  # "ok" | "degraded" | "down"
    rust_core: str                 # "ok" | "unavailable"
```

### Feature Flags

```python
class FeatureFlags(BaseModel):
    """Read from environment at startup. Immutable at runtime."""
    testing_mode: bool = False         # STOAT_TESTING_MODE
    seed_endpoint: bool = False        # STOAT_ENABLE_SEED (requires testing_mode)
    synthetic_monitoring: bool = False # STOAT_SYNTHETIC_MONITORING
    batch_rendering: bool = True       # STOAT_BATCH_RENDERING (already exists)
```

### Workspace Layout

```python
class WorkspaceLayout(BaseModel):
    """Persisted in localStorage, not SQLite."""
    preset: str                    # "edit", "review", "render", "custom"
    panels: list[PanelConfig]

class PanelConfig(BaseModel):
    panel_id: str                  # "library", "timeline", "preview", "effects", "render"
    visible: bool
    size_percent: float            # CSS Grid fraction
    position: int                  # order in layout
```

## SQLite Schema Additions

### Feature Flags Audit

```sql
-- Track feature flag state at startup for operational audit
CREATE TABLE IF NOT EXISTS feature_flag_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    flag_name TEXT NOT NULL,
    flag_value TEXT NOT NULL,
    logged_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

### Migration Safety

```sql
-- Track migration history with rollback info
CREATE TABLE IF NOT EXISTS migration_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL,
    applied_at TEXT NOT NULL DEFAULT (datetime('now')),
    backup_path TEXT,              -- path to pre-migration backup
    rollback_sql TEXT,             -- SQL to reverse this migration
    status TEXT NOT NULL DEFAULT 'applied' -- 'applied', 'rolled_back'
);
```

## Config Extensions

```python
# additions to Settings (src/stoat_ferret/config.py)
class Settings(BaseSettings):
    # ... existing fields ...

    # Phase 6: Deployment
    testing_mode: bool = False
    enable_seed_endpoint: bool = False
    synthetic_monitoring: bool = False
    migration_backup_dir: str = "data/backups"

    # Phase 6: WebSocket replay
    ws_replay_buffer_size: int = 1000
    ws_replay_ttl_seconds: int = 300
```

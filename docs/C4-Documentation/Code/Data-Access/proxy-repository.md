# Proxy Repository

**Source:** `src/stoat_ferret/db/proxy_repository.py`
**Component:** Data Access

## Purpose

Provides asynchronous repository pattern implementations for proxy file persistence. Defines AsyncProxyRepository protocol and offers two implementations: SQLiteProxyRepository for production use and InMemoryProxyRepository for testing. Handles proxy file CRUD operations with strict status transition validation, access tracking, and proxy cache management (count, total size, oldest access).

## Public Interface

### Protocols

- `AsyncProxyRepository`
  - Abstract protocol defining asynchronous proxy file repository operations
  - Methods:
    - `async add(proxy: ProxyFile) -> ProxyFile` — Add a new proxy file record
    - `async get(proxy_id: str) -> ProxyFile | None` — Get a proxy file by ID
    - `async get_by_video_and_quality(source_video_id: str, quality: ProxyQuality) -> ProxyFile | None` — Get proxy by video and quality
    - `async list_by_video(source_video_id: str) -> list[ProxyFile]` — List all proxy files for a source video
    - `async update_status(proxy_id: str, status: ProxyStatus, *, file_size_bytes: int | None = None) -> None` — Update proxy status with transition validation
    - `async delete(proxy_id: str) -> bool` — Delete a proxy file record
    - `async count() -> int` — Count all proxy file records
    - `async total_size_bytes() -> int` — Get total size of all proxy files in bytes
    - `async count_by_status(status: ProxyStatus) -> int` — Count proxies with a given status
    - `async get_oldest_accessed() -> ProxyFile | None` — Get the oldest-accessed ready proxy

### Classes

- `SQLiteProxyRepository`
  - Async SQLite implementation of AsyncProxyRepository protocol
  - `__init__(conn: aiosqlite.Connection) -> None`
    - Initialize with async SQLite connection
    - Sets row_factory to aiosqlite.Row for named column access
  - `async add(proxy: ProxyFile) -> ProxyFile` — INSERT into proxy_files table
    - Serializes ProxyQuality and ProxyStatus enums to string values
    - Serializes datetime fields to ISO format strings
    - Enforces unique constraint on (source_video_id, quality)
    - Raises ValueError if proxy for same video/quality already exists (IntegrityError wrapper)
  - `async get(proxy_id: str) -> ProxyFile | None` — SELECT by id
  - `async get_by_video_and_quality(source_video_id: str, quality: ProxyQuality) -> ProxyFile | None` — SELECT by video and quality
  - `async list_by_video(source_video_id: str) -> list[ProxyFile]` — SELECT proxies for a video
    - Returns proxies ordered by quality (ascending)
  - `async update_status(proxy_id: str, status: ProxyStatus, *, file_size_bytes: int | None = None) -> None` — UPDATE proxy status
    - Validates status transition
    - Sets generated_at to now when transitioning to READY status
    - Updates last_accessed_at to current time on every call
    - Optionally updates file_size_bytes (typically when transitioning to ready)
    - Raises ValueError if proxy not found or transition invalid
  - `async delete(proxy_id: str) -> bool` — DELETE by id
    - Returns True if deleted, False if not found
  - `async count() -> int` — SELECT COUNT(*) FROM proxy_files
  - `async total_size_bytes() -> int` — SELECT SUM(file_size_bytes) FROM proxy_files
    - Returns 0 if no proxies exist
  - `async count_by_status(status: ProxyStatus) -> int` — SELECT COUNT(*) WHERE status = ?
  - `async get_oldest_accessed() -> ProxyFile | None` — SELECT oldest ready proxy by last_accessed_at
    - Only considers proxies with status 'ready'
    - Used for proxy cache eviction (LRU-like policy)
  - `_row_to_proxy(row: aiosqlite.Row) -> ProxyFile` — Convert database row to ProxyFile
    - Deserializes enum values back from strings
    - Converts ISO format strings back to datetime objects
    - Handles nullable generated_at field

- `InMemoryProxyRepository`
  - In-memory test implementation
  - All public methods are async (return awaitable results)
  - Uses `copy.deepcopy()` to isolate internal state from caller mutations
  - Maintains index: `_proxies` (proxy_id → ProxyFile)
  - `__init__() -> None` — Initialize empty repository
  - `async add(proxy: ProxyFile) -> ProxyFile` — Store deepcopy in _proxies
    - Enforces unique constraint on (source_video_id, quality) by checking all existing proxies
    - Raises ValueError if proxy for same video/quality already exists
    - Returns deepcopy to prevent external mutations
  - `async get(proxy_id: str) -> ProxyFile | None` — Return deepcopy from _proxies
  - `async get_by_video_and_quality(source_video_id: str, quality: ProxyQuality) -> ProxyFile | None` — Search _proxies for matching video/quality
    - Returns deepcopy if found, None otherwise
  - `async list_by_video(source_video_id: str) -> list[ProxyFile]` — Return deepcopies for a video
    - Sorted by quality (ascending)
  - `async update_status(proxy_id: str, status: ProxyStatus, *, file_size_bytes: int | None = None) -> None` — Update _proxies entry
    - Validates status transition
    - Sets generated_at to now when transitioning to READY status
    - Updates last_accessed_at to current time on every call
    - Updates file_size_bytes if provided
    - Raises ValueError if proxy not found or transition invalid
  - `async delete(proxy_id: str) -> bool` — Remove from _proxies
    - Returns True if deleted, False if not found
  - `async count() -> int` — Return len(self._proxies)
  - `async total_size_bytes() -> int` — Sum of file_size_bytes across all proxies
  - `async count_by_status(status: ProxyStatus) -> int` — Count of proxies matching status
  - `async get_oldest_accessed() -> ProxyFile | None` — Get deepcopy of oldest ready proxy by last_accessed_at
    - Returns None if no ready proxies exist

### Helper Functions

- `_validate_status_transition(current: str, new: str) -> None`
  - Validates that a status transition is allowed
  - Enforces state machine: pending → (generating | failed) → ready | stale
  - Raises ValueError with detailed message if transition invalid

## Dependencies

- **stoat_ferret.db.models**: ProxyFile, ProxyQuality, ProxyStatus
- **aiosqlite**: Async SQLite wrapper providing aiosqlite.Connection and aiosqlite.Row
- **datetime**: For timestamp fields (generated_at, last_accessed_at, created_at)
- **copy**: For deepcopy isolation in in-memory repository
- **typing**: For Protocol and runtime_checkable
- **structlog**: For logging proxy repository operations

## Key Implementation Details

### Status Transitions

Valid transitions are strictly enforced:
```
pending -> generating -> ready
pending -> generating -> failed
ready -> stale
```

Terminal states (failed, stale) have no further transitions. Any attempt to transition outside this state machine raises ValueError with details of allowed next states.

### Proxy Uniqueness

- Each (source_video_id, quality) pair is unique
- A video cannot have multiple proxies at the same quality level
- This is enforced at the database level via UNIQUE constraint
- InMemoryProxyRepository enforces this during add() by checking all existing proxies

### Generated At Tracking

- `generated_at` is NULL until the proxy is ready
- Set to current UTC time when status transitions to READY
- Used to distinguish newly-generated proxies from old/stale ones

### Access Tracking

- `last_accessed_at` is updated on every status update (not just generation)
- Used for LRU-like cache eviction via `get_oldest_accessed()`
- Proxy systems can use this to evict least-recently-used proxies when cache is full

### Cache Management Queries

- `count()` — Get total number of proxies in cache
- `total_size_bytes()` — Get disk space used by all proxies
- `count_by_status()` — Get count of generating/ready proxies for resource planning
- `get_oldest_accessed()` — Get least-recently-used ready proxy for eviction

These queries support cache management strategies without needing to fetch all proxy records.

### Enum Serialization

- **ProxyQuality**: Stored as string in database (e.g., "high")
  - Deserialized back to enum on retrieval via ProxyQuality(value)
- **ProxyStatus**: Stored as string in database (e.g., "ready")
  - Deserialized back to enum on retrieval via ProxyStatus(value)

### Deepcopy Isolation

- InMemoryProxyRepository stores and returns deepcopies to prevent test code from accidentally mutating internal state
- Each returned record is independent and changes won't affect future queries

## Relationships

- **Used by:**
  - Proxy generation service for proxy lifecycle management
  - Media player API endpoints for proxy file serving
  - Cache eviction service for LRU-based cleanup
  - Monitoring/analytics for cache statistics

- **Uses:**
  - models.ProxyFile — the primary data model
  - models.ProxyQuality — quality level enum
  - models.ProxyStatus — status lifecycle enum
  - aiosqlite — async database operations
  - datetime — timestamp management

- **Associated entities:**
  - Videos (via source_video_id FK) — each proxy is generated from a source video
  - Projects (indirectly through clips that reference videos) — proxies are used in editing

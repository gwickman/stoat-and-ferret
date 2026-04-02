# Encoder Cache

**Source:** `src/stoat_ferret/render/encoder_cache.py`
**Component:** Render Engine

## Purpose

Caches FFmpeg hardware encoder detection results in SQLite to avoid repeated subprocess calls. Provides a protocol-based repository abstraction with SQLite and in-memory implementations.

## Public Interface

### Classes

- `EncoderCacheEntry`: Dataclass for cached encoder information
  - `id: int | None` — Database row ID
  - `name: str` — Encoder name (e.g., "h264_nvenc")
  - `codec: str` — Codec family (e.g., "h264")
  - `is_hardware: bool` — Whether this is a hardware encoder
  - `encoder_type: str` — Encoder technology (e.g., "Nvenc", "QSV", "AMF", "VideoToolbox")
  - `description: str` — Human-readable description
  - `detected_at: datetime` — Timestamp of detection

### Protocols

- `AsyncEncoderCacheRepository`: Protocol for encoder cache persistence
  - `get_all() -> list[EncoderCacheEntry]`: Retrieve all cached encoders
  - `create_many(entries: list[EncoderCacheEntry]) -> list[EncoderCacheEntry]`: Bulk-insert encoder entries
  - `clear() -> None`: Truncate the cache (used before refresh)

### Implementations

- `AsyncSQLiteEncoderCacheRepository`: Production SQLite implementation
  - `__init__(connection: aiosqlite.Connection) -> None`: Initialize with database connection

- `InMemoryEncoderCacheRepository`: Test double using in-memory list

## Dependencies

### External Dependencies

- `aiosqlite`: Async SQLite access (production implementation)
- `dataclasses`: Dataclass decorator
- `datetime`: Timestamp tracking

## Key Implementation Details

### Cache Lifecycle

1. On first `GET /api/v1/render/encoders`, the cache is checked via `get_all()`
2. If empty, encoder detection runs (FFmpeg subprocess) and results are stored via `create_many()`
3. On `POST /api/v1/render/encoders/refresh`, `clear()` is called before re-detection and `create_many()`

### Database Schema

Operates on the `encoder_cache` table with columns matching `EncoderCacheEntry` fields. The `detected_at` timestamp enables cache age tracking.

## Relationships

- **Used by:** API Gateway (render router encoder endpoints)
- **Uses:** SQLite database (encoder_cache table)

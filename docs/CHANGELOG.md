# Changelog

All notable changes to stoat-and-ferret will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [v003] - 2026-01-28

API Layer + Clip Model (Roadmap M1.6-1.7). Establishes FastAPI REST API, async repository layer, video library endpoints, clip/project data models with Rust validation, and CI improvements.

### Added

- **Process Improvements**
  - `AsyncVideoRepository` protocol with async SQLite and in-memory implementations
  - CI migration verification step (upgrade → downgrade → upgrade)
  - CI path filters using `dorny/paths-filter` to skip heavy tests for docs-only changes
  - Three-job CI structure (changes → test → ci-status) for branch protection

- **API Foundation**
  - FastAPI application factory with lifespan context manager for database lifecycle
  - Externalized configuration using pydantic-settings with environment variable support
  - Health endpoints: `/health/live` (liveness) and `/health/ready` (readiness with dependency checks)
  - Middleware stack with correlation ID (`X-Correlation-ID` header) and Prometheus metrics

- **Library API**
  - `GET /api/v1/videos` - List videos with pagination (offset/limit)
  - `GET /api/v1/videos/{video_id}` - Get video details by ID
  - `GET /api/v1/videos/search` - Full-text search with FTS5 integration
  - `POST /api/v1/videos/scan` - Directory scanning with FFprobe metadata extraction
  - `DELETE /api/v1/videos/{video_id}` - Delete video with optional file removal (`delete_file` flag)

- **Clip Model**
  - `Project` model for organizing clips with output settings (resolution, fps)
  - `Clip` model with in/out points delegating validation to Rust core
  - `AsyncProjectRepository` and `AsyncClipRepository` with SQLite and in-memory implementations
  - `GET/POST /api/v1/projects` - List and create projects
  - `GET/PUT/DELETE /api/v1/projects/{project_id}` - Project CRUD operations
  - `GET/POST /api/v1/projects/{project_id}/clips` - List and create clips
  - `GET/PUT/DELETE /api/v1/clips/{clip_id}` - Clip CRUD operations

### Changed

- Repository pattern now supports both sync (CLI) and async (API) access
- CI workflow now conditionally runs tests based on changed paths
- pytest-asyncio configured with `asyncio_mode = "auto"` for cleaner async tests

### Fixed

- CI migration reversibility now verified automatically on every push

## [v002] - 2026-01-27

Database & FFmpeg Integration with Python Bindings Completion. Addresses roadmap M1.4-1.5.

### Added

- **Python Bindings Completion**
  - `Clip` and `ClipValidationError` types exposed to Python with full property access
  - `find_gaps`, `merge_ranges`, and `total_coverage` functions for TimeRange operations
  - Automatic stub generation verification script (`scripts/verify_stubs.py`)
  - CI drift detection for stub files

- **Database Foundation**
  - SQLite schema with 14-column `videos` table for video metadata storage
  - FTS5 full-text search with automatic index synchronization via triggers
  - `VideoRepository` protocol with SQLite and InMemory implementations
  - Alembic migration support with rollback capability
  - Audit logging for tracking all data modifications (`audit_log` table)

- **FFmpeg Integration**
  - FFprobe wrapper for extracting structured video metadata (`VideoMetadata` dataclass)
  - `FFmpegExecutor` protocol with Real, Recording, and Fake implementations
  - Integration layer bridging Rust `FFmpegCommand` to Python executor
  - Recording/replay pattern for deterministic subprocess testing
  - `ObservableFFmpegExecutor` wrapper with structured logging (structlog)
  - Prometheus metrics for FFmpeg command execution (duration, success/failure counts)

- **Process Documentation**
  - PyO3 bindings section in AGENTS.md with incremental binding rule
  - Stub regeneration workflow documentation
  - Naming convention guidance (`py_` prefix with `#[pyo3(name)]` attribute)

### Changed

- API naming cleanup: removed `py_` prefixes from 16 Python-visible method names
- Updated 37 test assertions for new API naming
- Renamed Rust `ValidationError` to `ClipValidationError` in Python for clarity

### Fixed

- Stub drift between generated and manual stubs now caught by CI verification

## [v001] - 2026-01-26

Foundation version establishing hybrid Python/Rust architecture with timeline math and FFmpeg command building.

### Added

- **Project Foundation**
  - Python project structure with uv, ruff, mypy, and pytest
  - Rust workspace with PyO3 bindings (abi3-py310)
  - GitHub Actions CI pipeline (Ubuntu, Windows, macOS × Python 3.10, 3.11, 3.12)
  - Type stubs for IDE support and mypy integration

- **Timeline Math (Rust)**
  - `FrameRate` type with rational numerator/denominator representation
  - `Position` type for frame-accurate timeline positions
  - `Duration` type for frame-accurate time spans
  - `Clip` type with validation (start, end, media_start, media_duration)
  - `ValidationError` with field, message, actual, and expected values
  - `TimeRange` with half-open interval semantics
  - Range operations: overlap, intersection, union, subtraction, contains
  - List operations: find_gaps, merge_ranges (O(n log n))
  - Property-based tests for invariants (proptest)

- **FFmpeg Command Builder (Rust)**
  - `FFmpegCommand` fluent builder with input/output management
  - Position-sensitive option handling (seek, codecs, filters)
  - `Filter`, `FilterChain`, and `FilterGraph` types
  - Common filter constructors: scale, pad, fps, setpts, concat, atrim
  - Input sanitization: text escaping, path validation, bounds checking
  - Codec and preset whitelist validation
  - Complete PyO3 bindings with method chaining support

- **Python API**
  - `stoat_ferret_core` module with all Rust types exposed
  - ImportError fallback for development without Rust builds
  - Full type stubs in `stubs/stoat_ferret_core/`

### Changed

- N/A (initial release)

### Fixed

- N/A (initial release)

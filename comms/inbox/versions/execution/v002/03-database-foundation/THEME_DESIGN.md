# Theme 03: database-foundation

## Overview
Establish SQLite database layer with repository pattern for video metadata storage.

## Context
Roadmap M1.4 specifies:
- SQLite with schema for videos, metadata, thumbnails
- Repository pattern with injectable storage interfaces
- In-memory implementation for testing
- Migration support with rollback
- Audit logging

## Architecture Decisions

### AD-001: Synchronous SQLite
Use synchronous sqlite3 for v002.
- No async API layer yet (FastAPI is v003)
- Simpler implementation and testing
- Migrate to aiosqlite in v003 if needed

### AD-002: Single Repository Interface
Start with single VideoRepository interface.
- Handles videos with embedded metadata and thumbnail paths
- Split into separate repositories later if needed

### AD-003: Schema Design
Videos table with:
- Core: id, path, filename
- Video: duration_frames, frame_rate_num/den, width, height, codec
- Audio: audio_codec (nullable)
- Meta: file_size, created_at, updated_at
- FTS5 virtual table for search

### AD-004: Alembic for Migrations
Use Alembic for schema migrations.
- Industry standard
- Supports upgrade and downgrade
- Works with sync sqlite3

## Dependencies
None from this version

## New Dependencies
- alembic>=1.13

## Evidence
- Repository pattern scope: `comms/outbox/exploration/design-research-gaps/design-clarifications.md`

## Success Criteria
- Videos table with FTS5 search
- VideoRepository protocol with SQLite and InMemory implementations
- Contract tests verifying implementations match
- Alembic migrations working
- Audit log captures mutations
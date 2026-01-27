# SQLite Schema

## Goal
Create SQLite database schema for video metadata with FTS5 full-text search.

## Requirements

### FR-001: Videos Table
Create videos table with columns:
- id: TEXT PRIMARY KEY (UUID)
- path: TEXT NOT NULL UNIQUE (full file path)
- filename: TEXT NOT NULL (basename for display)
- duration_frames: INTEGER NOT NULL
- frame_rate_numerator: INTEGER NOT NULL
- frame_rate_denominator: INTEGER NOT NULL
- width: INTEGER NOT NULL
- height: INTEGER NOT NULL
- video_codec: TEXT NOT NULL
- audio_codec: TEXT (nullable)
- file_size: INTEGER NOT NULL
- thumbnail_path: TEXT (nullable)
- created_at: TEXT NOT NULL (ISO8601)
- updated_at: TEXT NOT NULL (ISO8601)

### FR-002: FTS5 Virtual Table
Create FTS5 virtual table for full-text search:
- videos_fts(filename, path)
- Triggers to keep in sync with videos table

### FR-003: Schema Module
Create src/stoat_ferret/db/schema.py with:
- SQL statements for table creation
- create_tables(connection) function
- Table name constants

### FR-004: Index
Add index on path for fast lookups.

## Acceptance Criteria
- [ ] Videos table created with all columns
- [ ] FTS5 table created with sync triggers
- [ ] create_tables() works on fresh database
- [ ] Path index exists
# Requirements: clip-effect-model

## Goal

Extend the clip data model with effects storage across Python schema, DB repository, and Alembic migration.

## Background

Backlog Item: BL-043 (partial — model layer)

No API endpoint exists to apply effects to clips, and the clip model currently has no field for storing applied effects. This feature handles the multi-layer schema change required to support effect storage. The clip model must be extended across Python Pydantic schemas, the DB repository, and the Python dataclass. The Rust Clip type remains unchanged — Python owns effect storage, Rust owns filter generation (LRN-011).

## Functional Requirements

**FR-001: Pydantic schema extension**
- Add typed `effects` list to `ClipResponse` schema
- AC: ClipResponse serializes and deserializes effects list correctly

**FR-002: Python dataclass extension**
- Add `effects` field to `Clip` dataclass (`src/stoat_ferret/db/models.py`)
- JSON string stored in DB, parsed via helper method
- AC: Clip dataclass accepts effects data and provides access to parsed effects

**FR-003: DB schema extension**
- Add `effects_json TEXT` column to clips table via Alembic migration
- Follows existing audit log `changes_json TEXT` pattern
- AC: Alembic migration runs successfully; column exists in clips table

**FR-004: SQLite repository update**
- Update `_row_to_clip()` in `AsyncSQLiteClipRepository` to handle effects_json column
- AC: Clips stored and retrieved with effects data intact via SQLite repository

**FR-005: In-memory repository update**
- Update `AsyncInMemoryClipRepository` to handle effects field
- AC: In-memory repository stores and retrieves effects identically to SQLite repository

**FR-006: Effect configuration format**
- Effect configuration format aligned with registry schema from effect-discovery feature
- AC: Effect configurations stored on clips can be validated against registry schemas

## Non-Functional Requirements

**NFR-001: Backward compatibility**
- Existing clips without effects return empty effects list (not null or error)
- AC: Clips created before migration have `effects: []` in responses

**NFR-002: Test coverage**
- Python coverage maintained above 80% threshold
- AC: Schema, repository, and migration have comprehensive tests

## Out of Scope

- Effect ordering or priority within the effects list
- Effect conflict detection (e.g., two text overlays at same position)
- Rust Clip type changes (Python owns effect storage per LRN-011)

## Test Requirements

- **Unit tests:** Pydantic model extension (serialization/deserialization), DB repository (effect storage and retrieval)
- **Contract tests:** Schema round-trip (Python → DB → Python effect configuration survives)
- **Parity tests:** If InMemory clip repository updated, run parity tests against SQLite implementation (LRN-007)

Reference: `See comms/outbox/versions/design/v006/004-research/ for supporting evidence`
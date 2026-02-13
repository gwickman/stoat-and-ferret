# Implementation Plan: clip-effect-model

## Overview

Extend the clip data model to support an effects list by adding an `effects_json TEXT` column to the clips table via Alembic migration, updating the Python Clip dataclass, Pydantic schemas, and both repository implementations. The Rust Clip type remains unchanged.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `src/stoat_ferret/db/schema.py` | Modify | Add effects_json column to clips table definition |
| `src/stoat_ferret/db/models.py` | Modify | Add effects field to Clip dataclass |
| `src/stoat_ferret/api/schemas/clip.py` | Modify | Add typed effects list to ClipResponse and ClipUpdate |
| `src/stoat_ferret/db/clip_repository.py` | Modify | Update _row_to_clip() and write methods in both SQLite and InMemory implementations |
| `alembic/versions/xxxx_add_effects_to_clips.py` | Create | Alembic migration adding effects_json column |
| `tests/test_clip_model.py` | Modify | Add tests for effects field on Clip dataclass |
| `tests/test_clip_repository_contract.py` | Modify | Add tests for effects storage and retrieval |
| `tests/test_contract/test_repository_parity.py` | Modify | Add parity tests for effects field across repository implementations |

## Implementation Stages

### Stage 1: DB Schema and Migration

1. Update `src/stoat_ferret/db/schema.py`:
   - Add `effects_json TEXT` column to clips table (follows audit log `changes_json TEXT` pattern at lines 68-77)
   - Default value: NULL (empty effects = no column value)
2. Create Alembic migration:
   ```bash
   cd /path/to/project && uv run alembic revision --autogenerate -m "add effects to clips"
   ```
   - Migration adds `effects_json TEXT` column to existing clips table

**Verification:**
```bash
uv run pytest tests/test_db_schema.py -v
```

### Stage 2: Python Dataclass Extension

1. Update `src/stoat_ferret/db/models.py`:
   - Add `effects: str = ""` field to Clip dataclass (JSON string)
   - Add helper method `parsed_effects() -> list[dict]` using `json.loads()`
   - Empty string or NULL treated as empty list

**Verification:**
```bash
uv run pytest tests/test_clip_model.py -v
```

### Stage 3: Pydantic Schema Extension

1. Update `src/stoat_ferret/api/schemas/clip.py`:
   - Add `effects: list[EffectConfig] = []` to `ClipResponse`
   - Create `EffectConfig` model matching the effect registry schema from effect-discovery feature
   - Serialization: JSON list ↔ effects_json TEXT column

**Verification:**
```bash
uv run pytest tests/test_api/test_clips.py -v
```

### Stage 4: Repository Updates

1. Update `AsyncSQLiteClipRepository` in `src/stoat_ferret/db/clip_repository.py`:
   - `_row_to_clip()`: parse effects_json column, default to empty list for NULL
   - Write methods: serialize effects to JSON string for storage
2. Update `AsyncInMemoryClipRepository`:
   - Handle effects field in storage and retrieval (use `copy.deepcopy()` pattern)

**Verification:**
```bash
uv run pytest tests/test_clip_repository_contract.py -v
uv run pytest tests/test_contract/test_repository_parity.py -v
```

## Test Infrastructure Updates

- Update test factories in `tests/factories.py` if clip factory exists, to include effects field
- Parity tests ensure SQLite and InMemory repositories handle effects identically (LRN-007)

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest
```

## Risks

- Multi-layer schema change — mitigated by following established audit log JSON pattern. See `comms/outbox/versions/design/v006/006-critical-thinking/risk-assessment.md`.
- Backward compatibility with existing clips — mitigated by NULL default and empty-list fallback.

## Commit Message

```
feat: extend clip data model with effects storage

Add effects_json TEXT column to clips table via Alembic migration,
effects field to Clip dataclass, typed effects list to ClipResponse
schema, and updated repository implementations. Covers BL-043 (partial).
```
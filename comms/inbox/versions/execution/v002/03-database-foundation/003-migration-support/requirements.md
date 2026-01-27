# Migration Support

## Goal
Configure Alembic for database migrations with rollback capability.

## Requirements

### FR-001: Alembic Configuration
- Initialize alembic in project
- Configure alembic.ini for SQLite
- Set up versions directory

### FR-002: Initial Migration
- Create migration for v001 schema (videos table, FTS5)
- Migration should be idempotent-safe

### FR-003: Upgrade/Downgrade
- alembic upgrade head works
- alembic downgrade -1 works
- Full rollback to empty database works

### FR-004: Add Dependency
- Add alembic to pyproject.toml dependencies

## Acceptance Criteria
- [ ] `alembic upgrade head` creates all tables
- [ ] `alembic downgrade -1` removes tables
- [ ] `alembic current` shows migration status
- [ ] Migration files in alembic/versions/
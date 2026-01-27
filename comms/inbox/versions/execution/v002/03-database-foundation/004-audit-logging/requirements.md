# Audit Logging

## Goal
Track all data modifications with audit log entries.

## Requirements

### FR-001: Audit Log Table
Create audit_log table:
- id: TEXT PRIMARY KEY
- timestamp: TEXT NOT NULL (ISO8601)
- operation: TEXT NOT NULL (INSERT, UPDATE, DELETE)
- entity_type: TEXT NOT NULL (video)
- entity_id: TEXT NOT NULL
- changes_json: TEXT (JSON of changed fields)
- context: TEXT (optional context like user/request ID)

### FR-002: AuditLogger Class
Create class with:
- log_change(operation, entity_type, entity_id, changes, context)
- get_history(entity_id, limit) -> list[AuditEntry]

### FR-003: Repository Integration
Modify SQLiteVideoRepository to log changes:
- add() logs INSERT
- update() logs UPDATE with changed fields
- delete() logs DELETE

### FR-004: Migration
Add audit_log table to Alembic migrations.

## Acceptance Criteria
- [ ] Audit log table exists
- [ ] All repository mutations create audit entries
- [ ] Can retrieve audit history for an entity
- [ ] Changes captured as JSON diff
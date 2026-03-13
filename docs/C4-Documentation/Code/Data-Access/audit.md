# Audit

**Source:** `src/stoat_ferret/db/audit.py`
**Component:** Data Access

## Purpose

Provides audit logging functionality for tracking and recording all data modifications to the database. Implements change tracking for INSERT, UPDATE, and DELETE operations with optional context information. Maintains an immutable audit trail for compliance and debugging purposes.

## Public Interface

### Classes

- `AuditLogger`
  - Logger for recording audit trail of data changes
  - Provides methods to log data modifications and retrieve audit history
  - `__init__(conn: sqlite3.Connection) -> None`
    - Initialize the audit logger with a database connection
    - Parameters: `conn` — SQLite database connection

  - `log_change(operation: str, entity_type: str, entity_id: str, changes: dict[str, object] | None = None, context: str | None = None) -> AuditEntry`
    - Log a data modification to the audit log
    - Parameters:
      - `operation: str` — Type of operation: "INSERT", "UPDATE", or "DELETE"
      - `entity_type: str` — Type of entity being modified (e.g., "video", "project", "clip")
      - `entity_id: str` — ID of the entity being modified
      - `changes: dict[str, object] | None` — Dictionary of field changes for UPDATE operations (optional)
        - Format: `{"field_name": {"old": old_value, "new": new_value}}`
      - `context: str | None` — Optional context information (e.g., user ID, request ID, API endpoint)
    - Returns: AuditEntry instance with generated ID and current timestamp
    - Side effects: Inserts record into audit_log table and commits transaction

  - `get_history(entity_id: str, limit: int = 100) -> list[AuditEntry]`
    - Retrieve audit history for an entity
    - Parameters:
      - `entity_id: str` — ID of the entity to get history for
      - `limit: int` — Maximum number of entries to return (default 100)
    - Returns: List of AuditEntry objects ordered by timestamp DESC (most recent first)
    - Query: Uses index on (entity_id, timestamp) for efficient retrieval

  - `_row_to_entry(row: tuple[object, ...]) -> AuditEntry`
    - Convert a database row tuple to an AuditEntry object
    - Private helper method for deserialization

## Dependencies

- **stoat_ferret.db.models**: AuditEntry dataclass
- **json**: For serializing/deserializing changes dict
- **sqlite3**: For SQLite database connection
- **datetime**: For timestamp handling (timezone.utc)

## Key Implementation Details

### Audit Entry Structure

Each audit log entry captures:
- **id**: UUID string (unique identifier)
- **timestamp**: ISO format datetime (UTC)
- **operation**: "INSERT", "UPDATE", or "DELETE"
- **entity_type**: Type of entity changed (e.g., "video", "project", "clip")
- **entity_id**: The specific entity's ID
- **changes_json**: JSON string of field changes (INSERT/DELETE = null, UPDATE = changes dict)
- **context**: Optional contextual info (user_id, request_id, endpoint, etc.)

### Change Tracking

- **INSERT operations**: changes_json is NULL (no "before" state exists)
- **UPDATE operations**: changes_json contains field-level diffs:
  ```json
  {
    "field_name": {"old": old_value, "new": new_value},
    "another_field": {"old": null, "new": 42}
  }
  ```
- **DELETE operations**: changes_json is NULL (entity is gone)

### Database Design

- **audit_log table** created via schema.py
- Composite index on (entity_id, timestamp) for efficient history queries
- All timestamps stored in ISO format for consistency
- JSON string storage for flexible field change tracking

### Timestamp Handling

- Uses `datetime.now(timezone.utc)` for consistent UTC timestamps
- Stored as ISO format strings (e.g., "2025-03-13T10:30:45.123456+00:00")
- Deserialized back to datetime objects via datetime.fromisoformat()

### Transaction Commitment

- Each log_change() call immediately commits the transaction
- Ensures audit records are persisted immediately
- No batching or delayed commits (always-on audit trail)

### Integration Pattern

- AuditLogger is optional parameter to repository constructors
- When provided, repositories call log_change() for all mutations
- Repositories compute field-level diffs (see repository.py for example)
- AuditLogger itself only handles serialization/deserialization

### Query Limitations

- get_history() queries only by entity_id
- To query by operation type, entity_type, or date range, use direct SQL queries
- Composite index supports the default access pattern efficiently

## Relationships

- **Used by:**
  - repository.SQLiteVideoRepository (optional audit logging)
  - async_repository.AsyncSQLiteVideoRepository (optional audit logging)
  - Service layer (to retrieve audit history for reporting)
  - Compliance and audit workflows

- **Uses:**
  - models.AuditEntry — the audit log entry dataclass
  - schema (indirectly) — depends on audit_log table definition
  - json — for serialization/deserialization of changes dict

- **Schema Integration:**
  - Tracks changes to any entity type (video, project, clip, track, version)
  - Can be extended to track additional entity types by passing them as entity_type parameter

# Implementation Plan: Audit Logging

## Step 1: Create AuditEntry Model
In `src/stoat_ferret/db/models.py`:

```python
@dataclass
class AuditEntry:
    id: str
    timestamp: datetime
    operation: str  # INSERT, UPDATE, DELETE
    entity_type: str
    entity_id: str
    changes_json: Optional[str] = None
    context: Optional[str] = None
```

## Step 2: Create AuditLogger
In `src/stoat_ferret/db/audit.py`:

```python
import json
from datetime import datetime
import uuid
import sqlite3
from .models import AuditEntry

class AuditLogger:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
    
    def log_change(
        self,
        operation: str,
        entity_type: str,
        entity_id: str,
        changes: dict | None = None,
        context: str | None = None,
    ) -> AuditEntry:
        entry = AuditEntry(
            id=str(uuid.uuid4()),
            timestamp=datetime.utcnow(),
            operation=operation,
            entity_type=entity_type,
            entity_id=entity_id,
            changes_json=json.dumps(changes) if changes else None,
            context=context,
        )
        self._conn.execute("""
            INSERT INTO audit_log (id, timestamp, operation, entity_type, entity_id, changes_json, context)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (entry.id, entry.timestamp.isoformat(), entry.operation, 
              entry.entity_type, entry.entity_id, entry.changes_json, entry.context))
        self._conn.commit()
        return entry
    
    def get_history(self, entity_id: str, limit: int = 100) -> list[AuditEntry]:
        cursor = self._conn.execute("""
            SELECT * FROM audit_log WHERE entity_id = ? ORDER BY timestamp DESC LIMIT ?
        """, (entity_id, limit))
        return [self._row_to_entry(row) for row in cursor.fetchall()]
    
    def _row_to_entry(self, row) -> AuditEntry:
        return AuditEntry(
            id=row[0],
            timestamp=datetime.fromisoformat(row[1]),
            operation=row[2],
            entity_type=row[3],
            entity_id=row[4],
            changes_json=row[5],
            context=row[6],
        )
```

## Step 3: Add Schema
Add to schema.py:
```python
AUDIT_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    timestamp TEXT NOT NULL,
    operation TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    changes_json TEXT,
    context TEXT
);
"""

AUDIT_LOG_INDEX = """
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_id, timestamp);
"""
```

Update create_tables() to include audit_log.

## Step 4: Integrate with Repository
Modify SQLiteVideoRepository:

```python
class SQLiteVideoRepository:
    def __init__(self, conn: sqlite3.Connection, audit_logger: AuditLogger | None = None):
        self._conn = conn
        self._conn.row_factory = sqlite3.Row
        self._audit = audit_logger
    
    def add(self, video: Video) -> Video:
        # ... insert logic ...
        self._conn.commit()
        if self._audit:
            self._audit.log_change("INSERT", "video", video.id)
        return video
    
    def update(self, video: Video) -> Video:
        old = self.get(video.id)
        # ... update logic ...
        self._conn.commit()
        if self._audit and old:
            changes = self._compute_diff(old, video)
            self._audit.log_change("UPDATE", "video", video.id, changes)
        return video
    
    def delete(self, id: str) -> bool:
        # ... delete logic ...
        if self._audit:
            self._audit.log_change("DELETE", "video", id)
        return True
    
    def _compute_diff(self, old: Video, new: Video) -> dict:
        changes = {}
        for field in ["path", "filename", "duration_frames", ...]:
            old_val = getattr(old, field)
            new_val = getattr(new, field)
            if old_val != new_val:
                changes[field] = {"old": old_val, "new": new_val}
        return changes
```

## Step 5: Add Alembic Migration
Create new migration for audit_log table:
```bash
uv run alembic revision -m "add_audit_log"
```

## Step 6: Add Tests
```python
def test_audit_log_on_add():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    audit = AuditLogger(conn)
    repo = SQLiteVideoRepository(conn, audit_logger=audit)
    
    video = make_test_video()
    repo.add(video)
    
    history = audit.get_history(video.id)
    assert len(history) == 1
    assert history[0].operation == "INSERT"
    assert history[0].entity_type == "video"

def test_audit_log_on_update():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    audit = AuditLogger(conn)
    repo = SQLiteVideoRepository(conn, audit_logger=audit)
    
    video = make_test_video()
    repo.add(video)
    
    video.filename = "updated.mp4"
    repo.update(video)
    
    history = audit.get_history(video.id)
    assert len(history) == 2
    assert history[0].operation == "UPDATE"
    assert "filename" in history[0].changes_json
```

## Verification
- Audit entries created on add/update/delete
- History retrieval works
- Changes JSON captures field diffs
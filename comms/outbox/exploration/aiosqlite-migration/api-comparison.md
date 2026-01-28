# aiosqlite vs sqlite3 API Comparison

## Overview

aiosqlite is designed as a drop-in async replacement for sqlite3. It maintains near-identical API semantics while wrapping all operations in async/await patterns.

## Side-by-Side Comparison

### Connection Creation

| sqlite3 | aiosqlite |
|---------|-----------|
| `conn = sqlite3.connect(":memory:")` | `conn = await aiosqlite.connect(":memory:")` |
| `conn.close()` | `await conn.close()` |
| `with sqlite3.connect(...) as conn:` | `async with aiosqlite.connect(...) as conn:` |

### Row Factory

| sqlite3 | aiosqlite |
|---------|-----------|
| `conn.row_factory = sqlite3.Row` | `conn.row_factory = sqlite3.Row` |

**Compatibility**: Identical. aiosqlite supports the same row_factory pattern, including `sqlite3.Row` for dict-like access.

### Query Execution

| sqlite3 | aiosqlite |
|---------|-----------|
| `cursor = conn.execute(sql, params)` | `cursor = await conn.execute(sql, params)` |
| `conn.executemany(sql, params)` | `await conn.executemany(sql, params)` |
| `conn.commit()` | `await conn.commit()` |
| `conn.rollback()` | `await conn.rollback()` |

### Result Fetching

| sqlite3 | aiosqlite |
|---------|-----------|
| `row = cursor.fetchone()` | `row = await cursor.fetchone()` |
| `rows = cursor.fetchall()` | `rows = await cursor.fetchall()` |
| `rows = cursor.fetchmany(n)` | `rows = await cursor.fetchmany(n)` |
| `for row in cursor:` | `async for row in cursor:` |

### Cursor Properties

| Property | sqlite3 | aiosqlite |
|----------|---------|-----------|
| `cursor.rowcount` | Sync | Sync (no await needed) |
| `cursor.lastrowid` | Sync | Sync (no await needed) |
| `cursor.description` | Sync | Sync (no await needed) |
| `cursor.arraysize` | Sync | Sync (no await needed) |

### Exception Handling

aiosqlite re-exports all sqlite3 exceptions unchanged:

```python
from aiosqlite import (
    IntegrityError,
    ProgrammingError,
    OperationalError,
    DatabaseError,
)
```

**Compatibility**: Identical exception types. Existing `except sqlite3.IntegrityError` can remain unchanged or use the re-exported versions.

### Utility Functions

aiosqlite re-exports sqlite3 utility functions:

| Function | Notes |
|----------|-------|
| `register_adapter()` | Works identically |
| `register_converter()` | Works identically |
| `Row` | Same class from sqlite3 |

## Current Repository Pattern Translation

### Current SQLiteVideoRepository

```python
def get(self, id: str) -> Video | None:
    cursor = self._conn.execute("SELECT * FROM videos WHERE id = ?", (id,))
    row = cursor.fetchone()
    return self._row_to_video(row) if row else None
```

### Async Equivalent

```python
async def get(self, id: str) -> Video | None:
    cursor = await self._conn.execute("SELECT * FROM videos WHERE id = ?", (id,))
    row = await cursor.fetchone()
    return self._row_to_video(row) if row else None
```

**Transformation Rule**: Add `await` before `execute()`, `fetchone()`, `fetchall()`, `commit()`. Everything else remains unchanged.

## Key Differences

### Threading Model

- **sqlite3**: Runs on the calling thread, can block the event loop
- **aiosqlite**: Spawns a dedicated background thread per connection, queues operations via `SimpleQueue`, returns results via `call_soon_threadsafe()`

### Iteration Performance

aiosqlite provides configurable chunk fetching:

```python
# Fetch 100 rows at a time to reduce async overhead
async for row in cursor.execute(..., iter_chunk_size=100):
    process(row)
```

### No Synchronous Fallback

aiosqlite is async-only. There's no way to call methods synchronously within an async function. This is intentional for event loop safety.

## Recommendation for stoat-and-ferret

Given the API compatibility, migration is mechanical:

1. Replace `import sqlite3` with `import aiosqlite`
2. Add `async` to method definitions
3. Add `await` to connection/cursor operations
4. Change `for row in cursor` to `async for row in cursor`
5. Exception handling remains unchanged

The existing `row_factory = sqlite3.Row` pattern works without modification.

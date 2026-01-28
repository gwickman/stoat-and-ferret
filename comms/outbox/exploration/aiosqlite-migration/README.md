# aiosqlite Migration Patterns for v003

## Summary

This exploration evaluated async database patterns for the v003 FastAPI integration. The key finding is that **aiosqlite provides a near-identical API to sqlite3**, making migration straightforward.

## Key Findings

### 1. aiosqlite API Compatibility

**High compatibility**. aiosqlite mirrors sqlite3 closely:

| Feature | Compatibility |
|---------|---------------|
| `row_factory` | Identical - `sqlite3.Row` works unchanged |
| `execute()` | Add `await` prefix |
| `fetchone()`/`fetchall()` | Add `await` prefix |
| `commit()`/`rollback()` | Add `await` prefix |
| Exception types | Re-exported identically |
| Utility functions | Re-exported identically |

**Migration effort**: Mechanical transformation - add `async`/`await` keywords.

See: [api-comparison.md](./api-comparison.md)

### 2. AsyncVideoRepository Protocol

**Feasible with separate protocol**. Recommended approach:

- Create `AsyncVideoRepository` protocol mirroring `VideoRepository`
- Implement `AsyncSQLiteVideoRepository` and `AsyncInMemoryVideoRepository`
- Keep existing sync implementations for CLI/batch operations

The transformation is 1:1 - every sync method becomes an async method with identical semantics.

See: [async-repository-pattern.md](./async-repository-pattern.md)

### 3. Contract Test Strategy

**Same parametrized fixture pattern works**. Use:

- `pytest-asyncio` for async test support
- `@pytest.fixture(params=["sqlite", "memory"])` with `AsyncGenerator`
- Separate test file `test_async_repository_contract.py`
- Share `make_test_video()` helper in `conftest.py`

See: [contract-test-strategy.md](./contract-test-strategy.md)

### 4. Alembic Async Support

**Fully supported** through SQLAlchemy's `run_sync()` bridge:

- Alembic provides async template: `alembic init -t async`
- Connection URL: `sqlite+aiosqlite:///database.db`
- Migrations use `await connection.run_sync(do_run_migrations)`

**v003 recommendation**: Keep existing sync `schema.py` for now, add Alembic when schema versioning is needed.

See: [alembic-compatibility.md](./alembic-compatibility.md)

### 5. FastAPI Connection Management

**Lifespan pattern recommended**:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = await aiosqlite.connect("database.db")
    yield
    await app.state.db.close()
```

For higher traffic, [aiosqlitepool](https://github.com/slaily/aiosqlitepool) provides connection pooling.

## Alternative: encode/databases

Evaluated `encode/databases` as an alternative. It wraps aiosqlite with:

- Multi-database support (PostgreSQL, MySQL, SQLite)
- SQLAlchemy Core query builder integration
- Built-in connection pooling

**Recommendation**: Stick with raw aiosqlite for v003. The abstraction layer adds complexity without immediate benefit for SQLite-only deployment.

## Recommendations for v003 Implementation

### Phase 1: Async Repository Layer

1. Add `aiosqlite` dependency
2. Create `src/stoat_ferret/db/async_repository.py`:
   - `AsyncVideoRepository` protocol
   - `AsyncSQLiteVideoRepository` implementation
   - `AsyncInMemoryVideoRepository` implementation
3. Create `tests/test_async_repository_contract.py`
4. Add `pytest-asyncio` dev dependency

### Phase 2: FastAPI Integration

1. Use lifespan pattern for connection management
2. Create dependency injection for repository
3. Wire async repository to API endpoints

### Phase 3: Schema Management (Future)

1. Add Alembic when schema changes are needed
2. Use async template with `sqlite+aiosqlite://`
3. Create baseline migration from current schema

## Dependencies to Add

```toml
[project.dependencies]
aiosqlite = ">=0.19"

[project.optional-dependencies]
dev = [
    "pytest-asyncio>=0.23",
]
```

## Files in This Exploration

| File | Purpose |
|------|---------|
| [README.md](./README.md) | This summary |
| [api-comparison.md](./api-comparison.md) | sqlite3 vs aiosqlite API comparison |
| [async-repository-pattern.md](./async-repository-pattern.md) | Concrete implementation examples |
| [contract-test-strategy.md](./contract-test-strategy.md) | Testing approach for async repos |
| [alembic-compatibility.md](./alembic-compatibility.md) | Alembic + async configuration |

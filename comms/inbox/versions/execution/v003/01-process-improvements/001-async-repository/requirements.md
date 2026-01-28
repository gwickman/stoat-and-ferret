# Async Repository (BL-013)

## Goal
Implement async video repository for FastAPI integration using aiosqlite.

## Requirements

### FR-001: AsyncVideoRepository Protocol
Define protocol in `src/stoat_ferret/db/async_repository.py`:
```python
class AsyncVideoRepository(Protocol):
    async def add(self, video: Video) -> Video: ...
    async def get(self, id: str) -> Video | None: ...
    async def get_by_path(self, path: str) -> Video | None: ...
    async def list_videos(self, limit: int = 100, offset: int = 0) -> list[Video]: ...
    async def search(self, query: str, limit: int = 100) -> list[Video]: ...
    async def update(self, video: Video) -> Video: ...
    async def delete(self, id: str) -> bool: ...
```

### FR-002: AsyncSQLiteVideoRepository
Implement using aiosqlite:
- Same SQL queries as SQLiteVideoRepository
- Use `await conn.execute()`, `await cursor.fetchone()`, etc.
- Support row_factory for Video mapping

### FR-003: AsyncInMemoryVideoRepository
Implement for testing:
- Same logic as InMemoryVideoRepository
- Async methods (can use sync internals)

### FR-004: Contract Tests
Create `tests/test_async_repository_contract.py`:
- Parametrized fixture for both implementations
- Same test cases as sync contract tests
- Use pytest-asyncio

### FR-005: Dependencies
Add to pyproject.toml:
- `aiosqlite>=0.19` (runtime)
- `pytest-asyncio>=0.23` (dev)
- `httpx>=0.26` (dev - for TestClient)

### FR-006: pytest Configuration
Update pyproject.toml:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
markers = [
    "api: API endpoint tests",
    "contract: Contract tests for protocol compliance",
]
```

## Acceptance Criteria
- [ ] AsyncVideoRepository protocol defined
- [ ] AsyncSQLiteVideoRepository implementation complete
- [ ] AsyncInMemoryVideoRepository implementation complete
- [ ] Contract tests pass for both implementations
- [ ] Sync repository unchanged (still works)
- [ ] pytest markers configured
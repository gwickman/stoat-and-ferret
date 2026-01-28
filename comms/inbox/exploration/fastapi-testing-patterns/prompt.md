## Exploration: FastAPI Testing Patterns

### Context
stoat-and-ferret v003 will introduce FastAPI endpoints. We need to establish testing patterns that integrate with our existing pytest infrastructure. Current test fixtures are in `tests/conftest.py`.

### Questions to Answer

1. **TestClient patterns**: How does FastAPI's TestClient work? Sync vs async variants? How does it integrate with pytest-asyncio?

2. **Dependency override patterns**: How do we inject test doubles (InMemoryVideoRepository, FakeFFmpegExecutor) into FastAPI endpoints during tests?

3. **Fixture requirements**: What new fixtures do we need in conftest.py for API testing? How do they interact with existing session-scoped fixtures like `sample_video_path`?

4. **Async test configuration**: What pytest-asyncio configuration is needed? pytest.ini settings? async fixture patterns?

5. **Integration with existing tests**: How do we structure API tests alongside existing unit tests? Separate files? Markers?

### Research Sources
- DeepWiki: fastapi/fastapi (testing section)
- DeepWiki: encode/starlette (TestClient origin)
- Existing code: tests/conftest.py

### Output Requirements

Write findings to: `comms/outbox/exploration/fastapi-testing-patterns/`

Required files:
- `README.md` - Summary with recommended testing architecture
- `testclient-usage.md` - TestClient patterns with examples
- `dependency-injection.md` - Override patterns for test doubles
- `conftest-additions.md` - Concrete fixture code to add
- `pytest-config.md` - Required pytest.ini / pyproject.toml changes

### Commit Instructions
Commit all files with message: "docs(exploration): FastAPI testing patterns for v003"
# Pytest Configuration for FastAPI Testing

## Overview

This document outlines the required pytest and pyproject.toml configuration changes for FastAPI testing in stoat-and-ferret v003.

## Dependencies to Add

Add these to `pyproject.toml` dependencies or dev dependencies:

```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "fastapi>=0.109",      # FastAPI framework
]

[dependency-groups]
dev = [
    # ... existing dev dependencies ...
    "httpx>=0.27",         # Required for TestClient
    "anyio>=4.0",          # For async test support (includes pytest plugin)
]
```

**Note:** `httpx` is required for FastAPI's `TestClient`. The `anyio` package provides the `pytest.mark.anyio` marker for async tests.

## pyproject.toml Changes

### Current Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
]
```

### Updated Configuration

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "--cov=src --cov-report=term-missing"
markers = [
    "slow: marks tests as slow (deselect with '-m \"not slow\"')",
    "api: marks tests as API/integration tests (deselect with '-m \"not api\"')",
]
# asyncio_mode is not needed if using @pytest.mark.anyio
```

## Async Testing Configuration

### Option 1: AnyIO (Recommended)

AnyIO is recommended by FastAPI docs and provides the `@pytest.mark.anyio` marker:

```toml
[dependency-groups]
dev = [
    "anyio[trio]>=4.0",  # Includes pytest plugin
]
```

Usage in tests:
```python
import pytest

@pytest.mark.anyio
async def test_async_operation():
    ...
```

### Option 2: pytest-asyncio (Alternative)

If you prefer pytest-asyncio:

```toml
[dependency-groups]
dev = [
    "pytest-asyncio>=0.23",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"  # or "strict"
```

Usage in tests:
```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    ...
```

**Recommendation:** Use AnyIO (Option 1) as it's the approach documented in FastAPI's official async testing guide.

## Running Tests

### Run All Tests

```bash
uv run pytest
```

### Run Only API Tests

```bash
uv run pytest -m api
```

### Run Everything Except API Tests

```bash
uv run pytest -m "not api"
```

### Run Everything Except Slow Tests

```bash
uv run pytest -m "not slow"
```

### Combine Markers

```bash
uv run pytest -m "api and not slow"
```

## Coverage Configuration

The current coverage configuration in `pyproject.toml` should work without changes:

```toml
[tool.coverage.run]
source = ["src"]
branch = true

[tool.coverage.report]
fail_under = 80
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
]
```

API tests will be included in coverage reporting automatically since they exercise code in `src/`.

## Type Checking Configuration

No changes needed for mypy. The existing configuration already supports the `tests/` directory:

```toml
[tool.mypy]
strict = true
disallow_untyped_defs = true
python_version = "3.10"
mypy_path = ["src", "stubs"]
packages = ["stoat_ferret"]
```

If you want mypy to check test files:

```toml
[tool.mypy]
# ... existing config ...
packages = ["stoat_ferret", "tests"]  # Add tests
```

## Complete pyproject.toml Diff

Here's the complete diff of changes needed:

```diff
 [project]
 dependencies = [
     "alembic>=1.13",
     "structlog>=24.0",
     "prometheus-client>=0.20",
+    "fastapi>=0.109",
 ]

 [dependency-groups]
 dev = [
     "pytest>=8.0",
     "pytest-cov>=4.0",
     "ruff>=0.4",
     "mypy>=1.10",
     "maturin>=1.0",
+    "httpx>=0.27",
+    "anyio[trio]>=4.0",
 ]

 [tool.pytest.ini_options]
 testpaths = ["tests"]
 addopts = "--cov=src --cov-report=term-missing"
 markers = [
     "slow: marks tests as slow (deselect with '-m \"not slow\"')",
+    "api: marks tests as API/integration tests (deselect with '-m \"not api\"')",
 ]
```

## Test Directory Structure

After configuration, create the API test directory:

```bash
mkdir -p tests/test_api
touch tests/test_api/__init__.py
touch tests/test_api/conftest.py
```

## Verification Commands

After making changes, verify the setup:

```bash
# Install new dependencies
uv sync

# Verify pytest markers are registered
uv run pytest --markers | grep -E "(api|slow)"

# Verify TestClient is available
uv run python -c "from fastapi.testclient import TestClient; print('OK')"

# Verify async testing works
uv run python -c "import anyio; print('OK')"

# Run a quick smoke test
uv run pytest tests/test_smoke.py -v
```

## Troubleshooting

### "No module named 'httpx'"

Install httpx:
```bash
uv add httpx --dev
```

### "RuntimeError: Event loop is closed"

This usually means using `TestClient` inside an `async def` test. Use `AsyncClient` instead for async tests, or use regular `def` with `TestClient`.

### "pytest.mark.anyio unknown marker"

Install anyio:
```bash
uv add "anyio[trio]" --dev
```

### Coverage Below Threshold

If adding API tests causes coverage to drop below 80%, you may need to:
1. Add more tests for new API code
2. Temporarily adjust the threshold during development
3. Add `# pragma: no cover` to code that's intentionally untested

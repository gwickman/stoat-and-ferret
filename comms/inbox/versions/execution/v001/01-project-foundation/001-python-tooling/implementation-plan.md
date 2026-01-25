# Implementation Plan: Python Tooling

## Step 1: Create Directory Structure
```bash
mkdir -p src/stoat_ferret
mkdir -p tests
touch src/stoat_ferret/__init__.py
touch src/stoat_ferret/py.typed
touch tests/__init__.py
```

## Step 2: Create pyproject.toml
Create with:
- `[project]` section with name, version, requires-python
- `[build-system]` with maturin backend
- `[dependency-groups]` for dev dependencies
- `[tool.ruff]` configuration
- `[tool.mypy]` configuration
- `[tool.pytest.ini_options]` configuration

## Step 3: Initialize uv
```bash
uv sync
```

## Step 4: Create Initial Test
Create `tests/test_smoke.py` with a passing smoke test to verify pytest works.

## Step 5: Verify Quality Gates
```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ -v
```

## Verification
- All commands exit with code 0
- `.venv/` created with dependencies
- `uv.lock` generated
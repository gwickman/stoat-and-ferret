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
- `[project]` section: name="stoat-ferret", version="0.1.0", requires-python=">=3.10"
- `[build-system]` with maturin backend
- `[dependency-groups]` for dev dependencies (pytest, pytest-cov, ruff, mypy, maturin)
- `[tool.ruff]` configuration (line-length=100, select=["E","F","I","UP","B","SIM"])
- `[tool.mypy]` configuration (strict=true, disallow_untyped_defs=true)
- `[tool.pytest.ini_options]` configuration (testpaths=["tests"], addopts="--cov=src")

## Step 3: Initialize uv
```bash
uv sync
```

## Step 4: Create Initial Test
Create `tests/test_smoke.py`:
```python
def test_smoke():
    """Verify pytest runs."""
    assert True
```

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
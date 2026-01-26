# Handoff: 001-python-tooling

## What Was Done

Python project foundation is now in place with all tooling configured and passing.

## For Next Feature Implementer

### Running Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ -v
```

### Adding New Packages

Use uv to add dependencies:

```bash
uv add <package>           # Runtime dependency
uv add --group dev <pkg>   # Dev dependency
```

### Rust Integration Note

When adding the Rust component (stoat_ferret_core), the build system will need to change from hatchling to maturin. This requires:

1. Creating `rust/stoat_ferret_core/Cargo.toml`
2. Updating `pyproject.toml` build-system to use maturin
3. Uncommenting the `[tool.maturin]` section

### Coverage

Current coverage is at 100% with a threshold of 80%. As the codebase grows, ensure tests maintain this threshold.

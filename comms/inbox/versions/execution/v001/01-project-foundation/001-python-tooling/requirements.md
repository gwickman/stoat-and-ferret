# Python Tooling Setup

## Goal
Initialize Python project with modern tooling: uv for dependency management, ruff for linting/formatting, pytest for testing, mypy for type checking.

## Requirements

### FR-001: Project Structure
- Create `src/stoat_ferret/` package directory
- Create `tests/` directory for pytest
- Create `pyproject.toml` with project metadata

### FR-002: Dependency Management
- Use `uv` as package manager
- Configure `pyproject.toml` with dependencies:
  - pytest, pytest-cov for testing
  - ruff for linting/formatting
  - mypy for type checking
  - maturin for Rust builds

### FR-003: Ruff Configuration
- Enable comprehensive rule sets (E, F, I, UP, B, SIM)
- Configure line length to 100
- Set target Python version to 3.10+

### FR-004: Mypy Configuration
- Strict mode enabled
- Disallow untyped defs
- Configure to check `src/` directory

### FR-005: Pytest Configuration
- Configure test paths
- Set up coverage reporting with 80% threshold
- Add markers for slow tests

## Acceptance Criteria
- [ ] `uv sync` installs all dependencies
- [ ] `uv run ruff check src/ tests/` passes
- [ ] `uv run mypy src/` passes
- [ ] `uv run pytest tests/` runs (even with no tests yet)
- [ ] Project follows src-layout pattern
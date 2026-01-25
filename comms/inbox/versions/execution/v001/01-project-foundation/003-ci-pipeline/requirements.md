# CI Pipeline Setup

## Goal
GitHub Actions workflow for hybrid Python/Rust builds with quality gates on every PR.

## Requirements

### FR-001: Test Workflow
- Run on push to main and all PRs
- Matrix: Ubuntu, Windows, macOS
- Matrix: Python 3.10, 3.11, 3.12

### FR-002: Python Quality Gates
- Run ruff check and format verification
- Run mypy type checking
- Run pytest with coverage

### FR-003: Rust Quality Gates
- Run cargo clippy with warnings as errors
- Run cargo test
- Run cargo fmt check

### FR-004: Build Verification
- Run maturin develop to verify build works
- Import module in Python to verify bindings

### FR-005: Caching
- Cache Rust compilation artifacts
- Cache uv/pip dependencies

## Acceptance Criteria
- [ ] Workflow runs on PR creation
- [ ] All quality gates enforced
- [ ] Build succeeds on all 3 platforms
- [ ] Reasonable CI time (<10 min)
# Implementation Plan: CI Pipeline

## Step 1: Create Workflow Directory
```bash
mkdir -p .github/workflows
```

## Step 2: Create CI Workflow
`.github/workflows/ci.yml`:
```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

env:
  CARGO_TERM_COLOR: always

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      fail-fast: false
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.10", "3.11", "3.12"]
    steps:
      - uses: actions/checkout@v4
      
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      
      - uses: dtolnay/rust-toolchain@stable
        with:
          components: clippy, rustfmt
      
      - uses: Swatinem/rust-cache@v2
        with:
          workspaces: rust/stoat_ferret_core
      
      - name: Install uv
        uses: astral-sh/setup-uv@v4
      
      - name: Install dependencies
        run: uv sync
      
      - name: Rust fmt
        run: cargo fmt --manifest-path rust/stoat_ferret_core/Cargo.toml -- --check
      
      - name: Rust clippy
        run: cargo clippy --manifest-path rust/stoat_ferret_core/Cargo.toml -- -D warnings
      
      - name: Rust tests
        run: cargo test --manifest-path rust/stoat_ferret_core/Cargo.toml
      
      - name: Build Python module
        run: uv run maturin develop
      
      - name: Verify stubs
        run: |
          cd rust/stoat_ferret_core
          cargo run --bin stub_gen
          cd ../..
          diff -q stubs/stoat_ferret_core/__init__.pyi rust/stoat_ferret_core/stoat_ferret_core.pyi || (echo "Stubs out of date! Regenerate with 'cargo run --bin stub_gen'" && exit 1)
      
      - name: Python lint
        run: |
          uv run ruff check src/ tests/
          uv run ruff format --check src/ tests/
      
      - name: Python types
        run: uv run mypy src/
      
      - name: Python tests
        run: uv run pytest tests/ -v --cov=src --cov-fail-under=80
```

## Step 3: Verify Locally
Run all CI steps locally to ensure they pass before push.

## Verification
- Push to branch triggers workflow
- All matrix combinations pass
- Stub verification catches drift
- Caching reduces subsequent run times
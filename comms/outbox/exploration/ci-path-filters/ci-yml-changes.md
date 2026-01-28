# CI Workflow Changes for stoat-and-ferret

## Current State

The existing `.github/workflows/ci.yml` runs a full test matrix (3 OS x 3 Python versions = 9 jobs) on every push and PR, regardless of what files changed.

## Recommended Approach

Use `dorny/paths-filter` to add a "changes" detection job, then conditionally run expensive jobs based on what changed.

## Proposed Workflow Structure

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:

env:
  CARGO_TERM_COLOR: always

jobs:
  # Fast job to detect what changed
  changes:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    outputs:
      code: ${{ steps.filter.outputs.code }}
      rust: ${{ steps.filter.outputs.rust }}
      python: ${{ steps.filter.outputs.python }}
      docs-only: ${{ steps.filter.outputs.docs-only }}
    steps:
      - uses: actions/checkout@v4

      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            code:
              - 'src/**'
              - 'rust/**'
              - 'tests/**'
              - 'stubs/**'
              - 'scripts/**'
              - 'pyproject.toml'
              - 'uv.lock'
              - 'Cargo.toml'
              - 'Cargo.lock'
              - 'rust/stoat_ferret_core/Cargo.toml'
              - '.github/workflows/**'
            rust:
              - 'rust/**'
              - 'Cargo.toml'
              - 'Cargo.lock'
            python:
              - 'src/**'
              - 'tests/**'
              - 'stubs/**'
              - 'pyproject.toml'
              - 'uv.lock'
            docs-only:
              - 'docs/**'
              - '*.md'
              - 'comms/**'

  # Full test matrix - only runs when code changes
  test:
    needs: changes
    if: needs.changes.outputs.code == 'true'
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

      - name: Install FFmpeg
        uses: AnimMouse/setup-ffmpeg@v1

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

      - name: Verify module import
        run: uv run python -c "from stoat_ferret_core import health_check; print(health_check())"

      - name: Verify stubs exist
        run: |
          test -f stubs/stoat_ferret_core/__init__.pyi
          test -f stubs/stoat_ferret_core/_core.pyi
        shell: bash

      - name: Verify stub completeness
        run: uv run python scripts/verify_stubs.py

      - name: Python lint
        run: |
          uv run ruff check src/ tests/
          uv run ruff format --check src/ tests/

      - name: Python types
        run: uv run mypy src/

      - name: Python tests
        run: uv run pytest tests/ -v --cov=src --cov-fail-under=80

  # Status job - always runs to satisfy required checks
  ci-status:
    runs-on: ubuntu-latest
    needs: [changes, test]
    if: always()
    steps:
      - name: Check CI outcome
        run: |
          if [[ "${{ needs.test.result }}" == "failure" ]]; then
            echo "Tests failed"
            exit 1
          fi

          if [[ "${{ needs.changes.outputs.code }}" == "true" ]]; then
            echo "Code changes detected - tests ran and passed"
          else
            echo "No code changes - tests skipped"
          fi
```

## Key Changes from Current Workflow

| Aspect | Current | Proposed |
|--------|---------|----------|
| Jobs | 1 (test) | 3 (changes, test, ci-status) |
| Path detection | None | dorny/paths-filter@v3 |
| Required check | test job | ci-status job |
| Docs-only behavior | Full matrix (9 jobs) | Only changes + ci-status (2 jobs) |

## Implementation Steps

1. **Add the changes job** at the top of the workflow
2. **Add `needs: changes` and `if` condition** to the test job
3. **Add ci-status job** for required check satisfaction
4. **Update branch protection rules** to require `ci-status` instead of individual test jobs

## Branch Protection Configuration

After deploying this workflow, update branch protection:

1. Go to Settings > Branches > main > Edit
2. Under "Require status checks to pass":
   - Remove individual test job checks
   - Add `ci-status` as required

## Incremental Rollout Option

For a safer rollout, start with a simpler approach using workflow-level `paths-ignore`:

```yaml
name: CI

on:
  push:
    branches: [main]
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - 'comms/**'
      - '.gitignore'
      - 'LICENSE'
  pull_request:
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - 'comms/**'
      - '.gitignore'
      - 'LICENSE'
```

**Note:** This simpler approach has the "pending checks" problem for docs-only PRs. Use the full solution with `ci-status` job for production.

## Cost/Benefit Analysis

### Time Saved

For docs-only commits:
- Current: ~9 jobs x ~5 min = ~45 minutes of CI time
- Proposed: ~2 jobs x ~30 sec = ~1 minute of CI time

### Complexity Added

- 1 new action dependency (dorny/paths-filter)
- ~30 lines of additional workflow YAML
- Need to update branch protection rules

### Risk

- Minimal if path patterns are comprehensive (see safety-considerations.md)
- The `ci-status` job ensures required checks are always satisfied

## Testing the Changes

Before merging:

1. Create a test PR with only docs changes
2. Verify the changes job detects it correctly
3. Verify the test job is skipped
4. Verify the ci-status job passes
5. Create a test PR with code changes
6. Verify full test matrix runs

## References

- [dorny/paths-filter@v3](https://github.com/dorny/paths-filter)
- [GitHub Actions: Using conditions to control job execution](https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/using-conditions-to-control-job-execution)

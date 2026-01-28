# Conditional Job Execution Patterns

## The Problem

GitHub's built-in `paths`/`paths-ignore` filters work at the **workflow level**, not the job level. When you want to:

- Run lint on all changes but skip tests for docs-only changes
- Run Python tests for Python changes, Rust tests for Rust changes
- Skip slow integration tests for trivial changes

You need **job-level** conditional execution.

## Solution: dorny/paths-filter Action

The `dorny/paths-filter` action detects changed files and outputs boolean flags for use in job conditions.

### Basic Pattern: Conditional Steps

```yaml
jobs:
  ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: dorny/paths-filter@v3
        id: changes
        with:
          filters: |
            src:
              - 'src/**'
              - 'tests/**'
            rust:
              - 'rust/**'
            docs:
              - 'docs/**'
              - '*.md'

      - name: Run Python tests
        if: steps.changes.outputs.src == 'true'
        run: uv run pytest

      - name: Run Rust tests
        if: steps.changes.outputs.rust == 'true'
        run: cargo test --manifest-path rust/stoat_ferret_core/Cargo.toml
```

### Advanced Pattern: Conditional Jobs

For better parallelization and cleaner workflow structure, use a dedicated "changes" job:

```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    permissions:
      pull-requests: read
    outputs:
      src: ${{ steps.filter.outputs.src }}
      rust: ${{ steps.filter.outputs.rust }}
      docs: ${{ steps.filter.outputs.docs }}
    steps:
      - uses: actions/checkout@v4
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            src:
              - 'src/**'
              - 'tests/**'
              - 'pyproject.toml'
            rust:
              - 'rust/**'
              - 'Cargo.toml'
              - 'Cargo.lock'
            docs:
              - 'docs/**'
              - '*.md'

  python-tests:
    needs: changes
    if: needs.changes.outputs.src == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # ... test steps

  rust-tests:
    needs: changes
    if: needs.changes.outputs.rust == 'true'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      # ... test steps

  docs-only:
    needs: changes
    if: needs.changes.outputs.docs == 'true' && needs.changes.outputs.src != 'true' && needs.changes.outputs.rust != 'true'
    runs-on: ubuntu-latest
    steps:
      - run: echo "Docs-only change, heavy tests skipped"
```

## Handling Skipped Jobs with `needs`

When a job is skipped via `if`, dependent jobs must account for this:

```yaml
jobs:
  build:
    needs: [python-tests, rust-tests]
    if: always() && (needs.python-tests.result == 'success' || needs.python-tests.result == 'skipped') && (needs.rust-tests.result == 'success' || needs.rust-tests.result == 'skipped')
    runs-on: ubuntu-latest
    steps:
      - run: echo "Build step"
```

**Key insight:** Skipped jobs report status as "Success", but you need `always()` to run downstream jobs when all dependencies were skipped.

## Alternative: Commit Message Detection

GitHub Actions natively supports skipping workflows via commit message:

```
git commit -m "docs: update README [skip ci]"
```

Recognized patterns: `[skip ci]`, `[ci skip]`, `[no ci]`, `[skip actions]`, `[actions skip]`

**Limitations:**
- Skips the **entire workflow**, not individual jobs
- Leaves required checks in "Pending" state
- Doesn't work with `pull_request_target` events

### Custom Commit Message Parsing

For more control, parse commit messages in a job:

```yaml
jobs:
  check-skip:
    runs-on: ubuntu-latest
    outputs:
      skip-tests: ${{ steps.check.outputs.skip }}
    steps:
      - id: check
        run: |
          if [[ "${{ github.event.head_commit.message }}" =~ ^docs: ]] || \
             [[ "${{ github.event.head_commit.message }}" =~ ^chore: ]]; then
            echo "skip=true" >> $GITHUB_OUTPUT
          else
            echo "skip=false" >> $GITHUB_OUTPUT
          fi

  tests:
    needs: check-skip
    if: needs.check-skip.outputs.skip-tests != 'true'
    runs-on: ubuntu-latest
    steps:
      # ... test steps
```

## dorny/paths-filter Configuration Options

### Filter Definitions

Inline YAML:
```yaml
filters: |
  backend:
    - 'backend/**'
```

External file:
```yaml
filters: '.github/path-filters.yml'
```

### File Status Filtering

Match only added, modified, or deleted files:

```yaml
filters: |
  added:
    - added: '**'
  modified:
    - modified: 'src/**'
  deleted:
    - deleted: 'deprecated/**'
  changed:
    - added|modified: 'src/**'
```

### List Changed Files

Output matching file paths for use in downstream steps:

```yaml
- uses: dorny/paths-filter@v3
  id: filter
  with:
    list-files: json
    filters: |
      src:
        - 'src/**'

- name: Show changed files
  if: steps.filter.outputs.src == 'true'
  run: echo "${{ steps.filter.outputs.src_files }}"
```

## Event-Specific Behavior

| Event | Change Detection | Notes |
|-------|-----------------|-------|
| `pull_request` | GitHub API | No checkout needed, compares to PR base |
| `push` (default branch) | Git diff | Compares to previous commit |
| `push` (feature branch) | Git diff | Needs explicit `base` parameter |

For feature branches:
```yaml
- uses: dorny/paths-filter@v3
  with:
    base: main  # Compare against main branch
    filters: |
      src:
        - 'src/**'
```

## References

- [dorny/paths-filter](https://github.com/dorny/paths-filter)
- [GitHub Actions: Skipping workflow runs](https://docs.github.com/en/actions/managing-workflow-runs/skipping-workflow-runs)
- [CICube: GitHub Actions If Condition](https://cicube.io/blog/github-actions-if-condition/)

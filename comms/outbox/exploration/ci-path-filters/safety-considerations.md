# Safety Considerations for Path Filtering

## Core Principle

**Never accidentally skip tests on code changes.** Path filtering saves CI time but introduces risk if misconfigured.

## Risk 1: Required Checks Blocked on Skipped Workflows

### The Problem

When a workflow is skipped due to path filtering, its associated checks remain in "Pending" state. If those checks are required for PR merging, the PR is blocked indefinitely.

### Solutions

**Option A: Separate workflows**
- Create a lightweight workflow that always runs for docs-only changes
- This workflow can post a successful status check

**Option B: Conditional job with status reporting**
```yaml
jobs:
  changes:
    runs-on: ubuntu-latest
    outputs:
      code: ${{ steps.filter.outputs.code }}
    steps:
      - uses: dorny/paths-filter@v3
        id: filter
        with:
          filters: |
            code:
              - 'src/**'
              - 'rust/**'
              - 'tests/**'

  test:
    needs: changes
    if: needs.changes.outputs.code == 'true'
    runs-on: ubuntu-latest
    steps:
      # ... actual tests

  # This job always runs and satisfies required checks
  ci-status:
    runs-on: ubuntu-latest
    needs: [changes, test]
    if: always()
    steps:
      - name: Check CI status
        run: |
          if [[ "${{ needs.test.result }}" == "failure" ]]; then
            exit 1
          fi
          echo "CI passed (tests ran: ${{ needs.changes.outputs.code }})"
```

## Risk 2: Missing Path Patterns

### The Problem

Forgetting to include a path that affects code behavior:

- Configuration files (`pyproject.toml`, `Cargo.toml`, `setup.cfg`)
- CI workflow files themselves
- Lock files that change dependency versions
- Type stubs that affect type checking

### Recommended Code Paths for stoat-and-ferret

Always run tests when these change:

```yaml
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
```

### Safe to Skip

These paths don't affect test outcomes:

```yaml
docs-only:
  - 'docs/**'
  - '*.md'
  - 'comms/**'
  - '.gitignore'
  - 'LICENSE'
  - '.editorconfig'
```

## Risk 3: PR vs Push Behavior Differences

### The Problem

Path filters behave differently:

| Event | Comparison |
|-------|------------|
| `pull_request` | Three-dot diff against base branch |
| `push` | Two-dot diff against previous commit |

A push to main after merging may have different detected changes than the PR had.

### Solution

Use consistent filtering for both events:

```yaml
on:
  push:
    branches: [main]
  pull_request:

jobs:
  changes:
    steps:
      - uses: dorny/paths-filter@v3
        with:
          # For push on main, compare to previous commit
          # For PR, compare to base branch (automatic)
          filters: |
            code:
              - 'src/**'
```

## Risk 4: Large Diffs

### The Problem

GitHub's file diff is limited to 300 files. If a commit changes more than 300 files, GitHub cannot determine which files changed, and the workflow runs unconditionally.

### Mitigation

This is actually a **safety feature** - when unsure, GitHub runs the workflow. No action needed, but be aware this can happen during large refactors.

## Risk 5: Workflow File Changes

### The Problem

Changes to `.github/workflows/ci.yml` itself should always trigger CI to validate the workflow works.

### Solution

Always include workflow files in code paths:

```yaml
code:
  - '.github/workflows/**'
  - 'src/**'
  # ... other code paths
```

## Risk 6: Transitive Dependencies

### The Problem

A change to a shared utility might only show changes in that utility's path, but affect tests across the codebase.

### Solution

Include all code paths that could affect behavior, not just "main" code:

```yaml
code:
  - 'src/**'        # All Python source
  - 'rust/**'       # All Rust source
  - 'tests/**'      # Test code changes need to run tests!
  - 'stubs/**'      # Type stubs affect type checking
```

## Best Practices Summary

1. **Default to running tests** - Only skip when you're confident the change is truly isolated
2. **Include config files** - `pyproject.toml`, `Cargo.toml`, lock files
3. **Include workflow files** - Changes to CI should trigger CI
4. **Include test code** - Test changes should run tests
5. **Use a "safety" job** - Always-running job that reports status
6. **Review filter patterns regularly** - As project structure evolves, update filters
7. **Document your filters** - Explain why each pattern is included/excluded

## Testing Your Filters

Before deploying path filters, test them:

```bash
# Simulate what files would match a pattern
git diff --name-only main...HEAD | grep -E '^src/|^rust/'

# Test dorny/paths-filter locally with act
act -P ubuntu-latest=nektos/act-environments-ubuntu:18.04
```

## References

- [GitHub Actions: Skipping workflow runs](https://docs.github.com/en/actions/managing-workflow-runs/skipping-workflow-runs)
- [GitHub Community: Path filtering discussions](https://github.com/orgs/community/discussions/25369)

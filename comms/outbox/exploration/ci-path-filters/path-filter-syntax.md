# GitHub Actions Path Filter Syntax

## Overview

GitHub Actions provides two workflow-level filters for controlling execution based on file changes: `paths` and `paths-ignore`. These work with `push` and `pull_request` events.

## Basic Syntax

### `paths` - Include Filter

Use when you want to run the workflow only when specific files change:

```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'tests/**'
  pull_request:
    paths:
      - 'src/**'
      - 'tests/**'
```

### `paths-ignore` - Exclude Filter

Use when you want to run the workflow for all changes except specific paths:

```yaml
on:
  push:
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - '.gitignore'
  pull_request:
    paths-ignore:
      - 'docs/**'
      - '*.md'
```

## Important Constraint

**You cannot use both `paths` and `paths-ignore` for the same event.** Choose one approach:

- Use `paths` when you have a clear list of paths that should trigger CI
- Use `paths-ignore` when most changes should trigger CI, with specific exclusions

## Glob Pattern Support

Both filters support `*` and `**` wildcards:

| Pattern | Matches |
|---------|---------|
| `*.md` | All markdown files in root |
| `**/*.md` | All markdown files anywhere |
| `src/**` | Everything under src/ |
| `src/*.py` | Python files directly in src/ |
| `src/**/*.py` | Python files anywhere under src/ |

## Negation Patterns with `paths`

You can combine include and exclude patterns using `!`:

```yaml
on:
  push:
    paths:
      - 'src/**'           # Include all src files
      - '!src/**/*.md'     # Except markdown files in src
```

**Order matters:** Negative patterns must come after positive ones to exclude paths. A positive pattern after a negative re-includes that path.

## Combining with Branch Filters

When using both `branches` and `paths`, the workflow runs only when **both** conditions are satisfied:

```yaml
on:
  push:
    branches:
      - main
    paths:
      - 'src/**'
```

This runs only on pushes to main that change files in src/.

## Behavior Differences: Push vs Pull Request

| Aspect | Push | Pull Request |
|--------|------|--------------|
| Diff comparison | Two-dot diff | Three-dot diff |
| Against | Previous commit | Base branch |
| File limit | 300 files max | 300 files max |

If a diff exceeds 300 files, GitHub cannot determine exact changes and the workflow runs.

## Common Patterns for stoat-and-ferret

### Run on Code Changes Only

```yaml
on:
  push:
    paths:
      - 'src/**'
      - 'rust/**'
      - 'tests/**'
      - 'stubs/**'
      - 'pyproject.toml'
      - 'Cargo.toml'
      - 'Cargo.lock'
```

### Skip Documentation Changes

```yaml
on:
  push:
    paths-ignore:
      - 'docs/**'
      - '*.md'
      - 'comms/**'
      - '.gitignore'
      - 'LICENSE'
```

## Limitations

1. **Tag pushes**: Path filters don't apply to tag pushes
2. **Workflow-level only**: These filters apply to the entire workflow, not individual jobs
3. **Pending status**: Skipped workflows leave required checks in "Pending" state, blocking PRs
4. **No runtime access**: You cannot access which paths triggered the workflow in job conditions

For job-level filtering, use the `dorny/paths-filter` action instead.

## References

- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)
- [dorny/paths-filter](https://github.com/dorny/paths-filter)

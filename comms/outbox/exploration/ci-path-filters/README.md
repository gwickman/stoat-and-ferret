# Exploration: GitHub Actions Path Filters

**Context:** BL-017 requires CI optimization to skip heavy test jobs for docs-only commits.

## Summary

GitHub Actions provides two mechanisms for path-based CI optimization:

1. **Workflow-level filters** (`paths`/`paths-ignore`) - Simple but all-or-nothing
2. **Job-level filtering** (`dorny/paths-filter` action) - Flexible, recommended approach

## Recommended Approach

Use `dorny/paths-filter@v3` with a three-job structure:

```
changes → test (conditional) → ci-status (always)
```

This allows:
- Skipping the expensive 9-job test matrix for docs-only changes
- Satisfying required status checks via the `ci-status` job
- Safe fallback to full testing when code paths change

## Key Findings

### 1. Built-in Path Filters

- Work at workflow level only, not job level
- `paths` and `paths-ignore` are mutually exclusive
- Skipped workflows leave required checks in "Pending" state (blocks PRs)
- Support glob patterns (`**/*.md`, `src/**`)

### 2. dorny/paths-filter Action

- Industry standard for job-level path filtering
- Outputs boolean flags for use in `if:` conditions
- Handles push and PR events differently (git diff vs API)
- Supports file status filtering (added/modified/deleted)

### 3. Commit Message Skip

- GitHub natively supports `[skip ci]`, `[ci skip]`, etc.
- Skips entire workflow, not individual jobs
- Not suitable for selective job skipping

### 4. Safety Considerations

- Always include config files (pyproject.toml, Cargo.toml) in "code" paths
- Include workflow files themselves
- Use a "ci-status" job to satisfy required checks
- Test filter patterns before deploying

## Estimated Savings

| Scenario | Current | With Filtering |
|----------|---------|----------------|
| Docs-only commit | 9 jobs, ~45 min | 2 jobs, ~1 min |
| Code commit | 9 jobs, ~45 min | 9 jobs, ~45 min |

## Files in This Exploration

| File | Purpose |
|------|---------|
| `path-filter-syntax.md` | GitHub Actions `paths`/`paths-ignore` reference |
| `conditional-jobs.md` | Patterns for job-level filtering with dorny/paths-filter |
| `safety-considerations.md` | Edge cases, risks, and safeguards |
| `ci-yml-changes.md` | Concrete workflow changes for stoat-and-ferret |

## Implementation Recommendation

1. Start with the full `dorny/paths-filter` solution (not simple `paths-ignore`)
2. Include comprehensive code path patterns
3. Add `ci-status` job to satisfy branch protection
4. Update branch protection to require `ci-status` instead of test jobs
5. Test with docs-only and code-change PRs before merging

## References

- [dorny/paths-filter](https://github.com/dorny/paths-filter)
- [GitHub Actions Workflow Syntax](https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions)
- [GitHub Actions: Skipping workflow runs](https://docs.github.com/en/actions/managing-workflow-runs/skipping-workflow-runs)
- [CICube: GitHub Actions If Condition](https://cicube.io/blog/github-actions-if-condition/)

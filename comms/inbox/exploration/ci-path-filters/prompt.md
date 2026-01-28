## Exploration: GitHub Actions Path Filters

### Context
stoat-and-ferret v003 backlog item BL-017 requires CI optimization to skip heavy steps for docs-only commits. Current CI workflow is in `.github/workflows/ci.yml`.

### Questions to Answer

1. **Path filter syntax**: How do `paths` and `paths-ignore` work in GitHub Actions workflow triggers? Can we filter at job level vs workflow level?

2. **Conditional job execution**: How do we conditionally skip jobs based on changed files? `if` conditions with `github.event.paths`?

3. **dorny/paths-filter action**: Is there a reliable action for detecting changed paths and conditionally running jobs?

4. **Commit message detection**: Can we also skip based on commit message prefixes like `docs:` or `chore:`?

5. **Safe patterns**: What patterns ensure we never accidentally skip tests on code changes? How do we handle PRs vs pushes?

### Research Sources
- GitHub Actions documentation (web search)
- DeepWiki: dorny/paths-filter (if exists)
- Existing code: .github/workflows/ci.yml

### Output Requirements

Write findings to: `comms/outbox/exploration/ci-path-filters/`

Required files:
- `README.md` - Summary with recommended approach
- `path-filter-syntax.md` - GitHub Actions path filter examples
- `conditional-jobs.md` - Patterns for conditional job execution
- `ci-yml-changes.md` - Concrete changes needed for stoat-and-ferret CI
- `safety-considerations.md` - Edge cases and safeguards

### Commit Instructions
Commit all files with message: "docs(exploration): GitHub Actions path filter patterns for BL-017"
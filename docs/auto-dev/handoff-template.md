# Feature Handoff Template

Use this template when a feature produces artifacts that a subsequent sequential feature depends on.
Completing this document is mandatory for sequential feature chains; it enables downstream features
to achieve full AC coverage on first submission without rework.

---

## Handoff: [Feature Name / BL-NNN]

**From:** Feature NNN (executor name)
**To:** Feature NNN+1 (or describe which downstream feature consumes this)
**Date:** YYYY-MM-DD

---

## Files Modified

List every file created or modified, with a one-line description of what changed:

| File | Change |
|------|--------|
| `path/to/file.py` | Added X; removed Y |
| `docs/design/foo.md` | New §3 covering Z |

---

## Framework Conflicts Encountered

Document any conflicts between version requirements and existing framework rules, and how they were resolved:

- **Conflict:** Rule 1b-i prohibits editing FRAMEWORK_CONTEXT.md content sections
  **Resolution:** Version design marked `framework_extension: true`; exception granted in design doc

If none: "No framework conflicts encountered."

---

## Cross-Feature Ordering Constraints

Specify any constraints the downstream feature must respect:

- Startup phase ordering: new service X must initialize after Phase 6 (see AGENTS.md Startup Ordering)
- Migration naming: use `revision_id` = `abc123` as the parent revision for the next migration
- Schema changes: column `foo` added in migration `001_add_foo`; downstream feature must not re-add it

If none: "No cross-feature ordering constraints."

---

## Known Limitations for Dependent Features

List anything the downstream feature should be aware of but that was out of scope for this feature:

- Test coverage for edge case Y was deferred (noted in quality-gaps.md)
- The stub at `docs/design/FRAMEWORK_CONTEXT.md` was not updated; downstream features should read the artifacts-repo copy

If none: "No known limitations."

---

## Completion Criteria

A handoff is considered complete when all of the following are true:

- [ ] All files modified are listed in the Files Modified table
- [ ] Framework conflicts are documented (or explicitly stated as none)
- [ ] Cross-feature ordering constraints are documented (or explicitly stated as none)
- [ ] Known limitations are documented (or explicitly stated as none)
- [ ] This document is committed to main before the downstream feature begins execution

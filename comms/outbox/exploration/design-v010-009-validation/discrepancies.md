# Discrepancies - v010

No blocking discrepancies identified.

## Minor Observations (Non-Blocking)

1. **THEME_INDEX.md formatting**: Missing blank line between Theme 01's feature list and the `### Theme 02:` header. This is a cosmetic issue that does not affect parsing or execution.

2. **VERSION_DESIGN.md and THEME_INDEX.md structural differences**: The persisted inbox versions differ structurally from the Task 007 drafts. This is expected behavior -- the `design_version` tool restructures these into its canonical template format. All substantive content is preserved.

3. **`tests/test_integration/` directory**: Does not yet exist. Feature 003 (`event-loop-responsiveness-test`) will create this directory. The parent `tests/` exists. This is normal for new-file features.

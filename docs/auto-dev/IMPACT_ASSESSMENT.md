# Impact Assessment Checks

Maintenance checks to flag when code changes may break smoke tests or require smoke test updates.

## Smoke Test Coverage Gaps

**Trigger:** New API route definitions added to `src/stoat_ferret/api/routers/` that are not exercised by any smoke test.

**Detection:**

```bash
# List routes defined in routers
grep -rn '@router\.\(get\|post\|put\|patch\|delete\)' src/stoat_ferret/api/routers/

# List routes exercised in smoke tests
grep -rn 'client\.\(get\|post\|put\|patch\|delete\)' tests/smoke/
```

**Action:** Compare output. Any route in routers not covered by a smoke test should be flagged for review. Add smoke test coverage for new endpoints.

## Sample Project Compatibility

**Trigger:** New effect types added to `src/stoat_ferret/effects/` or new Rust filter builders that smoke tests don't exercise.

**Detection:**

```bash
# List effect/filter types in source
grep -rn 'class.*Effect' src/stoat_ferret/effects/
grep -rn 'pub struct.*Filter\|pub struct.*Builder' rust/stoat_ferret_core/src/

# List effects exercised in smoke tests
grep -rn 'effect\|filter\|transition' tests/smoke/
```

**Action:** Compare output. New effect types should have corresponding smoke test coverage to verify they work end-to-end with sample projects.

## Test Video Fixture Assumptions

**Trigger:** Changes to video files in the `videos/` directory or references to `EXPECTED_VIDEOS` in test fixtures.

**Detection:**

```bash
# Check for video file changes
git diff --name-only HEAD~1 | grep -i 'videos/'

# Check for EXPECTED_VIDEOS references
grep -rn 'EXPECTED_VIDEOS\|expected_videos\|video.*fixture' tests/smoke/
```

**Action:** When video files are added, removed, or modified, verify that smoke test fixtures still reference valid files and that expected video counts are correct.

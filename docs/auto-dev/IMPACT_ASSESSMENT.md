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

## Composition Model Changes (Phase 3)

**Trigger:** Changes to Phase 3 composition types (`TrackType`, `LayoutPosition`, `LayoutPreset`, `AudioMixSpec`, `BatchProgress`) or their identifiers in Python or Rust source.

**Detection:**

```bash
# List Phase 3 composition model definitions in Python
grep -rn 'class.*TrackType\|class.*LayoutPosition\|class.*LayoutPreset\|class.*AudioMixSpec\|class.*BatchProgress' src/

# List Phase 3 composition model definitions in Rust
grep -rn 'pub struct TrackType\|pub struct LayoutPosition\|pub struct LayoutPreset\|pub struct AudioMixSpec\|pub struct BatchProgress\|pub enum TrackType\|pub enum LayoutPosition\|pub enum LayoutPreset' rust/stoat_ferret_core/src/

# List Phase 3 identifier usage in API schemas and routers
grep -rn 'track_type\|batch_id' src/stoat_ferret/api/

# List Phase 3 types exercised in smoke tests
grep -rn 'TrackType\|LayoutPosition\|LayoutPreset\|AudioMixSpec\|BatchProgress\|track_type\|batch_id' tests/smoke/
```

**Action:** Compare output. When composition model types or identifiers change, verify that smoke tests and contract tests still exercise the updated interfaces. New composition types should have corresponding test coverage.

## Context

When planning versions that include bug fixes alongside feature work, there's a question of whether to bundle bug fixes into existing themes or create separate themes for them.

## Learning

Isolated bug fixes with a clear root cause should be their own single-feature theme rather than bundled into unrelated themes. This keeps the fix precisely scoped, makes the PR review trivial, and allows the fix to pass through CI independently. The overhead of a separate theme is minimal compared to the clarity gained.

## Evidence

v008 Theme 02 (ci-stability) contained a single feature (001-flaky-e2e-fix) — a one-line change adding an explicit timeout. Despite being minimal, it was correctly isolated as its own theme because: (1) it had nothing to do with Theme 01's startup wiring, (2) it could be reviewed independently, and (3) it had its own acceptance criteria and validation requirements (NFR-001: 10 consecutive CI runs). It passed on first iteration.

## Application

During version planning:
1. Create single-feature themes for bug fixes with clear root causes
2. Don't bundle bug fixes into unrelated themes just to reduce theme count
3. Use the theme name to describe the fix category (e.g., "ci-stability") rather than the specific bug
4. Include post-merge validation criteria for bug fixes (e.g., "X consecutive clean runs")
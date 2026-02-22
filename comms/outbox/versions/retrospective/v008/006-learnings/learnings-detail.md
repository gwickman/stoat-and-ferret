# Learnings Detail - v008 Retrospective

## LRN-040: Idempotent Startup Functions for Lifespan Wiring

**Tags:** pattern, startup, idempotency, fastapi, lifespan
**Source:** v008/01-application-startup-wiring retrospective, v008/01-application-startup-wiring/001-database-startup completion-report, v008/01-application-startup-wiring/002-logging-startup completion-report

### Content

#### Context

When wiring initialization logic into application startup (e.g., FastAPI lifespan), the same startup function may be invoked multiple times — once in production and repeatedly across test fixtures.

#### Learning

All startup/lifespan functions should be idempotent. Use guards appropriate to the operation: `IF NOT EXISTS` for DDL statements, exact-type checks for handler registration, and initialization flags for one-time setup. This prevents accumulating duplicate side effects (duplicate log handlers, redundant schema creation) without requiring callers to track invocation state.

#### Evidence

In v008 Theme 01, both `create_tables_async()` (using `IF NOT EXISTS` DDL) and `configure_logging()` (guarding `root.addHandler()` with an exact-type check for existing `StreamHandler`) were made idempotent. This allowed tests to invoke lifespan functions freely without accumulating duplicate handlers or triggering schema errors.

#### Application

When adding any initialization logic to an application lifespan or startup sequence:
1. Assume the function will be called multiple times
2. Choose an idempotency guard appropriate to the operation type
3. Test explicitly that multiple invocations produce the same result as a single invocation

---

## LRN-041: Static Type Checking Catches Cross-Module Wiring Errors

**Tags:** pattern, mypy, type-checking, wiring, debugging
**Source:** v008/01-application-startup-wiring/003-orphaned-settings completion-report, v008 version retrospective

### Content

#### Context

When wiring settings or configuration values to framework APIs across module boundaries, the correct consumer API is not always obvious. Implementation plans may suggest API calls that seem reasonable but are actually invalid.

#### Learning

Static type checkers (mypy) are especially valuable during wiring work that connects configuration to framework APIs. They catch invalid keyword arguments, wrong parameter types, and missing method signatures before runtime — errors that would otherwise only surface in production or integration tests. This is more valuable than in typical application code because wiring crosses module boundaries where the author may not be intimately familiar with the target API.

#### Evidence

In v008, the implementation plan for feature 003 (orphaned settings) suggested wiring `settings.debug` to both `FastAPI(debug=...)` and `uvicorn.run(debug=...)`. mypy caught that `uvicorn.run()` does not accept a `debug` keyword argument. The correct consumer was `FastAPI(debug=...)` only. Without mypy, this would have been a runtime error in production.

#### Application

When wiring configuration to third-party or framework APIs:
1. Run mypy after each wiring change, not just at the end
2. Treat mypy errors as design feedback — they may indicate the implementation plan has an incorrect assumption about the target API
3. Trust the type checker over documentation or implementation plans when they disagree

---

## LRN-042: Group Features by Modification Point for Theme Cohesion

**Tags:** process, planning, theme-design, cohesion, efficiency
**Source:** v008/01-application-startup-wiring retrospective, v008 version retrospective

### Content

#### Context

When planning version themes, features can be grouped by various criteria: functional area, priority, user story, or modification point (the code paths they change).

#### Learning

Grouping features that modify the same code path into a single theme reduces context-switching, makes code review straightforward, and increases the likelihood of first-iteration success. The shared context compounds across features — knowledge gained in the first feature directly benefits subsequent features in the theme.

#### Evidence

v008 Theme 01 grouped three features (database startup, logging startup, orphaned settings) that all modified `app.py` lifespan. All three passed quality gates on first iteration. The shared modification point meant context from feature 001 (lifespan structure, ordering constraints) was immediately reusable for features 002 and 003.

#### Application

During version planning, when multiple features exist that could be grouped different ways:
1. Identify the primary modification point for each feature (which file/function it changes)
2. Group features sharing a modification point into the same theme
3. Order features within the theme so earlier features establish patterns that later features can follow

---

## LRN-043: Explicit Assertion Timeouts in CI-Bound E2E Tests

**Tags:** testing, e2e, playwright, ci, reliability, failure-mode
**Source:** v008/02-ci-stability/001-flaky-e2e-fix completion-report, v008/02-ci-stability retrospective

### Content

#### Context

Playwright E2E tests use default assertion timeouts (typically 5 seconds) that assume local execution speed. CI environments (GitHub Actions) have variable performance characteristics where API responses plus React re-renders can exceed default timeouts.

#### Learning

Every state-transition assertion in E2E specs (`toBeHidden()`, `toBeVisible()`, `toHaveText()`, etc.) should have an explicit timeout proportional to the expected operation duration. Default timeouts cause intermittent CI failures that are difficult to diagnose and block PR merges unpredictably. Apply explicit timeouts consistently from the start rather than waiting for CI failures to surface them.

#### Evidence

In v008, a flaky `toBeHidden()` assertion in `project-creation.spec.ts` intermittently failed in CI with the default 5-second timeout. Adding `{ timeout: 10_000 }` fixed the flake. The project already had this pattern in other specs (`scan.spec.ts`, `effect-workshop.spec.ts`), validating the approach. The fix was a single line change — the cost of applying it proactively across all E2E specs is minimal.

#### Application

When writing or reviewing E2E tests:
1. Add explicit `{ timeout: 10_000 }` (or appropriate value) to all state-transition assertions
2. Match existing timeout patterns in the codebase for consistency
3. Prefer explicit timeouts over retry loops — they're simpler and more predictable
4. Audit existing E2E specs periodically for assertions using default timeouts

---

## LRN-044: Settings Consumer Traceability as a Completeness Check

**Tags:** pattern, configuration, settings, completeness, maintenance
**Source:** v008/01-application-startup-wiring/003-orphaned-settings completion-report, v008/01-application-startup-wiring retrospective

### Content

#### Context

Configuration settings classes (e.g., Pydantic `Settings`) can accumulate fields that are defined but never consumed by production code. These orphaned settings create confusion about whether they're intentionally unused or were simply forgotten during wiring.

#### Learning

After any settings wiring work, verify that every settings field has at least one production consumer. This "settings traceability" check catches configuration drift where fields exist in the schema but aren't consumed. It can be done manually (grep for field names) or automated as a lint rule that maps each Settings field to its usage sites.

#### Evidence

v008 feature 003 (orphaned settings) found that 2 of 9 `Settings` fields (`debug`, `ws_heartbeat_interval`) were defined but unconsumed by production code. After wiring them, all 9 fields had production consumers. The retrospective recommended automating this as a lint check to prevent future orphaned settings.

#### Application

After adding or modifying settings fields:
1. Verify each field has at least one production code consumer (not just test usage)
2. Consider adding an automated check that maps Settings fields to import sites
3. Treat orphaned settings as low-priority tech debt — they indicate incomplete wiring that may cause operator confusion

---

## LRN-045: Single-Feature Themes for Precisely-Scoped Bug Fixes

**Tags:** process, planning, theme-design, bug-fixes, scoping
**Source:** v008/02-ci-stability retrospective, v008 version retrospective

### Content

#### Context

When planning versions that include bug fixes alongside feature work, there's a question of whether to bundle bug fixes into existing themes or create separate themes for them.

#### Learning

Isolated bug fixes with a clear root cause should be their own single-feature theme rather than bundled into unrelated themes. This keeps the fix precisely scoped, makes the PR review trivial, and allows the fix to pass through CI independently. The overhead of a separate theme is minimal compared to the clarity gained.

#### Evidence

v008 Theme 02 (ci-stability) contained a single feature (001-flaky-e2e-fix) — a one-line change adding an explicit timeout. Despite being minimal, it was correctly isolated as its own theme because: (1) it had nothing to do with Theme 01's startup wiring, (2) it could be reviewed independently, and (3) it had its own acceptance criteria and validation requirements (NFR-001: 10 consecutive CI runs). It passed on first iteration.

#### Application

During version planning:
1. Create single-feature themes for bug fixes with clear root causes
2. Don't bundle bug fixes into unrelated themes just to reduce theme count
3. Use the theme name to describe the fix category (e.g., "ci-stability") rather than the specific bug
4. Include post-merge validation criteria for bug fixes (e.g., "X consecutive clean runs")

---

## LRN-046: Maintenance Versions Succeed with Well-Understood Change Scoping

**Tags:** process, planning, scoping, maintenance, quality
**Source:** v008 version retrospective

### Content

#### Context

Version planning involves choosing between new feature development and maintenance work (wiring, bug fixes, debt resolution). There's a tendency to combine both, but maintenance-focused versions have different success characteristics.

#### Learning

Versions scoped to well-understood, maintenance-focused changes (wiring existing code, fixing diagnosed bugs, resolving known debt) achieve significantly higher first-iteration success rates than feature-development versions. The key factor is that the problem and solution are both well-understood before implementation begins — there's no discovery phase. This validates dedicating entire versions to maintenance when the debt inventory is sufficient.

#### Evidence

v008 achieved 100% first-iteration success (4/4 features, 0 quality gate failures) across two themes. All changes were "wiring existing code rather than building new features" — database schema creation, logging configuration, orphaned settings, and a previously-diagnosed E2E flake. Compare this to feature-development versions where some features require 2-3 iterations.

#### Application

When planning version scope:
1. Don't mix maintenance work into feature-development versions — dedicate versions to maintenance when debt inventory justifies it
2. Maintenance versions benefit from precise problem statements — "wire X to Y" rather than "implement X"
3. Use maintenance versions to resolve P0/P1 blockers before starting the next feature-development cycle
4. Track first-iteration success rates to quantify the scoping benefit

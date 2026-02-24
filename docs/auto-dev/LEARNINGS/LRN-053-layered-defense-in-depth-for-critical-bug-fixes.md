## Context

When fixing a critical bug (P0/P1), a single fix addresses the immediate symptom but leaves the codebase vulnerable to the same class of bug recurring. Bug-fix themes benefit from a structured three-layer approach.

## Learning

Apply a three-layer defense-in-depth pattern for critical bug fixes: (1) fix the immediate bug, (2) add static analysis rules to catch the same class of bug at CI time, (3) add a runtime regression test that detects the failure mode. This ensures the specific bug is fixed, similar bugs are caught before merge, and regressions are detected if the static analysis is insufficient.

## Evidence

v010 Theme 01 (async-pipeline-fix) applied this pattern successfully:
- Feature 001: Fixed the blocking `subprocess.run()` call by converting to `asyncio.create_subprocess_exec()`
- Feature 002: Enabled ruff ASYNC rules (ASYNC221/210/230) to catch blocking calls in async functions at CI time
- Feature 003: Added an integration test verifying event-loop responsiveness during scans

All three features shipped with all acceptance criteria met. The ruff rules would have caught the original bug before it reached production.

## Application

When designing a bug-fix theme for P0/P1 issues:
1. First feature: Fix the specific bug
2. Second feature: Add static analysis or linting rules that catch the same class of bug
3. Third feature: Add a runtime regression test that detects the failure mode under realistic conditions

This pattern is most valuable when the bug class is likely to recur (e.g., blocking calls in async code, security boundary violations, data consistency issues).
# Task 004: Quality Gates

Read AGENTS.md first and follow all instructions there, including the mandatory PR workflow.

## Objective

Run all quality gate checks and verify the codebase passes. Attempt fixes for straightforward failures.

## Context

Post-version retrospective for `${PROJECT}` version `${VERSION}`. Quality gates must pass before closure can proceed.

## Tasks

### 1. Run Quality Gates

Call:
```python
run_quality_gates(project="${PROJECT}")
```

Record the result for each check: pytest, ruff, mypy.

### 2. Evaluate Results

For each check, record:
- Check name
- Pass/fail status
- Return code
- Key output (first 50 lines of failure output if failed)

### 3. Classify and Resolve Failures

If any check fails:

#### 3a. Ruff/Mypy Failures — Classify by Location

- **Errors in `tests/` files** → TEST PROBLEM. Fix directly: run `ruff check --fix`, add missing type annotations, fix formatting.
- **Errors in `src/` files** → CODE PROBLEM. A mypy type error or ruff violation in production code is a real code quality issue, not a "test problem." Document for Task 007 backlog item creation. Do NOT auto-fix production code during retrospective.

#### 3b. Pytest Failures — Classify Each One

For each failing test, read BOTH the test code AND the production code it tests. Also read the version's THEME_INDEX.md and relevant completion reports.

Apply this decision tree:

1. **Does the test assert behavior intentionally changed by a feature in this version?**
   - Check: Does a feature in THEME_INDEX.md explicitly change the behavior the test checks?
   - Check: Does a completion report mention changing this behavior?
   - If YES → **TEST PROBLEM.** The test is outdated — it asserts old behavior.

2. **Does the test reference APIs/parameters/types modified by this version?**
   - Check: Was a parameter renamed, removed, or had its type changed by a feature?
   - If YES → **TEST PROBLEM.** The test signature is stale.

3. **Does the test fail due to moved modules or renamed classes from this version?**
   - If YES → **TEST PROBLEM.** Fix the imports.

4. **Is the failing code path untouched by this version?**
   - Check: Does the failing code path appear in any diff from this version?
   - If NO → Investigate further:
     - Run `git log --oneline -5 -- <test_file>` and `git log --oneline -5 -- <production_file>`
     - Production code changed more recently than test → **TEST PROBLEM** (test not updated)
     - Test changed more recently than production code → **CODE PROBLEM** (test correctly catches a bug)

5. **Does the test pass in isolation but fail in the suite?**
   - If YES → **TEST PROBLEM** (ordering dependency or shared state issue).

6. **None of the above apply?**
   - Default: **CODE PROBLEM.** When in doubt, classify as code problem — false positives (extra backlog items) are cheaper than false negatives (silenced valid tests).

#### 3c. Fix Test Problems

- Update tests to match intentional behavior changes
- Fix stale imports and parameter names
- Do NOT change production code to make tests pass
- Do NOT delete or skip tests — update them to test the new behavior
- Every fix must cite a specific intentional change (from completion reports or THEME_INDEX)

#### 3d. Document Code Problems

For each code problem, record:
- Test file and test name
- Expected vs actual behavior
- Production file at fault
- Classification reasoning

These flow to Task 007 for backlog item creation.

### 4. Final Gate Check

After all test-problem fixes are applied, run `run_quality_gates` one final time.

- All pass → document success and proceed
- Only code-problem failures remain → document them for Task 007, proceed
- New unexpected failures appear → classify and handle (max 2 additional rounds)

## Output Requirements

Save outputs to `comms/outbox/versions/retrospective/${VERSION}/004-quality/`:

### README.md (required)

First paragraph: Quality gate summary (all pass / X failures remain).

Then:
- **Initial Results**: Table of check → pass/fail
- **Failure Classification**: Table of Test | File | Classification | Action | Backlog
- **Test Problem Fixes**: List of fixes applied with evidence citations
- **Code Problem Deferrals**: List of deferred items with classification reasoning
- **Final Results**: Table of check → pass/fail after fixes
- **Outstanding Failures**: Detailed description of any remaining failures

### quality-report.md

Full quality gate output including:
- Complete output from each check run
- Diff of any fixes applied
- Before/after comparison if fixes were made

## Allowed MCP Tools

- `run_quality_gates`
- `read_document`

## Guidelines

- Run gates at least once, even if you expect them to pass
- Do NOT weaken gate thresholds to make checks pass
- Do NOT skip any gate check
- Limit fix attempts to 2 rounds maximum — if gates fail after 2 rounds, document and move on
- Do NOT commit fix changes — the master prompt handles commits

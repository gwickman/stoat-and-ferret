# Recommendations: Preventing Async/Blocking Bugs

## Root Causes Identified

1. **No lint rule catches `subprocess.run()` inside async code.** Ruff rules `["E", "F", "I", "UP", "B", "SIM"]` don't include async-specific checks. Neither ruff nor mypy flag synchronous blocking calls inside `async def` functions.

2. **Feature requirements didn't carry async constraints forward.** v002 requirements for `ffprobe_video()` didn't specify async because no async caller existed. When v003 consumed it from async context, no review step verified compatibility.

3. **Known issue documented but not remediated.** v004 research (`codebase-patterns.md:100`) explicitly noted the blocking pattern but the theme scope only added the job queue — the underlying call was left unchanged. No backlog item was created at that time.

4. **No integration test exercises the async event loop under load.** All scan tests mock `ffprobe_video()`, so the blocking behavior is never observed in tests. No test verifies that the server remains responsive during a scan.

## Gaps Already Addressed Since Discovery

| Gap | Status | Evidence |
|-----|--------|----------|
| Bug identified and triaged | Done | BL-072 (P0, open) with clear acceptance criteria |
| Root cause documented | Done | `scan-directory-stuck` exploration with full flow analysis |
| Progress reporting gap | Identified | BL-073 (P1, open) |
| Job cancellation gap | Identified | BL-074 (P1, open) |

## Recommended Process Changes

### 1. Add Ruff Rule `ASYNC` to Quality Gates

**What:** Add `"ASYNC"` (or at minimum `"ASYNC100"`, `"ASYNC210"`, `"ASYNC220"`) to the ruff lint `select` list in `pyproject.toml`.

**Why:** Ruff's `ASYNC` rules flag common async anti-patterns. While no current ruff rule catches `subprocess.run()` inside async functions specifically (that would require `ASYNC210` from the `flake8-async` plugin with trio/anyio), adding the category establishes the foundation and catches other async pitfalls.

**Limitation:** As of ruff 0.4+, the `ASYNC` rules primarily target trio/anyio patterns, not raw asyncio. This alone won't catch the exact bug. See recommendation #3 for a complementary approach.

### 2. Add a Custom Lint Check for Blocking Calls in Async Context

**What:** Create a grep-based CI check or custom ruff rule that flags `subprocess.run(`, `subprocess.call(`, `subprocess.check_output(`, `time.sleep(` inside files that also contain `async def`.

**Why:** This is the most direct prevention. A simple script like:

```bash
# Find files with both async def and blocking subprocess calls
for f in $(grep -rl "async def" src/); do
  grep -n "subprocess\.run\|subprocess\.call\|time\.sleep" "$f" && echo "  ^ in $f"
done
```

This could be added as a quality gate check or pre-commit hook.

**Scope:** stoat-and-ferret only (not auto-dev-mcp tooling change).

### 3. Add an Event-Loop Responsiveness Integration Test

**What:** Create a test that starts a scan on a directory with multiple files, then verifies that `GET /api/v1/jobs/{id}` responds within a reasonable time (e.g., <2s) while the scan is running.

**Why:** This is the test that would have caught the bug. All current scan tests mock `ffprobe_video()`, so the blocking behavior is invisible. A test using real (or slow-simulated) subprocess calls would immediately reveal event loop starvation.

**Example shape:**
```python
async def test_server_responsive_during_scan():
    """Verify polling works while scan is active."""
    # Start scan on directory with test videos
    # Immediately poll job status
    # Assert poll returns within 2s (not blocked by scan)
```

### 4. Add "Async Safety" as a Review Criterion in Feature Design

**What:** When a feature's implementation plan calls a synchronous function from an `async def` context, the plan should explicitly note this and justify why it's acceptable (or specify the async alternative).

**Why:** The v003 implementation plan silently called `probe_video()` (sync) from `async def scan_directory()` without comment. If async safety were a review criterion, this would have been flagged at design time.

**Implementation:** Add to theme/feature design templates a section or checklist item: "Are any blocking calls (subprocess, file I/O, network) made inside async functions? If yes, document the mitigation (asyncio.to_thread, create_subprocess_exec, etc.)."

### 5. Create Backlog Items from Research Findings

**What:** When version research (like v004's `codebase-patterns.md`) identifies a code quality issue, require that a backlog item is created for it — even if it's outside the current version scope.

**Why:** v004 research identified the blocking pattern on `codebase-patterns.md:100` but no BL-xxx item was created. The issue was known and documented but fell through the cracks until a user hit it ~2 weeks later.

**Implementation:** Add to the research/critical-thinking phase checklist: "For each code quality issue identified during research, create a backlog item or link to an existing one."

## Priority Order

| # | Recommendation | Effort | Impact | Priority |
|---|---------------|--------|--------|----------|
| 2 | Custom blocking-in-async lint check | Low | High | P1 |
| 3 | Event-loop responsiveness integration test | Medium | High | P1 |
| 5 | Backlog items from research findings | Low | Medium | P1 |
| 4 | Async safety in design review | Low | Medium | P2 |
| 1 | Add ASYNC ruff rules | Trivial | Low | P3 |

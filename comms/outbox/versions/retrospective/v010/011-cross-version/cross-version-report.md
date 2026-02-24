# Cross-Version Analysis: v006-v010

## Data Coverage

| Version | Quality Report | Learnings | Backlog Report | Final Summary |
|---------|---------------|-----------|----------------|---------------|
| v006    | Present       | Present   | Present        | Present       |
| v007    | Present       | Present   | Present        | Present       |
| v008    | Present       | Present   | Present        | Present       |
| v009    | Present       | Present   | Present        | Present       |
| v010    | Present       | Present   | Present        | Present       |

All 5 versions had complete retrospective data. No versions were skipped.

## Generic Analysis

### Recurring Bugs and Failures

**No recurring code bugs detected across v006-v010.** All five versions achieved 100% quality gate pass rates on their retrospective runs:

| Version | ruff | mypy | pytest | Tests |
|---------|------|------|--------|-------|
| v006    | PASS | PASS | PASS   | 753   |
| v007    | PASS | PASS | PASS   | 884   |
| v008    | PASS | PASS | PASS   | 909   |
| v009    | PASS | PASS | PASS   | 956   |
| v010    | PASS | PASS | PASS   | 980   |

**One cross-version issue:** The flaky E2E test (BL-055, `project-creation.spec.ts`) appeared in v007 and persisted until v008 fixed it. This was a CI reliability issue (default Playwright timeout too short for GitHub Actions) rather than a code bug. It was successfully resolved with LRN-043 (explicit assertion timeouts).

**Tooling errors (session analytics):** Bash tool has a 15.7% error rate (919/5,865 calls) and Edit has 11.7% (126/1,074). These are process-level issues rather than code bugs, but they persist across versions. See Execution Analytics section for details.

### Persistent Quality Gaps

**No persistent code quality gaps detected.** All versions achieved:
- 0 mypy issues across 49 source files (consistent across all 5 versions)
- 0 ruff violations
- 100% test pass rates

**Process quality gap:** The ruff format-before-check ordering issue (LRN-052, v009) persists as a recurring friction point during implementation. Session analytics show nearly every implementation session encounters format failures on the first quality gate run, requiring at least one fix-and-rerun cycle.

**Architecture documentation gap:** C4 documentation has fallen behind since v008. See dedicated finding under PR-007.

### Efficiency Trends

**Feature completion rates are strong and improving:**

| Version | Features | Completed | First-Iteration | Themes |
|---------|----------|-----------|-----------------|--------|
| v006    | 8        | 8 (100%)  | 8 (100%)        | 3      |
| v007    | 11       | 9 (82%)   | 9 (82%)         | 4      |
| v008    | 4        | 4 (100%)  | 4 (100%)        | 2      |
| v009    | 6        | 6 (100%)  | 6 (100%)        | 2      |
| v010    | 5        | 5 (100%)  | 5 (100%)        | 2      |

**Observations:**
- v007 was the only version with non-100% completion (2 features partial due to pre-existing BL-055 E2E flake, not implementation issues)
- v008-v010 achieved 100% first-iteration success, likely due to well-scoped maintenance and wiring work (LRN-046)
- Feature count per version has decreased (8 -> 11 -> 4 -> 6 -> 5), suggesting more focused scoping
- Zero quality gate failures during execution across all 5 versions

**Test growth is steady and healthy:**
- v006: 753 tests
- v010: 980 tests
- Growth: +227 tests (+30.1%) over 5 versions, ~45 tests per version average
- No test count regressions in any version

### Execution Analytics

**Token consumption (v006-v010 aggregate):**

| Model | Sessions | Input Tokens | Output Tokens | Cache Read | Est. Cost |
|-------|----------|-------------|---------------|------------|-----------|
| claude-opus-4-6 | 243 | 1.2M | 264K | 2.18B | $5,047.68 |
| claude-haiku-4-5 | 106 | 399K | 21K | 398M | $0.00 |
| claude-sonnet-4-6 | 14 | 31K | 8K | 63M | $0.00 |

Opus dominates cost. Haiku is used effectively for sub-agent delegation (106 sessions, 0 cost).

**Tool failure rates (notable):**

| Tool | Calls | Errors | Error % | Assessment |
|------|-------|--------|---------|------------|
| WebFetch | 48 | 28 | 58.3% | Critically high — see PR-006 |
| health_check | 32 | 7 | 21.9% | MCP server restarts |
| deepwiki ask_question | 28 | 6 | 21.4% | External API timeouts |
| Bash | 5,865 | 919 | 15.7% | Expected (includes failed commands) |
| Edit | 1,074 | 126 | 11.7% | Elevated — see PR-005 |
| WebSearch | 146 | 7 | 4.8% | Acceptable |
| request_clarification | 49 | 2 | 4.1% | Acceptable |
| Glob | 2,113 | 60 | 2.8% | Acceptable |
| Read | 9,582 | 144 | 1.5% | Acceptable |

**Daily activity distribution:**
- Most active day: Feb 19 (122 sessions, 11,410 tool calls) — corresponds to v006 retrospective + v007 execution
- Activity is bursty: concentrated on specific days with gaps between
- 14 active days across 60-day window, averaging ~43 sessions per active day

### Backlog Hygiene

**Open backlog items: 11 BL items + 2 PR items**

**Stale items (open 3+ versions without scheduling):**

| Item | Title | Open Since | Versions Open | Priority Drift |
|------|-------|------------|---------------|----------------|
| BL-019 | Add Windows bash /dev/null guidance | v005 era (Feb 6) | 5+ versions | P1 -> P3 |

BL-019 is the only item that has been open for 3+ versions without being scheduled. See PR-008.

**Recently created items (v009-v010):** BL-061, BL-066-BL-079 are recent and appropriately in the pipeline. No staleness concerns.

**Scheduled-vs-completed ratios:**

| Version | Planned | Completed | Ratio |
|---------|---------|-----------|-------|
| v006    | 7 BL    | 7 BL      | 100%  |
| v007    | 9 BL    | 9 BL      | 100%  |
| v008    | 4 BL    | 4 BL      | 100%  |
| v009    | 6 BL    | 6 BL      | 100%  |
| v010    | 5 BL    | 5 BL      | 100%  |

Perfect completion ratios across all 5 versions. Every planned backlog item was delivered.

### Learning Effectiveness

**Learning corpus:** 59 active learnings (LRN-001 through LRN-059), with 34 created during v006-v010 (LRN-026 through LRN-059).

**Learnings with evidence of effectiveness:**
- **LRN-031** (detailed design specs): Referenced in v006 evidence, pattern continued through v008-v010 with consistent first-iteration success
- **LRN-033** (fix CI before dev cycles): v007 flaky E2E test was fixed in v008 as BL-055, confirming the learning was applied
- **LRN-042** (group by modification point): Applied in v009 Theme 01 (observability pipeline) with all 3 features modifying lifespan code
- **LRN-045** (single-feature themes for bugs): Applied in v010 Theme 01 (async-pipeline-fix), which was a focused bug-fix theme
- **LRN-046** (maintenance versions): v009 and v010 both achieved 100% first-iteration success with well-understood scopes

**Learnings with evidence of ineffectiveness:**
- **LRN-038** (sub-agent read-before-write): Captured in v007, but Edit error rate remains at 11.7% through v010. The learning exists but is not being operationalized in sub-agent prompts. See PR-005.
- **LRN-030** (architecture docs as explicit feature): Practiced in v006-v007, abandoned in v009-v010. C4 drift now at 16 items. The learning was not sustained. See PR-007.

**Learnings older than 5 versions that may need review:**
- LRN-001 through LRN-025 (pre-v006) are all older than the analysis range. These are foundational learnings from v001-v005. A targeted review of LRN-001 through LRN-003 (earliest, least detailed) may be warranted to ensure they remain relevant and accurate.

## Project-Specific Analysis

No project-specific configuration found (`docs/auto-dev/CROSS_VERSION_RETRO.md` does not exist).

## Product Requests Created

| ID | Title | Priority | Category |
|----|-------|----------|----------|
| PR-005 | High Edit tool error rate (11.7%) indicates persistent sub-agent workflow issue | P2 | Tooling / Error Rate |
| PR-006 | WebFetch tool 58.3% error rate wastes API round-trips across versions | P2 | Tooling / Error Rate |
| PR-007 | C4 architecture documentation drift accumulating across v009-v010 | P1 | Architecture / Documentation |
| PR-008 | BL-019 stale for 5 versions — schedule or cancel | P2 | Backlog Hygiene |

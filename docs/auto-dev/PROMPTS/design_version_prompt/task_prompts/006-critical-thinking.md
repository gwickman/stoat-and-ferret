# Task 006: Critical Thinking and Risk Investigation

Read AGENTS.md first and follow all instructions there.

## Objective

Review the logical design from Task 005, investigate all identified risks and unknowns, and produce a refined design with mitigations. This step ensures the design is robust BEFORE document drafting begins.

## Context

This is Phase 2 (Logical Design & Critical Thinking) for `${PROJECT}` version `${VERSION}`.

Task 005 produced a logical design with a "Risks and Unknowns" section. This task investigates each risk, resolves unknowns where possible, and produces an updated design that incorporates findings.

**IMPORTANT:** This task builds EXCLUSIVELY on Task 005's output and the existing design artifact store (001-004). Do NOT re-gather environment context, re-read backlogs, or duplicate work from Tasks 001-004.

## Tasks

### 1. Read the Logical Design

Read from the design artifact store:
- `comms/outbox/versions/design/${VERSION}/005-logical-design/logical-design.md`
- `comms/outbox/versions/design/${VERSION}/005-logical-design/risks-and-unknowns.md`
- `comms/outbox/versions/design/${VERSION}/005-logical-design/test-strategy.md`

### 2. Triage Risks

Categorize each risk/unknown from Task 005:
- **Investigate now**: Can be resolved with codebase queries, web search, or DeepWiki
- **Accept with mitigation**: Cannot be fully resolved, but a mitigation strategy exists
- **TBD - requires runtime testing**: Genuinely cannot be determined pre-implementation

### 3. Investigate Resolvable Risks

For each "Investigate now" item:
- Query the codebase using `request_clarification`
- Search external sources via DeepWiki or web search
- Spawn sub-explorations for complex investigations if needed
- Document findings with evidence (file paths, URLs, data)

**Empirical verification required:** Do not conclude that code "should behave X way" based solely on reading the code path. Where possible, verify against actual runtime data (test output, log files, state files). Architectural reasoning generates hypotheses; only empirical evidence confirms them. (See LRN-135.)

### 4. Define Mitigations

For each "Accept with mitigation" item:
- Document the specific mitigation strategy
- Identify which theme/feature is affected
- Note any changes to the logical design required

### 5. Refine the Logical Design

Based on investigation findings:
- Update theme groupings if risks revealed structural issues
- Adjust feature ordering if dependencies changed
- Add or modify features if risks require additional work
- Update test strategy with new test requirements from findings

### 6. Validate Design Coherence

Review the refined design for:
- ALL backlog items from PLAN.md still covered (mandatory scope — no deferrals allowed)
- No circular dependencies introduced
- Test strategy covers new risk mitigations
- Execution order still makes sense
- **Persistence coherence**: If Task 004 produced a `persistence-analysis.md`, validate that the logical design accounts for all identified storage concerns (location, isolation, lifecycle, path stability). Features that introduce persistent state but reference a storage path API that was **NOT verified** in Task 004 must be flagged as **BLOCKING** risk — unverified storage APIs have caused runtime failures in past versions (see BL-539)

## Output Requirements

Save outputs to `comms/outbox/versions/design/${VERSION}/006-critical-thinking/`:

### README.md (required)

First paragraph: Summary of critical thinking review — risks investigated, resolutions found, design changes made.

Then:
- **Risks Investigated**: Count and categories
- **Resolutions**: Key findings that changed the design
- **Design Changes**: What changed from Task 005's proposal
- **Remaining TBDs**: Items that require runtime testing
- **Confidence Assessment**: Overall confidence in the refined design

### risk-assessment.md

For each risk from Task 005:

```markdown
## Risk: [title]
- **Original severity**: [from Task 005]
- **Category**: [investigate now / accept with mitigation / TBD]
- **Investigation**: [what was done]
- **Finding**: [what was discovered]
- **Resolution**: [how the design addresses it]
- **Affected themes/features**: [which parts of the design]
```

### refined-logical-design.md

Updated logical design incorporating all findings. Same structure as Task 005's `logical-design.md` but with:
- Risk resolutions integrated
- Updated theme/feature structures (if changed)
- Updated execution order (if changed)
- References to risk-assessment.md for details

### investigation-log.md

Detailed log of all investigations performed:
- Codebase queries and results
- External research findings
- Sub-exploration results
- Evidence supporting each resolution

## Allowed MCP Tools

- `read_document`
- `request_clarification`
- `start_exploration` (with `allowed_mcp_tools=["ALL_ALLOWED"]` for investigations)
- `get_exploration_status`
- `get_exploration_result`
- `list_product_requests`
- `get_product_request`
- `add_product_request`
- `update_product_request`
- `upvote_item`

Plus DeepWiki tools:
- `mcp__deepwiki__ask_question`
- `mcp__deepwiki__read_wiki_structure`

## Guidelines

- ALL backlog items from PLAN.md are MANDATORY — risk investigation must not result in deferrals or descoping
- Do NOT re-read backlogs, re-check environment, or duplicate Tasks 001-004
- Build exclusively on Task 005's output and the design artifact store
- Document ALL investigation work — even dead ends are valuable
- If a risk investigation reveals a design-breaking issue, update the design
- If investigation cannot resolve a risk, document it as TBD with clear markers
- Keep each document under 200 lines
- Do NOT commit — the master prompt handles commits after this task

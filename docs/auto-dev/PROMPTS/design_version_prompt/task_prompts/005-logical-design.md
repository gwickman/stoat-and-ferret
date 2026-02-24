# Task 005: Logical Design Proposal

Read AGENTS.md first and follow all instructions there.

## Objective

Synthesize findings from Tasks 001-004 into a coherent logical design proposal with theme groupings, feature breakdowns, and test strategy.

## Context

This is Phase 2 (Logical Design & Critical Thinking) for `${PROJECT}` version `${VERSION}`.

All context is gathered. Now propose the structure. This proposal feeds into Task 006 (Critical Thinking) for risk review before document drafting begins.

## Tasks

### 1. Read Phase 1 Outputs

Read all design artifacts from the centralized store:
- `comms/outbox/versions/design/${VERSION}/001-environment/` — environment and version scope
- `comms/outbox/versions/design/${VERSION}/002-backlog/` — backlog details and retrospective
- `comms/outbox/versions/design/${VERSION}/004-research/` — research findings and evidence

### 2. Theme Groupings

Based on backlog items and research findings, propose logical themes:
- Group related features together
- Each theme should have 2-5 features
- Provide rationale for grouping decisions
- Consider dependencies and execution order

For each theme:
- Theme name (slug format: `NN-descriptive-name`)
- Theme goal (one paragraph)
- Features included (with backlog mappings)

### 3. Feature Breakdown

For each feature within themes:
- Feature name (slug format: `NNN-descriptive-name`)
- Feature goal (one sentence)
- Backlog item(s) addressed (BL-XXX references)
- Dependencies (features or themes that must complete first)

### 3a. End-to-End Acceptance Criteria for Observable Output

When a feature produces observable output (bug fixes, new endpoints, CLI commands, generated files, log entries, or any user-visible behavior):

- Require at least one acceptance criterion that validates **user-observable end-to-end behavior**, not just internal method correctness
- If the fix modifies a service method signature or adds a parameter, an AC must verify that the production caller passes the parameter and the user sees the corrected behavior
- Example: a fix that adds a `goal` parameter to a service method needs an AC verifying that the prompt template (production caller) supplies `goal` and the generated output reflects it

This prevents fixes that pass unit tests but remain practically ineffective because no caller was updated to exercise the fix (see LRN-079).

### 4. Execution Order

Propose the order for theme and feature execution:
- Document dependencies between themes
- Document dependencies between features within themes
- Provide rationale for ordering decisions

### 5. Test Strategy

For each feature, identify test requirements:
- **Unit tests**: New service/handler logic requiring unit tests
- **System/Golden scenarios**: Features that affect execution flows
- **Parity tests**: API/MCP tool changes requiring parity validation
- **Contract tests**: New DTO models requiring round-trip tests
- **Replay fixtures**: New execution patterns requiring replay scenarios

### 6. Research Sources Adopted

Document which research findings inform the design:
- Libraries or patterns selected
- Architectural decisions made
- Configuration values chosen
- Reference evidence by path: `comms/outbox/versions/design/${VERSION}/004-research/[file]`

### 7. Risks and Unknowns

**IMPORTANT:** This section feeds directly into Task 006 (Critical Thinking).

List all identified risks and unknowns:
- Technical risks (e.g., "unclear how X integrates with Y")
- Scope risks (e.g., "BL-XXX may be larger than estimated")
- Dependency risks (e.g., "theme 02 depends on theme 01 pattern")
- Any assumptions made that need validation

For each, provide:
- Description
- Severity (high/medium/low)
- What investigation would help resolve it
- Current best guess if unresolved (clearly labeled as UNVERIFIED — do not present guesses as conclusions)

### 8. Handler Concurrency Decisions

For each new MCP tool handler introduced in the version, evaluate the following:

1. **I/O Profile**: Does the handler perform filesystem I/O, database queries, network calls, or subprocess invocations? List each I/O operation and its expected latency.

2. **Event Loop Blocking Potential**: Will any I/O operation block the event loop for >100ms under normal conditions? If yes, the handler should be async with `run_in_executor` for blocking calls, or use native async I/O libraries.

3. **Concurrent Caller Support**: Can multiple clients call this handler simultaneously? If yes, ensure shared state is protected (e.g., file locks, atomic writes) or that the handler is stateless.

Document the sync/async decision and rationale for each new handler in the logical design output.

If no new handlers are introduced in the version, note "Not applicable — no new handlers" and skip the evaluation.

**Example entry:**
```
Handler: query_cli_sessions
- I/O Profile: filesystem scan + SQLite read (~200ms)
- Event Loop Blocking: Yes — SQLite I/O blocks >100ms
- Concurrent Callers: Yes — multiple clients may query simultaneously
- Decision: async with run_in_executor for DB operations
```

## Output Requirements

Save outputs to `comms/outbox/versions/design/${VERSION}/005-logical-design/`:

### README.md (required)

First paragraph: Summary of proposed structure (X themes, Y features total).

Then:
- **Theme Overview**: List of themes with goals
- **Key Decisions**: Major architectural or grouping decisions
- **Dependencies**: High-level execution order rationale
- **Risks and Unknowns**: Items needing investigation in Task 006

### logical-design.md

Complete logical design proposal:

#### Version Overview
- Version number and description
- Goals and objectives

#### Theme Breakdown

For each theme:
```markdown
## Theme N: [name]

**Goal**: [one paragraph]
**Backlog Items**: BL-XXX, BL-YYY

**Features**:
| # | Feature | Goal | Backlog | Dependencies |
|---|---------|------|---------|--------------|
| 1 | NNN-feature-name | [goal] | BL-XXX | None |
```

#### Execution Order
- Theme dependencies
- Feature dependencies
- Rationale

#### Research Sources
- Key findings adopted (reference 004-research/ by path)
- Patterns selected
- Values chosen with sources

### test-strategy.md

Test requirements per feature (same format as v1).

### risks-and-unknowns.md

All identified risks and unknowns for Task 006:

```markdown
## Risk: [title]
- **Severity**: [high/medium/low]
- **Description**: [what the risk is]
- **Investigation needed**: [what to check]
- **Current assumption**: [best guess]
```

## Allowed MCP Tools

- `read_document`
- `list_product_requests`
- `get_product_request`
- `add_product_request`
- `update_product_request`
- `upvote_item`

(All data should come from design artifact store, tasks 001-004)

## Guidelines

- Theme names should be descriptive and URL-friendly
- Feature names should be action-oriented
- ALL backlog items from PLAN.md are MANDATORY and must be mapped to a feature — no deferrals, no descoping
- Dependencies must be clear and explicit
- Evidence must come from Task 004, not new assumptions
- Reference the design artifact store by path, not by inlining
- Keep the main logical design document under 300 lines
- Feature execution environments have file-level tools only (Read/Write/Edit/Bash) — do not design features that require state-modifying MCP tool calls at execution time (read-only tools get_project_info and read_document are permitted)
- Do NOT commit — the master prompt handles commits after Phase 2

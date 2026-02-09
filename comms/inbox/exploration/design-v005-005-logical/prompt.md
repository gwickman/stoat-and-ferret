Read AGENTS.md first and follow all instructions there.

## Objective

Synthesize findings from Tasks 001-004 into a coherent logical design proposal with theme groupings, feature breakdowns, and test strategy for stoat-and-ferret version v005.

## Context

This is Phase 2 (Logical Design & Critical Thinking) for stoat-and-ferret version v005. All Phase 1 context is gathered. Now propose the structure. This proposal feeds into Task 006 (Critical Thinking) for risk review before document drafting begins.

v005 scope: GUI shell + library browser + project manager. Backlog items: BL-003, BL-028 through BL-036.

## Tasks

### 1. Read Phase 1 Outputs

Read all design artifacts from the centralized store:
- `comms/outbox/versions/design/v005/001-environment/README.md` — environment and version scope
- `comms/outbox/versions/design/v005/001-environment/version-context.md` — version context details
- `comms/outbox/versions/design/v005/002-backlog/README.md` — backlog overview
- `comms/outbox/versions/design/v005/002-backlog/backlog-details.md` — full backlog details
- `comms/outbox/versions/design/v005/002-backlog/retrospective-insights.md` — retrospective insights
- `comms/outbox/versions/design/v005/002-backlog/learnings-summary.md` — learnings
- `comms/outbox/versions/design/v005/003-impact-assessment/README.md` — impact overview
- `comms/outbox/versions/design/v005/003-impact-assessment/impact-table.md` — impact details
- `comms/outbox/versions/design/v005/004-research/README.md` — research findings
- `comms/outbox/versions/design/v005/004-research/codebase-patterns.md` — codebase patterns
- `comms/outbox/versions/design/v005/004-research/external-research.md` — external research
- `comms/outbox/versions/design/v005/004-research/evidence-log.md` — evidence
- `comms/outbox/versions/design/v005/004-research/impact-analysis.md` — impact analysis

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

### 4. Execution Order

Propose the order for theme and feature execution:
- Document dependencies between themes
- Document dependencies between features within themes
- Provide rationale for ordering decisions

### 5. Test Strategy

For each feature, identify test requirements:
- **Unit tests**: New service/handler logic requiring unit tests
- **Integration tests**: API endpoint tests
- **E2E tests**: Browser-level tests (for GUI features)
- **Contract tests**: New models requiring validation

### 6. Research Sources Adopted

Document which research findings inform the design:
- Libraries or patterns selected
- Architectural decisions made
- Configuration values chosen
- Reference evidence by path

### 7. Risks and Unknowns

**IMPORTANT:** This section feeds directly into Task 006 (Critical Thinking).

List all identified risks and unknowns with:
- Description
- Severity (high/medium/low)
- What investigation would help resolve it
- Current best guess if unresolved

## Output Requirements

Save ALL outputs to BOTH locations:

**Primary (exploration output):** `comms/outbox/exploration/design-v005-005-logical/`
**Design artifact store:** `comms/outbox/versions/design/v005/005-logical-design/`

Write identical files to both locations.

### README.md (required)

First paragraph: Summary of proposed structure (X themes, Y features total).

Then:
- **Theme Overview**: List of themes with goals
- **Key Decisions**: Major architectural or grouping decisions
- **Dependencies**: High-level execution order rationale
- **Risks and Unknowns**: Items needing investigation in Task 006

### logical-design.md

Complete logical design proposal with:
- Version overview (goals and objectives)
- Theme breakdown (for each theme: goal, backlog items, features table)
- Execution order with rationale
- Research sources adopted

### test-strategy.md

Test requirements per feature.

### risks-and-unknowns.md

All identified risks and unknowns for Task 006 review.

## Allowed MCP Tools

- `read_document`

(All data should come from design artifact store, tasks 001-004)

## Guidelines

- Theme names should be descriptive and URL-friendly
- Feature names should be action-oriented
- ALL backlog items from PLAN.md are MANDATORY and must be mapped to a feature — no deferrals
- Dependencies must be clear and explicit
- Evidence must come from Task 004, not new assumptions
- Reference the design artifact store by path, not by inlining
- Keep the main logical design document under 300 lines
- Do NOT commit — the orchestrator handles commits after Phase 2

Do NOT commit or push — the calling prompt handles commits. Results folder: design-v005-005-logical.
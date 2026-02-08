You are performing Task 005: Logical Design Proposal for stoat-and-ferret version v004.

Read AGENTS.md first and follow all instructions there.

PROJECT=stoat-and-ferret
VERSION=v004

## Objective

Synthesize findings from Tasks 001-004 into a coherent logical design proposal with theme groupings, feature breakdowns, and test strategy.

## Context

This is Phase 2 (Logical Design and Critical Thinking) for stoat-and-ferret version v004. All context is gathered. Now propose the structure. This proposal feeds into Task 006 (Critical Thinking) for risk review before document drafting begins.

## Tasks

### 1. Read Phase 1 Outputs

Read ALL design artifacts from the centralized store:
- `comms/outbox/versions/design/v004/001-environment/README.md` — environment and version scope
- `comms/outbox/versions/design/v004/001-environment/version-context.md` — version context
- `comms/outbox/versions/design/v004/002-backlog/README.md` — backlog overview
- `comms/outbox/versions/design/v004/002-backlog/backlog-details.md` — backlog details
- `comms/outbox/versions/design/v004/002-backlog/retrospective-insights.md` — retrospective
- `comms/outbox/versions/design/v004/003-impact-assessment/impact-table.md` — impacts
- `comms/outbox/versions/design/v004/004-research/README.md` — research findings
- `comms/outbox/versions/design/v004/004-research/codebase-patterns.md` — codebase patterns
- `comms/outbox/versions/design/v004/004-research/external-research.md` — external research
- `comms/outbox/versions/design/v004/004-research/evidence-log.md` — evidence
- `comms/outbox/versions/design/v004/004-research/impact-analysis.md` — impact analysis

### 2. Theme Groupings

Group related features into logical themes (2-5 features each):
- Consider dependencies and execution order
- Provide rationale for grouping decisions
- Use slug format: `NN-descriptive-name`

The v004 backlog items are (ALL MANDATORY):
- BL-020 (P1): InMemory test doubles for projects and jobs
- BL-021 (P1): Dependency injection for create_app()
- BL-022 (P1): Fixture factory with builder pattern
- BL-023 (P1): Black box test scenario catalog
- BL-024 (P2): Contract tests with real FFmpeg
- BL-025 (P2): Security audit of Rust sanitization
- BL-026 (P3): Rust vs Python performance benchmark
- BL-027 (P2): Async job queue for scan operations
- BL-009 (P2): Property test guidance in feature design template
- BL-010 (P3): Rust code coverage with llvm-cov
- BL-012 (P3): Fix coverage reporting gaps for ImportError fallback
- BL-014 (P2): Docker-based local testing option
- BL-016 (P3): Unify InMemory vs FTS5 search behavior

Dependencies: BL-021->BL-020, BL-022->BL-021, BL-023->BL-022, BL-027->BL-020

### 3. Feature Breakdown

For each feature within themes:
- Feature name (slug format: `NNN-descriptive-name`)
- Feature goal (one sentence)
- Backlog item(s) addressed
- Dependencies

### 4. Execution Order

Propose order for theme and feature execution with rationale.

### 5. Test Strategy

For each feature, identify test requirements: unit tests, system/golden scenarios, parity tests, contract tests, etc.

### 6. Research Sources Adopted

Document which research findings inform the design, referencing `comms/outbox/versions/design/v004/004-research/`.

### 7. Risks and Unknowns

IMPORTANT: This section feeds directly into Task 006.

List all identified risks and unknowns with description, severity, investigation needed, and current best guess.

## Output Requirements

Create findings in comms/outbox/exploration/design-v004-005-logical-design/:

### README.md (required)

First paragraph: Summary of proposed structure (X themes, Y features total).

Then:
- **Theme Overview**: List of themes with goals
- **Key Decisions**: Major architectural or grouping decisions
- **Dependencies**: High-level execution order rationale
- **Risks and Unknowns**: Items needing investigation in Task 006

### logical-design.md

Complete logical design proposal with version overview, theme breakdown (with feature tables), execution order, and research sources.

### test-strategy.md

Test requirements per feature.

### risks-and-unknowns.md

All identified risks and unknowns for Task 006.

## Guidelines

- Theme names should be descriptive and URL-friendly
- Feature names should be action-oriented
- ALL backlog items from PLAN.md are MANDATORY and must be mapped to a feature — no deferrals
- Dependencies must be clear and explicit
- Evidence must come from Task 004, not new assumptions
- Keep the main logical design document under 300 lines

## When Complete

After writing all output files to comms/outbox/exploration/design-v004-005-logical-design/, also COPY all files to comms/outbox/versions/design/v004/005-logical-design/ so they are in the design artifact store.

git add comms/outbox/exploration/design-v004-005-logical-design/
git commit -m "exploration: design-v004-005-logical-design - logical design complete"

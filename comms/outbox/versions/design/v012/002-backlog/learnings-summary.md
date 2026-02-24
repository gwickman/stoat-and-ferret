# Learnings Summary — v012

Relevant learnings from the project learning repository, filtered for applicability to v012 scope (API surface cleanup, bindings audit, GUI wiring, docs polish).

## Highly Relevant

### LRN-011: Python Business Logic, Rust Input Safety in Hybrid Architectures

- **Tags:** architecture, rust, python, hybrid, security, boundaries
- **Summary:** In hybrid Python/Rust architectures, Rust handles input sanitization and type safety while Python handles business policy and domain rules.
- **Applicability:** Directly informs BL-067 bindings audit. When evaluating validate_crf/validate_speed, determine whether Python ever needs these as standalone calls or whether Rust-internal validation in FFmpegCommand.build() is sufficient. If Python delegates all validation to Rust builders, standalone sanitization bindings are dead code.

### LRN-029: Conscious Simplicity with Documented Upgrade Paths

- **Tags:** decision-framework, architecture, yagni, simplicity, trade-offs
- **Summary:** Choose the simplest implementation for current scope but document explicit upgrade triggers.
- **Applicability:** When removing bindings in BL-067/BL-068, document what was removed and what conditions would trigger re-adding them. Particularly relevant for TimeRange list operations (potential Phase 3 Composition Engine need) and filter composition bindings (internal Rust usage works fine, but future Python-level composition might need them).

### LRN-031: Detailed Design Specifications Correlate with First-Iteration Success

- **Tags:** process, design, requirements, planning, quality
- **Summary:** Detailed design specs with specific acceptance criteria and implementation plans lead to first-iteration success.
- **Applicability:** All 5 v012 backlog items have well-structured descriptions with Current state/Gap/Impact format. Maintain this quality in the version design to continue the first-pass completion pattern seen in v011.

### LRN-062: Design-Time Impact Checks Shift Defect Detection Left

- **Tags:** process, design, quality, failure-mode, institutional-knowledge
- **Summary:** Codify recurring issue patterns into structured design-time checks to catch defects during version design.
- **Applicability:** Reference `IMPACT_ASSESSMENT.md` during v012 design. The cross-version wiring check is directly relevant to BL-061 (execute_command decision) and BL-066 (transition GUI wiring). The async safety check applies if BL-061 decides to wire execute_command into an async workflow.

## Moderately Relevant

### LRN-016: Validate Acceptance Criteria Against Codebase During Design

- **Tags:** process, design, requirements, validation
- **Summary:** Validate that acceptance criteria reference existing domain models and APIs during design phase.
- **Applicability:** BL-066 AC references `POST /projects/{id}/effects/transition` — verify this endpoint exists and has the expected interface. BL-067/BL-068 ACs reference specific function names — verify they still exist in current codebase.

### LRN-030: Architecture Documentation as an Explicit Feature Deliverable

- **Tags:** process, documentation, architecture, api-design, quality
- **Summary:** Dedicate an explicit feature to architecture documentation updates after implementation.
- **Applicability:** v012 removes bindings, changing the public API surface. C4 documentation should be updated, but BL-069 is excluded from v012. Note this gap — v012 may introduce new architecture drift.

### LRN-032: Schema-Driven Architecture Enables Backend-to-Frontend Consistency

- **Tags:** pattern, architecture, schema, frontend, backend
- **Summary:** Define data schemas once in the backend and use them to drive frontend UI generation.
- **Applicability:** BL-066 (transition GUI) should follow the schema-driven approach used by the existing Effect Workshop. The transition endpoint likely already provides a JSON schema that the GUI can consume.

### LRN-060: Wire Frontend to Existing Backend Endpoints Before Creating New Ones

- **Tags:** pattern, frontend, api-design, planning, efficiency
- **Summary:** Prioritize wiring frontend to existing backend endpoints — faster and fewer defects.
- **Applicability:** Directly applies to BL-066. The transition endpoint already exists — scope the feature as frontend-only wiring.

## Low Relevance (Context Only)

### LRN-009: Handler Registration Pattern for Generic Job Queues

- **Applicability:** May be tangentially relevant if BL-061 wires execute_command into the job queue system, but unlikely given v012's cleanup focus.

### LRN-019: Build Infrastructure First in Sequential Version Planning

- **Applicability:** v012's Theme 1 (rust-bindings-audit) should complete before Theme 2 (workshop-and-docs-polish) since BL-061 decisions affect audit scope. Already reflected in PLAN.md ordering.

### LRN-034: Validate Numeric Requirements Against Upstream Sources During Design

- **Applicability:** Relevant to BL-079 (API spec examples) — ensure realistic progress values match actual FFmpeg progress reporting behavior.

### LRN-037: Feature Composition Through Independent Store Interfaces

- **Applicability:** Relevant pattern for BL-066 GUI implementation — transitions should be a separate store composable with existing effect stores.

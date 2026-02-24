# Learnings Summary: Applicable to v011

## Directly Applicable

### LRN-031: Detailed Design Specifications Correlate with First-Iteration Success
- **Insight:** Detailed design specs with specific acceptance criteria, implementation plans, and scope boundaries lead to first-iteration feature success with no rework.
- **Applicability:** Critical for BL-075 (clip CRUD GUI) — the largest feature in v011. The design must specify exact UI layout, form fields, validation rules, and API integration points. Vague GUI specs lead to rework.

### LRN-032: Schema-Driven Architecture Enables Backend-to-Frontend Consistency
- **Insight:** Define data schemas once in the backend and use them to drive frontend UI generation, eliminating hardcoded components and ensuring consistent validation at both layers.
- **Applicability:** BL-075 should leverage existing Pydantic models for clip properties to generate form fields. This avoids duplicating validation logic between backend and frontend.

### LRN-037: Feature Composition Through Independent Store Interfaces
- **Insight:** Design each feature as a standalone component with an independent state store and clean interface; composition features can then orchestrate without modifying internals.
- **Applicability:** Both BL-070 (browse button) and BL-075 (clip CRUD) add new GUI components. These should follow the Zustand independent-store pattern to avoid coupling with existing page state.

### LRN-016: Validate Acceptance Criteria Against Codebase During Design
- **Insight:** Validate that acceptance criteria reference existing domain models and APIs during design phase to prevent unachievable requirements during execution.
- **Applicability:** BL-075's AC references specific API endpoints (POST, PATCH, DELETE on clips). Design must verify these endpoints exist with the expected signatures before committing to the implementation plan.

## Contextually Relevant

### LRN-029: Conscious Simplicity with Documented Upgrade Paths
- **Insight:** Choose the simplest implementation for current scope but document explicit upgrade triggers.
- **Applicability:** BL-070 (browse button) may have a simple implementation (backend directory listing API) vs a complex one (browser File System Access API). Document the simpler choice and when to upgrade.

### LRN-030: Architecture Documentation as an Explicit Feature Deliverable
- **Insight:** Dedicate an explicit feature to architecture documentation updates after implementation.
- **Applicability:** v011 is partially documentation-focused (BL-019, BL-071, BL-076). Ensure documentation changes are treated with the same rigor as code changes.

### LRN-034: Validate Numeric Requirements Against Upstream Sources
- **Insight:** Cross-check numeric claims in requirements against upstream source documentation.
- **Applicability:** Low direct applicability to v011 scope, but relevant if BL-075's clip time range validation references specific format constraints.

### LRN-011: Python Business Logic, Rust Input Safety
- **Insight:** In hybrid Python/Rust architectures, Rust handles input sanitization and type safety while Python handles business policy and domain rules.
- **Applicability:** BL-075's clip validation may involve Rust-side time range validation. The design should clarify which validation layer handles what.

### LRN-019: Build Infrastructure First in Sequential Version Planning
- **Insight:** Sequence infrastructure themes before consumer themes.
- **Applicability:** v011's PLAN.md already accounts for this: the developer-onboarding theme (infrastructure/process) has no dependency on scan-and-clip-ux (consumer features), and they can run in parallel.

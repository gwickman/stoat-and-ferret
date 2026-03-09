# Phase 3: Composition Engine Design

Phase 3 extends stoat-and-ferret with multi-clip timeline composition, layout-based compositions (PIP, split-screen), multi-track audio mixing, batch processing, and project versioning. The design builds on the established hybrid Python/Rust architecture: new Rust modules handle layout math, composition filter graph generation, and batch progress calculation, while Python provides the API layer, persistence, and orchestration. Four deferred Phase 2 quality items (BL-081 through BL-084) are resolved at the start of Phase 3 to establish a solid foundation before adding composition complexity. The design produces 30 backlog items (9 Small, 19 Medium, 2 Large) mapped across 4 suggested versions (v015–v018).

## Document Inventory

Read in this order:

| # | File | Description |
|---|------|-------------|
| 1 | `01-composition-data-models.md` | Pydantic and Rust struct definitions for timelines, tracks, clips, transitions, audio mixing, layouts, batch jobs, and project versions. Includes database schema additions. |
| 2 | `02-rust-core-design.md` | New Rust modules (layout, compose, batch) with function signatures, PyO3 bindings, and parallelism approach using Rayon. Extends existing audio module with AudioMixSpec. |
| 3 | `03-api-endpoints.md` | FastAPI endpoints for timeline CRUD, layout presets, audio mixing, batch rendering, and project version management. Includes request/response examples and error codes. |
| 4 | `04-test-strategy.md` | Test harness updates: Rust proptest strategies for layout and composition, black box test scenarios, FFmpeg contract tests, smoke tests, and CI gate changes. Addresses deferred Phase 2 quality items first. |
| 5 | `05-artifact-update-plan.md` | Complete inventory of all files needing creation (44 new) or modification (30 existing) across Rust core, Python backend, tests, GUI, design docs, and CI. |
| 6 | `06-backlog-items.md` | 30 backlog items with sizing, acceptance criteria, theme grouping, and suggested version mapping (v015–v018). Includes 4 deferred Phase 2 items to resolve first. |

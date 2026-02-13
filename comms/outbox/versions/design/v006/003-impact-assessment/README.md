# 003-Impact Assessment: v006 Effects Engine Foundation

Identified 14 impacts across 7 backlog items (BL-037 through BL-043): 12 small (sub-task scope) and 2 substantial (feature scope). No cross-version impacts. The Rust-heavy items (BL-037-041) primarily cause documentation and type stub impacts handled inline per-feature. The Python API items (BL-042-043) cause the two substantial impacts requiring upfront design.

## Generic Impacts

- **tool_help currency**: Not assessed — `tool_help` tool was not authorized for this exploration. v006 changes are project-internal (Rust modules, Python API endpoints) and do not modify MCP tool behavior or parameters.
- **Tool description accuracy**: No MCP tool descriptions are affected by v006 changes. The backlog items add project code, not MCP tooling.
- **Documentation review**: 4 design documents impacted:
  - `AGENTS.md` — Rust module listing and project structure tree (2 small impacts)
  - `02-architecture.md` — Rust module structure, Effects Service description, filter builder code example (3 small impacts)
  - `05-api-specification.md` — Effects endpoint implementation status (1 small impact)
  - `01-roadmap.md` — Phase 2 milestone checkbox updates (1 small impact)

## Project-Specific Impacts

N/A — no `docs/auto-dev/IMPACT_ASSESSMENT.md` exists for this project.

## Work Items Generated

- **12 small** — Type stubs, module registration, documentation updates, CI config, WebSocket events. All handled as sub-tasks within existing features or a documentation-update pass.
- **2 substantial** — Clip effects storage model (BL-043 prerequisite) and effect registry service design (BL-042 core component). Both require design decisions during logical design phase.
- **0 cross-version** — All impacts fit within v006 scope.

## Recommendations

1. **Clip effects model design**: The logical design phase should explicitly address how effects are stored on clips. The current data model has no effects field at any layer (Python schema, DB, Rust). This is BL-043's primary risk and should be designed before implementation begins, possibly warranting a brief exploration.

2. **Effect registry pattern**: BL-042's effect registry should be designed for extensibility (v007 will add more effects). The DI integration via `create_app()` kwargs follows established patterns (LRN-005), but the registry pattern itself needs specification.

3. **Documentation update pass**: Rather than updating docs incrementally, batch documentation updates (AGENTS.md, architecture docs, roadmap checkboxes) into a documentation sub-task in the final theme. This is lower risk than updating docs mid-implementation when APIs may still shift.

4. **Type stubs are inline work**: Per the incremental bindings rule in AGENTS.md, PyO3 bindings and stubs are always added in the same feature as Rust types. No separate feature needed — this is inherent to each Rust feature's definition of done.

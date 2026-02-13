# Impact Summary: v006

## Small Impacts (sub-task scope)

These can be handled as sub-tasks within existing features or as a documentation-update pass after implementation.

1. **Type stubs for new Rust types** — Each Rust feature (BL-037 through BL-041) adds new PyO3 types that need stubs in `_core.pyi`. Handled per-feature per the incremental bindings rule in AGENTS.md. *(Owning: BL-037, BL-038, BL-039, BL-040, BL-041)*

2. **`lib.rs` module registration** — New modules registered in the PyO3 `_core` module. Handled per-feature. *(Owning: BL-037 through BL-041)*

3. **AGENTS.md Rust module listing** — The documented Rust module structure (`timeline`, `filters`, `commands`, `sanitize`) will be incomplete after v006 adds expression engine, graph validation, and composition modules. *(Owning: final theme documentation pass)*

4. **AGENTS.md project structure tree** — New Python files for effects router, schemas, and services are not in the current tree. *(Owning: final theme documentation pass)*

5. **05-api-specification.md consistency** — The API spec documents effects endpoints in aspirational detail. After v006 implements a subset, annotations may be needed to distinguish implemented vs. planned endpoints. *(Owning: BL-042, BL-043)*

6. **02-architecture.md Rust module structure** — Architecture doc's Rust module listing needs updating for new modules. *(Owning: final theme documentation pass)*

7. **02-architecture.md Effects Service description** — Verify the documented Effects Service responsibilities match the actual BL-042/BL-043 implementation. *(Owning: BL-042, BL-043)*

8. **02-architecture.md filter builder code example** — Standalone function example will not match the builder struct pattern from BL-040. *(Owning: BL-040)*

9. **01-roadmap.md Phase 2 milestone checkboxes** — M2.1, M2.2, M2.3 checkboxes should be updated to reflect v006 completion. *(Owning: version completion pass)*

10. **Contract test infrastructure extension** — BL-040 needs filter-level contract tests; existing infrastructure supports command-level validation. Minor extension needed. *(Owning: BL-040)*

11. **CI matrix for contract tests** — Per LRN-015, ensure new FFmpeg contract tests from BL-040 run on a single CI matrix entry. *(Owning: BL-040)*

12. **WebSocket event types for effects** — New event types needed when effects are applied/removed. *(Owning: BL-043)*

## Substantial Impacts (feature scope)

These require dedicated features or significant design work within the version plan.

1. **Clip effects storage model** — BL-043 requires storing effect configurations on clips. The current clip model (Python schemas, DB repository, Rust `Clip` type) has no `effects` field. This is a multi-layer schema change that touches:
   - `src/stoat_ferret/api/schemas/clip.py` — Pydantic model
   - `src/stoat_ferret/db/clip_repository.py` — DB storage
   - Rust `Clip` struct (if effects need Rust-side validation)
   - Potentially DB migration for persisted clip data

   *Recommendation: Include clip effects model design as a prerequisite feature or first sub-task of BL-043. May warrant a design exploration before implementation.*

2. **Effect registry service with DI** — BL-042 requires a Python-side effect registry service that:
   - Registers available effects (text overlay from BL-040, speed control from BL-041)
   - Exposes effect metadata including parameter JSON schemas and AI hints
   - Integrates with `create_app()` DI pattern
   - Invokes Rust core for filter preview generation

   *Recommendation: Scope as a core component within the BL-042 feature. The registry pattern should be designed before implementation to ensure it's extensible for v007 effects.*

## Cross-Version Impacts (backlog scope)

None identified. All impacts are scoped within v006 or its immediate documentation updates.

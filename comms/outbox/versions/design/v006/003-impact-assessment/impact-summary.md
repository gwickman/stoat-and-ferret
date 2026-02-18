# Impact Summary by Classification - v006

## Small Impacts (sub-task scope)

These can be handled as sub-tasks within existing features during v006 execution.

- **#1 — AGENTS.md module listing**: Add new Rust submodule names (expressions, graph_validation, composition, drawtext, speed) to the Project Structure section. Attach to the first Rust theme. Owning feature: whichever theme implements BL-037.

- **#3 — 05-api-specification.md reconciliation**: After BL-042 (effect discovery API) and BL-043 (clip effect application) are implemented, reconcile the existing Effects section in the API spec with actual implementation details. Attach to the API theme. Owning feature: BL-043 (last API endpoint).

- **#4 — Type stub regeneration**: Run `cargo run --bin stub_gen` and update `stubs/stoat_ferret_core/_core.pyi` after each Rust feature that adds PyO3 bindings. This is already documented in AGENTS.md workflow — just ensure implementation plans include it. Owning features: BL-037, BL-039, BL-040, BL-041 (each independently).

- **#5 — PLAN.md status and investigation closure**: Update v006 status from "Planned" to "In Progress"/"Complete" and close the BL-043 investigation dependency. Owning feature: version-level bookkeeping during execution start and close.

- **#7 — 01-roadmap.md milestone checkboxes**: Check off M2.1-2.3 items in the roadmap during version close. Owning feature: version close process.

## Substantial Impacts (feature scope)

These require their own feature in the v006 plan due to scope and importance.

- **#2 — 02-architecture.md update**: The architecture document is the authoritative system reference. v006 changes it materially:
  - New Rust modules (expressions, graph_validation, composition, drawtext, speed) must be added to the module structure
  - Code examples showing filter building will be outdated (monolithic function → expression engine + builder pattern)
  - Effects Service description is currently a placeholder — v006 implements the real service with registry, discovery, and application
  - Data model needs clip effect storage field (BL-043)
  - PyO3 bindings section needs new class/function entries

  **Recommendation:** Create a dedicated documentation feature in the final theme of v006 that updates 02-architecture.md after all implementation is complete. This ensures the doc reflects the actual implementation rather than the planned design.

## Cross-Version Impacts (backlog scope)

These are too large for v006 and should be tracked for future work.

- **#6 — C4 architecture documentation**: C4 diagrams were not updated for v005 (frontend components missing) and v006 adds major new Rust modules. Full C4 regeneration spans code-level through context-level documentation across Python, Rust, and frontend layers. This is a multi-day effort unsuitable for inclusion in an effects engine version.

  **Recommendation:** Existing backlog item BL-018 ("Create C4 architecture documentation") covers this. After v006 completes, upvote or reprioritize BL-018 to include v005+v006 architectural additions. Consider scheduling as a standalone version or as part of v007's scope.

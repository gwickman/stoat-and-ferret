# v012 Learning Extraction — Detail

Full content of each learning saved during this extraction.

---

## LRN-063: Zero-Caller Verification Before Code Removal Eliminates Regression Risk

**Tags:** pattern, code-removal, risk-management, refactoring, verification
**Source:** v012/01-rust-bindings-cleanup retrospective, v012 version retrospective

### Context

When removing unused code (dead functions, deprecated API bindings, legacy bridge modules), the primary risk is breaking an unknown caller. This applies to any cleanup task where code is being deleted rather than modified.

### Learning

Before deleting any function, class, or module, grep the entire codebase for production callers. If the grep returns zero matches outside test files and the code being deleted, proceed with confidence. If any callers exist, the removal must be deferred or the callers must be migrated first. This single verification step converts a risky deletion into a safe, mechanical operation.

### Evidence

Three consecutive cleanup features all used this pattern (grepping for production callers before removal). All three completed with 100% acceptance criteria passing, zero test regressions, and clean quality gates. The pattern was cited by both theme-level and version-level retrospectives as the key risk-mitigation step.

### Application

1. Before any code removal PR, run a project-wide search for the function/class name
2. Exclude test files and the file being deleted from the search results
3. If zero production callers exist, proceed with deletion
4. Document the "zero callers" finding in the PR or completion report for reviewer confidence
5. If callers exist, convert the removal into a migration task instead

---

## LRN-064: Group Cleanup Removals by Origin Era for Cohesive PRs

**Tags:** pattern, code-removal, refactoring, planning, pr-strategy
**Source:** v012/01-rust-bindings-cleanup retrospective, v012 version retrospective

### Context

When a cleanup effort targets multiple items introduced across different project phases (e.g., deprecated APIs from v1 and v2, legacy modules from different feature cycles), the removal order matters for reviewability and risk management.

### Learning

Group items by their origin era or introduction phase, then remove them in chronological order from oldest to newest. This creates naturally cohesive PRs where all removed items share the same historical context, making reviews easier and building confidence progressively — simple, well-understood old code first, then more recent and potentially complex code.

### Evidence

A binding cleanup theme organized three features by era: a dead Python bridge function first (simplest, pure Python), then v001-era bindings (5 items with shared range/sanitize context), then v006-era bindings (6 items with shared expression/filter context). Each PR was self-contained and reviewable because all items shared origin context. The progression from simple to complex built reviewer confidence across the series.

### Application

1. When planning multi-item cleanup, inventory all items and tag them by origin (phase, version, feature)
2. Sort groups chronologically — oldest first
3. Create one PR per group, keeping all items from the same origin together
4. Start with the simplest group to establish the removal pattern
5. Each subsequent PR can reference the established pattern from earlier PRs

---

## LRN-065: Preserve Internal Implementations When Removing Public API Surface

**Tags:** pattern, architecture, api-design, code-removal, tech-debt
**Source:** v012/01-rust-bindings-cleanup retrospective, v012/01-rust-bindings-cleanup/002-v001-bindings-trim completion-report, v012/01-rust-bindings-cleanup/003-v006-bindings-trim completion-report

### Context

When trimming a public API surface (removing bindings, endpoints, or exported functions), the underlying implementation may still be used internally or may need to be re-exposed in the future. This applies to FFI boundaries, SDK surfaces, and any layered architecture where internal logic is wrapped by a public-facing layer.

### Learning

When removing public API wrappers, delete only the wrapper layer (bindings, exports, registrations) while preserving the internal implementation. Document the removal in a changelog with explicit re-add triggers describing the conditions under which the functionality should be re-exposed. This approach makes re-exposure a cheap, mechanical operation (add wrapper + registration) rather than a re-implementation.

### Evidence

Eleven PyO3 binding wrappers were removed from a Rust-Python boundary while all Rust-internal implementations (enums, methods, algorithms) were preserved. The changelog documented specific re-add triggers (e.g., "re-add when orchestrated multi-step pipelines need a unified entry point"). Internal tests continued passing because the underlying code was untouched.

### Application

1. Distinguish between the wrapper layer (bindings, exports) and the implementation layer (logic, algorithms)
2. Remove only the wrapper layer — imports, registrations, exports, public-facing stubs
3. Verify internal tests still pass (they should, since implementation is unchanged)
4. Document each removal in a changelog with a specific re-add trigger condition
5. When the trigger condition is met in a future version, re-adding is a small PR (wrapper + registration only)

---

## LRN-066: Optional Props Pattern Extends UI Components Without Breaking Existing Callers

**Tags:** pattern, gui, react, backward-compatibility, component-design
**Source:** v012/02-workshop-and-docs-polish/001-transition-gui completion-report, v012/02-workshop-and-docs-polish retrospective

### Context

When a UI component needs new behavior for a new feature (e.g., pair-selection mode for transitions) but existing callers depend on the current behavior (e.g., single-selection mode for effects), the component must be extended without breaking backward compatibility.

### Learning

Add new behavior as optional props with sensible defaults that preserve existing behavior. All new props should be optional (undefined by default), and when absent, the component behaves exactly as before. This avoids forking the component into two variants and keeps the codebase DRY. The same pattern applies to reusing existing form components (e.g., parameter forms) across different feature contexts.

### Evidence

A clip selector component was extended with optional pair-mode props (`pairMode`, `selectedFromId`, `selectedToId`, `onSelectPair`). All existing callers continued to work unchanged because the new props defaulted to undefined. A parameter form component was reused for transition parameter rendering without modification. The result: a full new feature tab was delivered with only 4 new files by reusing existing components.

### Application

1. When extending a component for a new feature, add new props as optional with `?` / `undefined` defaults
2. Guard new behavior behind `if (newProp)` checks so existing callers see no change
3. Before creating a new component, check if an existing one can be reused with optional props
4. Write tests for both the original behavior (props absent) and the new behavior (props present)
5. Use color-coding or visual differentiation to distinguish modes when the same component serves multiple purposes

---

## LRN-067: Execution Metadata Requires Same Automation as Code Artifacts

**Tags:** process, failure-mode, automation, execution-tracking, metadata
**Source:** v012/01-rust-bindings-cleanup retrospective, v012/02-workshop-and-docs-polish retrospective, v012 version retrospective

### Context

During version execution, multiple metadata artifacts track progress: state files recording feature completion counts, progress tracking documents, and quality gap records. When these require manual updates, they consistently fall out of sync with actual progress.

### Learning

Execution metadata (progress files, state files, quality gap records) drifts when it depends on manual updates. If an artifact is referenced by the process definition but requires a manual step to create or update, it will be skipped under time pressure. Either automate the metadata updates (triggered by PR merge or feature completion) or remove the metadata requirement from the process definition. The gap between "process says do X" and "X requires a manual step" is where drift originates.

### Evidence

Two consecutive themes in the same version both skipped progress.md creation despite the theme definition referencing it. A state file tracking feature completion counts remained at zero despite all features being complete and merged. Neither feature in the second theme produced quality-gaps.md files. The retrospectives for both themes independently flagged the same gaps, confirming it was systematic rather than accidental.

### Application

1. Audit process artifacts: identify which ones require manual creation/updates
2. For each manual artifact, decide: automate it, or remove it from the process
3. If automation isn't feasible, add the step to a checklist that gates the next action (e.g., "update state file before starting next feature")
4. If an artifact is consistently skipped across multiple iterations, it's a signal to either automate or drop the requirement
5. Distinguish between "nice to have" metadata and "required for next step" metadata — only enforce the latter

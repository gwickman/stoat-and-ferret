# Sizing Evidence Gathering: v008–v012

## Summary

Examined 25 backlog items across 5 versions (v008–v012) for sizing accuracy evidence. Findings were sourced from design documents (backlog-details.md), execution outputs (completion-report.md), and retrospective analyses (backlog README, proposals).

### Findings Count

| Category | Count |
|----------|-------|
| Total items examined | 25 |
| Accurately sized | 17 |
| Over-estimated | 6 |
| Under-estimated | 1 |
| Slightly conservative (within half-step) | 1 |

### Mis-sized Items

| Version | BL-ID | Title | Est | Actual | Direction |
|---------|-------|-------|-----|--------|-----------|
| v008 | BL-055 | Fix flaky E2E test | L | S | Over by 2 steps |
| v008 | BL-062 | Wire orphaned settings | L | S–M | Over by 1–2 steps |
| v010 | BL-077 | CI quality gate for async blocking | L | S–M | Over by 1–2 steps |
| v010 | BL-074 | Job cancellation support | M | L | Under by 1 step |
| v012 | BL-079 | API spec corrections | L | S–M | Over by 1–2 steps |
| v012 | BL-061 | Remove execute_command() bridge | L | M | Over by 1 step |

### Key Patterns

1. **Documentation-only and deletion tasks are systematically over-estimated.** BL-055 (single-line fix), BL-079 (5 text fixes), and BL-061 (dead code deletion) were all estimated at L but required S–M effort. Sizing heuristics should differentiate these task types from greenfield or cross-layer work.

2. **Cross-layer full-stack work is occasionally under-estimated.** BL-074 (job cancellation) was sized M based on the algorithm pattern being "well-understood," but the 5-layer implementation (queue → protocol → handler → API → frontend) pushed actual effort to L. Modification-point count is a better predictor than algorithmic familiarity.

3. **Wiring work with established patterns is highly predictable.** v009 achieved perfect sizing accuracy (6/6 items) because all items followed established DI and repository patterns. Pattern familiarity compresses variance.

4. **Over-estimation correlates with solution uncertainty.** BL-077 was estimated at L assuming a custom grep script, but the discovery of ruff's built-in ASYNC rules reduced it to a 1-line config change. When the implementation approach is uncertain at design time, estimates tend to assume the harder path.

5. **Sizing accuracy improved across versions.** v008 had 2 significant over-estimates out of 4 items (50% miss rate). v009–v011 achieved near-perfect calibration. v012 had 2 over-estimates out of 5 items but both were for task types (docs-only, deletion) that are inherently lower-effort.

### Calibration Recommendations (from retrospective sources)

- Use **S** for documentation-only text corrections (spec fixes, typo corrections)
- Use **S–M** for single-line configuration changes and known-root-cause bug fixes
- Use **M** for straightforward code deletion and dead-code removal
- Use **M** for DI wiring following established patterns
- Use **L** for cross-layer features, Rust PyO3 changes with stub regeneration, and new GUI components with state management
- Count **modification points** (distinct files/layers touched) rather than relying on algorithmic complexity assessment when sizing cross-cutting work

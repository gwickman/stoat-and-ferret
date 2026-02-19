# 005 Logical Design - v007 Effect Workshop GUI

Proposed structure: 4 themes, 11 features total (9 backlog items + 2 documentation features), covering audio mixing builders, video transitions, effect registry refactoring, GUI effect workshop, and end-to-end testing. All 9 backlog items (BL-044 through BL-052) are mapped to features with no deferrals.

## Theme Overview

| Theme | Name | Features | Goal |
|-------|------|----------|------|
| 01 | rust-filter-builders | 2 | Implement Rust builders for audio mixing (amix, volume, afade, ducking) and video transitions (fade, xfade, acrossfade) with PyO3 bindings |
| 02 | effect-registry-api | 3 | Refactor effect registry to builder-protocol dispatch, create transition API endpoint, update architecture docs |
| 03 | effect-workshop-gui | 4 | Build effect catalog, schema-driven parameter forms, live filter preview, and full builder workflow with CRUD |
| 04 | quality-validation | 2 | E2E Playwright tests with accessibility and API specification documentation |

## Key Decisions

- **Audio before transitions** (T01): Audio builders are simpler, establishing the template for the more complex two-input transition builders (LRN-028)
- **Custom form generator over RJSF** (T03): Lightweight custom implementation for 5-6 parameter types; RJSF documented as upgrade path if complexity grows
- **Preview thumbnails deferred**: Filter string preview (BL-050) serves as the v007 transparency mechanism; actual FFmpeg thumbnail rendering deferred to a future version
- **Effect CRUD via array index**: Uses existing JSON array storage with index-based operations; per-effect UUIDs documented as upgrade path
- **Registry refactoring as centerpiece** (T02): Replaces if/elif dispatch with build_fn lookup on EffectDefinition, fulfilling the v006 documented refactoring trigger
- **2 documentation features** added: Architecture docs (T02-F003) and API spec update (T04-F002) per LRN-030

## Dependencies

```
T01 (Rust Builders) ──→ T02 (Registry & API) ──→ T03 (GUI Workshop) ──→ T04 (Quality)
```

Strictly sequential theme execution following the infrastructure-first pattern validated in v006 (LRN-019). Within each theme, features are also sequential with later features building on earlier ones.

## Risks and Unknowns

Items requiring investigation in Task 006 (Critical Thinking):

| Risk | Severity | Summary |
|------|----------|---------|
| Two-input filter pattern untested | medium | xfade/sidechaincompress use FilterChain two-input path never exercised through PyO3 |
| Audio ducking composite pattern | medium | DuckingPattern composes multiple filters; no v006 precedent for composite builders |
| Registry refactoring scope | medium | Replacing _build_filter_string() touches critical effect application path |
| Effect CRUD schema stability | low | Array-index-based CRUD may need per-effect IDs for reordering |
| Preview thumbnails deferred | low | BL-051 AC #3 may expect rendered thumbnails, not filter string preview |
| SPA fallback routing | low | Deferred from v005; effect workshop URLs won't survive page refresh |
| Custom form generator trade-off | low | Custom implementation vs. RJSF dependency |
| Pre-existing mypy errors | low | 11 errors may interact with new typed code |
| Rust coverage gap | low | 75% vs 90% target; new code must not regress |

See `risks-and-unknowns.md` for full details including investigation recommendations.

## Artifacts

| File | Description |
|------|-------------|
| [logical-design.md](./logical-design.md) | Complete logical design with theme/feature breakdown, execution order, and research sources |
| [test-strategy.md](./test-strategy.md) | Test requirements per feature (~155 tests estimated across Rust, Python, frontend, E2E) |
| [risks-and-unknowns.md](./risks-and-unknowns.md) | 9 identified risks with severity, investigation needs, and current assumptions |

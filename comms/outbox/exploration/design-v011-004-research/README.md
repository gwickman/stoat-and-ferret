# Exploration: design-v011-004-research

Research and investigation for v011 version design covering all 5 mandatory backlog items.

## Artifacts Produced

All outputs saved to `comms/outbox/versions/design/v011/004-research/`:

| File | Description |
|------|-------------|
| README.md | Research scope, findings summary, learning verification, recommendations |
| codebase-patterns.md | Endpoint signatures, Pydantic models, React/Zustand patterns, Settings audit |
| external-research.md | showDirectoryPicker browser support, Zustand patterns (DeepWiki), IMPACT_ASSESSMENT format |
| evidence-log.md | Concrete values with sources for all parameters investigated |
| impact-analysis.md | Dependencies, breaking changes, test needs, documentation updates |

No `persistence-analysis.md` needed — no features introduce persistent state.

## Key Findings

1. **BL-075**: All clip CRUD endpoints exist and are tested. Frontend has zero callers of write endpoints. ClipCreate schema has no `label` field (AC mismatch).
2. **BL-070**: `showDirectoryPicker()` is Chromium-only. Recommend backend directory listing endpoint with `allowed_scan_roots` security.
3. **BL-071**: 11 Settings fields found; config docs only cover 9.
4. **BL-076**: 4 concrete project-history examples ready for impact assessment checks.
5. **BL-019**: Straightforward documentation addition after Commands section in AGENTS.md.
6. **All 6 referenced learnings verified as active and applicable.**

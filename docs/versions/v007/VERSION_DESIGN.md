# v007 Version Design

## Overview

**Version:** v007
**Title:** Effect Workshop GUI — Complete remaining effect types (audio mixing, transitions), build the effect registry with JSON schema validation and registry-based dispatch, and construct the full GUI effect workshop with catalog UI, parameter forms, and live preview. Covers milestones M2.4-2.6, M2.8-2.9.
**Themes:** 4

## Backlog Items

- [BL-044](docs/auto-dev/BACKLOG.md#bl-044)
- [BL-045](docs/auto-dev/BACKLOG.md#bl-045)
- [BL-046](docs/auto-dev/BACKLOG.md#bl-046)
- [BL-047](docs/auto-dev/BACKLOG.md#bl-047)
- [BL-048](docs/auto-dev/BACKLOG.md#bl-048)
- [BL-049](docs/auto-dev/BACKLOG.md#bl-049)
- [BL-050](docs/auto-dev/BACKLOG.md#bl-050)
- [BL-051](docs/auto-dev/BACKLOG.md#bl-051)
- [BL-052](docs/auto-dev/BACKLOG.md#bl-052)

## Design Context

### Rationale

v007 builds on v006's effects engine foundation to deliver the complete effect workshop: new Rust filter builders for audio and transitions, a refactored effect registry with builder-protocol dispatch and JSON schema validation, and the full GUI for discovering, configuring, previewing, and managing effects on clips.

### Constraints

- v006 effects engine must be complete (provides filter expression engine, graph validation, text overlay, speed control, EffectRegistry)
- v005 GUI shell must be complete (provides React/TypeScript/Vite, Zustand stores, WebSocket, component patterns)
- Non-destructive editing: never modify source files
- Rust for compute, Python for orchestration
- Transparency: API responses include generated FFmpeg filter strings
- SPA fallback routing still deferred (LRN-023)

### Assumptions

- Rust builder pattern from v006 (LRN-028) extends to audio and transition domains without modification
- Two-input filter pattern (xfade, acrossfade) works via existing FilterChain.input() API
- Custom form generator handles 5-6 parameter types without RJSF dependency
- Array-index-based effect CRUD is sufficient for single-user v007 scope
- Pre-existing mypy errors (11) do not block new code

### Deferred Items

- Preview thumbnails (server-side FFmpeg rendering) — filter string preview used instead
- SPA fallback routing for deep links
- UUID-based effect IDs (array index used for v007)
- RJSF migration (custom form generator used for v007)

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-rust-filter-builders | Implement Rust filter builders for audio mixing and video transitions, extending the proven v006 builder pattern to two new effect domains. | 2 |
| 2 | 02-effect-registry-api | Refactor the effect registry to use builder-protocol dispatch, add JSON schema validation, create the transition API endpoint, and document architectural changes. | 3 |
| 3 | 03-effect-workshop-gui | Build the complete Effect Workshop GUI: catalog, schema-driven forms, live preview, and full builder workflow. | 4 |
| 4 | 04-quality-validation | Validate the complete effect workshop through E2E testing with accessibility compliance and update API specification documentation. | 2 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (rust-filter-builders): Implement Rust filter builders for audio mixing and video transitions, extending the proven v006 builder pattern to two new effect domains.
- [ ] Theme 02 (effect-registry-api): Refactor the effect registry to use builder-protocol dispatch, add JSON schema validation, create the transition API endpoint, and document architectural changes.
- [ ] Theme 03 (effect-workshop-gui): Build the complete Effect Workshop GUI: catalog, schema-driven forms, live preview, and full builder workflow.
- [ ] Theme 04 (quality-validation): Validate the complete effect workshop through E2E testing with accessibility compliance and update API specification documentation.

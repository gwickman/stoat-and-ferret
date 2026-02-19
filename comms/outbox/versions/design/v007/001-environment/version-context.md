# Version Context - v007 Effect Workshop GUI

Source: `docs/auto-dev/PLAN.md`

## Version Goals

Complete remaining effect types (audio mixing, transitions), build the effect registry with JSON schema validation, and construct the full GUI effect workshop with catalog UI, parameter forms, and live preview. Covers milestones M2.4-2.6, M2.8-2.9.

## Backlog Items

9 items planned (BL-044 through BL-052):

| ID | Priority | Title |
|----|----------|-------|
| BL-044 | P1 | Implement audio mixing filter builders |
| BL-045 | P1 | Implement transition filter builders |
| BL-046 | P1 | Create transition API endpoint |
| BL-047 | P1 | Build effect registry with JSON schema validation |
| BL-048 | P1 | Build effect catalog UI |
| BL-049 | P1 | Build dynamic parameter form generator |
| BL-050 | P1 | Implement live filter preview |
| BL-051 | P1 | Build effect builder workflow |
| BL-052 | P2 | E2E tests for effect workshop |

## Dependency Chain

```
BL-044 (audio) ──┐
                  ├──→ BL-047 (registry) → BL-048 (catalog UI) → BL-049 (param forms) → BL-050 (preview) ──┐
BL-045 (trans.) ──┘                                                                                         ├→ BL-051 (workflow) → BL-052 (E2E)
     │                                                                                                      │
     └──→ BL-046 (trans. API)                                                                    BL-048+049─┘
```

All items depend on v006 (effects engine) and v005 (frontend). BL-044/045 depend on BL-037 (expression engine, delivered in v006).

## Investigation Dependencies

Two pending investigations that should inform v007 design:

| ID | Question | Status |
|----|----------|--------|
| BL-047 | Effect registry schema and builder protocol design | pending |
| BL-051 | Preview thumbnail pipeline (frame extraction + effect application) | pending |

These are listed as pending investigations in PLAN.md and may need exploration before or during implementation.

## Constraints and Assumptions

- **v006 complete:** Effects engine foundation is delivered, providing the filter expression engine, graph validation, text overlay, speed control, and initial EffectRegistry
- **v005 complete:** GUI shell with React/TypeScript/Vite, Zustand stores, WebSocket support, and component patterns are established
- **Non-destructive editing:** Core architectural constraint — never modify source files
- **Rust for compute:** Audio/transition filter builders will be implemented in Rust with PyO3 bindings (incremental binding rule)
- **Python for orchestration:** API endpoints, effect registry orchestration in Python
- **Transparency:** API responses include generated FFmpeg filter strings

## Deferred Items to Be Aware Of

From previous versions:
- **SPA fallback routing for deep links** (from v005) — may affect effect workshop URL routing
- **WebSocket connection consolidation** (from v005) — live preview may use WebSocket
- **Rust coverage at 75%** (target 90%, from v004) — new Rust code should maintain coverage
- **Drop-frame timecode** (from v001) — not relevant to v007

## Prior Version Context

v006 delivered the effects engine foundation that v007 builds on:
- Greenfield Rust filter expression engine with type-safe Expr builder API
- Filter graph validation with cycle detection (Kahn's algorithm)
- Filter composition system with LabelGenerator
- DrawtextBuilder with position presets and alpha fade
- SpeedControl with setpts/atempo and automatic chaining
- EffectRegistry with effect discovery API
- Clip effect application endpoint with effects_json storage

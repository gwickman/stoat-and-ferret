# stoat-and-ferret - Development Plan

> Bridge between strategic roadmap and auto-dev execution.
> 
> Strategic Roadmap: `docs/design/01-roadmap.md`
> Last Updated: 2025-01-25

## Roadmap → Version Mapping

| Version | Roadmap Reference | Focus | Prerequisites | Status |
|---------|-------------------|-------|---------------|--------|
| v001 | Phase 1, M1.1-1.3 | Foundation + Rust core basics | EXP-001, EXP-002 | complete |
| v002 | Phase 1, M1.4-1.5 | Database + FFmpeg integration | v001 | complete |
| v003 | Phase 1, M1.6-1.7 | API layer + Clip model | v002 | planned |
| v004 | Phase 1, M1.8-1.9 | Testing infrastructure + quality verification | v003 | planned |
| v005 | Phase 1, M1.10-1.12 | GUI shell + library browser + project manager | v004 | planned |
| v006 | Phase 2, M2.1-2.3 | Effects engine foundation | v005 | planned |
| v007 | Phase 2, M2.4-2.6 | Effect Workshop GUI | v006 | planned |

## Investigation Dependencies

Track explorations that must complete before version design.

| ID | Question | Informs | Status | Results |
|----|----------|---------|--------|---------|
| EXP-001 | PyO3/maturin hybrid build workflow — dev experience, CI setup, stub generation | v001 | complete | [rust-python-hybrid](../../comms/outbox/exploration/rust-python-hybrid/) |
| EXP-002 | Recording fake pattern — concrete implementation for RecordingFFmpegExecutor | v001, v004 | complete | [recording-fake-pattern](../../comms/outbox/exploration/recording-fake-pattern/) |
| EXP-003 | FastAPI static file serving — GUI deployment from API server | v005 | pending | - |

## Scoping Decisions

### v001 Boundary

**Included:** Milestones 1.1, 1.2, 1.3
- Project setup with Python + Rust tooling
- Rust core: timeline math, validation, FFmpeg command builder
- PyO3 bindings with type stubs

**Rationale:** These form the foundation that everything else builds on. The Rust core must be working before any Python integration can proceed meaningfully.

**Deferred:** Database (M1.4) requires stable Rust types to define schemas.

### v002 Boundary

**Included:** Milestones 1.4, 1.5
- SQLite with repository pattern
- FFmpeg executor with dependency injection
- Integration between Rust command builder and Python executor

**Rationale:** Database and FFmpeg integration share similar testing patterns (recording fakes, contract tests). Natural to develop together.

### v003 Boundary

**Included:** Milestones 1.6, 1.7
- FastAPI REST endpoints
- Request correlation, metrics middleware
- Clip model using Rust timeline math

**Rationale:** API layer is the primary interface. Must be solid before building testing infrastructure around it.

### v004 Boundary

**Included:** Milestones 1.8, 1.9
- Black box testing harness
- Recording test doubles
- Contract tests for FFmpeg commands
- Quality verification suite

**Rationale:** Testing infrastructure is substantial enough to warrant its own version. Builds on stable API from v003.

### v005 Boundary

**Included:** Milestones 1.10, 1.11, 1.12
- GUI shell with React/Svelte + Vite
- Library browser component
- Project manager component

**Rationale:** GUI milestones are tightly coupled — shell provides frame for browser and manager.

## Deferred Items

Items explicitly deferred during version design, with target versions.

| Item | From | To | Rationale |
|------|------|----|-----------|
| Structured logging with correlation ID | M1.1 | v003 | Requires API layer for request context |
| Prometheus metrics (/metrics endpoint) | M1.1 | v003 | Requires API layer |
| Health check endpoints (/health/*) | M1.1 | v003 | Requires API layer |
| Externalized settings (pydantic-settings) | M1.1 | v003 | Requires API layer for configuration |
| Project duration calculations | M1.2 | v003 | Requires Clip model |
| Encoding preset builder | M1.3 | v002 | Needed for FFmpeg executor integration |
| Contract tests with real FFmpeg | M1.3 | v004 | Part of testing infrastructure version |
| Drop-frame timecode support | M1.2 | TBD | Complex; start with non-drop-frame only |

## Completed Versions

| Version | Date | Summary |
|---------|------|---------|  
| v001 | 2026-01-26 | Foundation version: Python/Rust tooling, timeline math, FFmpeg command builder |
| v002 | 2026-01-27 | Database & FFmpeg integration: Python bindings completion, SQLite with repository pattern, FFmpeg executor with observability |

## Backlog Integration

Work that surfaces during planning or execution but doesn't fit current scope:

| Tag | Purpose |
|-----|---------|
| `investigation` | Needs exploration before implementation |
| `deferred` | Known work explicitly pushed to later |
| `discovered` | Found during execution, not originally planned |
| `blocked` | Waiting on external dependency |

## Change Log

| Date | Change | Rationale |
|------|--------|-----------|
| 2025-01-25 | Initial plan created | Project bootstrap, mapping Phase 1-2 milestones to versions |
| 2025-01-25 | EXP-001, EXP-002 complete | Investigations for v001 prerequisites |
| 2025-01-25 | v001 design complete | 3 themes, 10 features designed |
| 2026-01-26 | v001 complete | Foundation version delivered |
| 2026-01-27 | v002 complete | Database & FFmpeg integration delivered (4 themes, 13 features) |

# stoat-and-ferret - Development Plan

> Bridge between strategic roadmap and auto-dev execution.
>
> Strategic Roadmap: `docs/design/01-roadmap.md`
> Last Updated: 2026-02-08

## Current Focus

**Recently Completed:** v003 (API layer + Clip model)
**Upcoming:** v004 (testing infrastructure + quality verification)

## Roadmap → Version Mapping

| Version | Roadmap Reference | Focus | Status |
|---------|-------------------|-------|--------|
| v007 | Phase 2, M2.4–2.6, M2.8–2.9 | Effect Workshop GUI: audio mixing, transitions, effect registry, catalog UI, parameter forms, live preview | 📋 planned |
| v006 | Phase 2, M2.1–2.3 | Effects engine foundation: filter expression engine, graph validation, text overlay, speed control | 📋 planned |
| v005 | Phase 1, M1.10–1.12 | GUI shell + library browser + project manager | 📋 planned |
| v004 | Phase 1, M1.8–1.9 | Testing infrastructure + quality verification | 📋 planned |
| v003 | Phase 1, M1.6–1.7 | API layer + Clip model | ✅ complete |
| v002 | Phase 1, M1.4–1.5 | Database + FFmpeg integration | ✅ complete |
| v001 | Phase 1, M1.1–1.3 | Foundation + Rust core basics | ✅ complete |

## Investigation Dependencies

Track explorations that must complete before version design.

| ID | Question | Informs | Status |
|----|----------|---------|--------|
| EXP-001 | PyO3/maturin hybrid build workflow — dev experience, CI setup, stub generation | v001 | complete |
| EXP-002 | Recording fake pattern — concrete implementation for RecordingFFmpegExecutor | v001, v004 | complete |
| EXP-003 | FastAPI static file serving — GUI deployment from API server | v005 | pending |
| BL-028 | Frontend framework selection (extends EXP-003) | v005 | pending |
| BL-043 | Clip effect model design (how effects attach to clips) | v006 | pending |
| BL-047 | Effect registry schema and builder protocol design | v007 | pending |
| BL-051 | Preview thumbnail pipeline (frame extraction + effect application) | v007 | pending |

## Planned Versions

### v004 - Testing Infrastructure & Quality Verification (Planned)

**Goal:** Black box testing harness, recording test doubles, contract tests, quality verification suite. Milestones M1.8–1.9.
**Estimated scope:** 8 new items + 5 existing items retagged

**New Items (BL-020–027):**
- BL-020 (P1): Implement InMemory test doubles for projects and jobs
- BL-021 (P1): Add dependency injection to create_app()
- BL-022 (P1): Build fixture factory with builder pattern
- BL-023 (P1): Implement black box test scenario catalog
- BL-024 (P2): Contract tests with real FFmpeg
- BL-025 (P2): Security audit of Rust sanitization
- BL-026 (P3): Rust vs Python performance benchmark
- BL-027 (P2): Async job queue for scan operations

**Existing Items Retagged:**
- BL-009 (P2): Add property test guidance to feature design template
- BL-010 (P3): Configure Rust code coverage with llvm-cov
- BL-012 (P3): Fix coverage reporting gaps for ImportError fallback
- BL-014 (P2): Add Docker-based local testing option
- BL-016 (P3): Unify InMemory vs FTS5 search behavior

**Dependencies:** BL-021→BL-020, BL-022→BL-021, BL-023→BL-022, BL-027→BL-020

### v005 - GUI Shell, Library Browser & Project Manager (Planned)

**Goal:** Frontend project from scratch, WebSocket support, application shell, library browser with thumbnails, project manager. Milestones M1.10–1.12.
**Estimated scope:** 9 new items + 1 existing prerequisite

**New Items (BL-028–036):**
- BL-028 (P1): EXP: Frontend framework selection and Vite setup
- BL-029 (P1): Implement WebSocket endpoint for real-time events
- BL-030 (P1): Build application shell and navigation
- BL-031 (P2): Build dashboard panel
- BL-032 (P1): Implement thumbnail generation pipeline
- BL-033 (P1): Build library browser
- BL-034 (P2): Fix pagination total count
- BL-035 (P1): Build project manager
- BL-036 (P2): E2E test infrastructure

**Existing:** BL-003 (EXP-003: FastAPI static file serving)

**Dependencies:** Depends on v004 (black box tests validate GUI backend). BL-030→BL-028, BL-033→BL-028+BL-032, BL-036→BL-030+BL-033+BL-035

### v006 - Effects Engine Foundation (Planned)

**Goal:** Greenfield Rust filter expression engine, graph validation, text overlay, speed control, effect discovery API. Milestones M2.1–2.3.
**Estimated scope:** 7 items

**Items (BL-037–043):**
- BL-037 (P1): Implement FFmpeg filter expression engine in Rust
- BL-038 (P1): Implement filter graph validation
- BL-039 (P1): Build filter composition system
- BL-040 (P1): Implement drawtext filter builder
- BL-041 (P1): Implement speed control filters
- BL-042 (P2): Create effect discovery API endpoint
- BL-043 (P2): Apply text overlay to clip API

**Dependencies:** Independent of v005 (pure Rust + API work). BL-039→BL-038, BL-040→BL-037, BL-042→BL-040+BL-041, BL-043→BL-040+BL-042. BL-043 may need EXP for clip effect model.

### v007 - Effect Workshop GUI (Planned)

**Goal:** Complete remaining effects (audio, transitions), build effect registry, construct full GUI workshop. Milestones M2.4–2.6, M2.8–2.9.
**Estimated scope:** 9 items

**Items (BL-044–052):**
- BL-044 (P1): Implement audio mixing filter builders
- BL-045 (P1): Implement transition filter builders
- BL-046 (P1): Create transition API endpoint
- BL-047 (P1): Build effect registry with JSON schema validation
- BL-048 (P1): Build effect catalog UI
- BL-049 (P1): Build dynamic parameter form generator
- BL-050 (P1): Implement live filter preview
- BL-051 (P1): Build effect builder workflow
- BL-052 (P2): E2E tests for effect workshop

**Dependencies:** Depends on v006 (effects engine) and v005 (frontend project). BL-044/045→BL-037 (expression engine), BL-046→BL-045, BL-047→BL-044+BL-045, BL-048→BL-047, BL-049→BL-048, BL-050→BL-049, BL-051→BL-048+BL-049+BL-050, BL-052→BL-051

## Completed Versions

### v003 - API Layer + Clip Model (2026-01-28)
- **Themes:** process-improvements, api-foundation, library-api, clip-model
- **Features:** 15 completed across 4 themes
- **Backlog Resolved:** BL-013, BL-015, BL-017
- **Key Changes:** FastAPI REST API with request correlation and metrics middleware, async repository layer, video library endpoints (CRUD + search + scan), clip and project data models with Rust validation, CI improvements
- **Deferred:** WebSocket support (→ v005), async scan job queue (→ v004)

### v002 - Database & FFmpeg Integration (2026-01-27)
- **Themes:** 4 themes, 13 features
- **Key Changes:** Python bindings completion, SQLite with repository pattern and FTS5 search, FFmpeg executor with dependency injection and observability, recording fake pattern for FFmpeg
- **Deferred:** Unify InMemory vs FTS5 search behavior (→ v004)

### v001 - Foundation (2026-01-26)
- **Themes:** 3 themes, 10 features
- **Key Changes:** Python/Rust hybrid tooling (maturin, PyO3), timeline math module (pure functions), FFmpeg command builder with filter chain/graph, input sanitization, type stubs
- **Deferred:** Contract tests with real FFmpeg (→ v004), drop-frame timecode (→ TBD)

## Deferred Items

| Item | From | To | Rationale |
|------|------|----|-----------|
| Contract tests with real FFmpeg | M1.3 | v004 | Part of testing infrastructure version |
| Drop-frame timecode support | M1.2 | TBD | Complex; start with non-drop-frame only |

## Backlog Integration

Work categories:

| Tag | Purpose |
|-----|---------|
| `investigation` | Needs exploration before implementation |
| `deferred` | Known work explicitly pushed to later |
| `discovered` | Found during execution, not originally planned |
| `blocked` | Waiting on external dependency |

**Version-agnostic items** (can be addressed opportunistically):
- BL-011 (P3): Consolidate Python/Rust build backends
- BL-018 (P2): Create C4 architecture documentation
- BL-019 (P1): Add Windows bash /dev/null guidance to AGENTS.md

Query: `list_backlog_items(project="stoat-and-ferret", status="open")`

## Change Log

| Date | Change |
|------|--------|
| 2026-02-08 | Rewrote plan.md to match auto-dev-mcp format. Added Planned Versions sections for v004–v007 with full backlog item listings and dependency chains. |
| 2026-02-08 | Gap analysis completed (backlog-gap-analysis exploration). Created 33 new backlog items (BL-020–052) for v004–v007. Retagged 5 existing items to v004. Updated plan with backlog coverage and scoping decisions for v006/v007. |
| 2026-01-28 | v003 complete: API layer + Clip model delivered (4 themes, 15 features, BL-013/015/017 completed) |
| 2026-01-27 | v002 complete: Database & FFmpeg integration delivered (4 themes, 13 features) |
| 2026-01-26 | v001 complete: Foundation version delivered |
| 2025-01-25 | v001 design complete: 3 themes, 10 features designed |
| 2025-01-25 | EXP-001, EXP-002 complete: Investigations for v001 prerequisites |
| 2025-01-25 | Initial plan created: Project bootstrap, mapping Phase 1-2 milestones to versions |

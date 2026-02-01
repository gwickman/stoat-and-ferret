# Project Backlog

*Last updated: 2026-02-01 18:17*

**Total completed:** 9 | **Cancelled:** 0

## Priority Summary

| Priority | Name | Count |
|----------|------|-------|
| P0 | Critical | 0 |
| P1 | High | 0 |
| P2 | Medium | 4 |
| P3 | Low | 4 |

## Quick Reference

| ID | Pri | Size | Title | Description |
|----|-----|------|-------|-------------|
| <a id="bl-003-ref"></a>[BL-003](#bl-003) | P2 | m | EXP-003: FastAPI static file serving for GUI | Investigate serving the React/Svelte GUI from FastAPI: |
| <a id="bl-009-ref"></a>[BL-009](#bl-009) | P2 | m | Add property test guidance to feature design template | v001 retrospective suggested writing proptest invariants ... |
| <a id="bl-014-ref"></a>[BL-014](#bl-014) | P2 | s | Add Docker-based local testing option | v002 retrospective identified that Windows Application Co... |
| <a id="bl-018-ref"></a>[BL-018](#bl-018) | P2 | s | Create C4 architecture documentation | No C4 architecture documentation currently exists for the... |
| <a id="bl-010-ref"></a>[BL-010](#bl-010) | P3 | m | Configure Rust code coverage with llvm-cov | v001 retrospective noted Rust code coverage is not tracke... |
| <a id="bl-011-ref"></a>[BL-011](#bl-011) | P3 | m | Consolidate Python/Rust build backends | v001 uses hatchling for Python package management and mat... |
| <a id="bl-012-ref"></a>[BL-012](#bl-012) | P3 | m | Fix coverage reporting gaps for ImportError fallback | v001 retrospective noted ImportError fallback code is exc... |
| <a id="bl-016-ref"></a>[BL-016](#bl-016) | P3 | s | Unify InMemory vs FTS5 search behavior | v002 retrospective noted that InMemoryVideoRepository use... |

## Tags Summary

| Tag | Count | Items |
|-----|-------|-------|
| testing | 4 | BL-009, BL-010, BL-012, BL-016 |
| process | 2 | BL-009, BL-014 |
| coverage | 2 | BL-010, BL-012 |
| tooling | 2 | BL-011, BL-014 |
| cleanup | 2 | BL-012, BL-016 |
| investigation | 1 | BL-003 |
| v005-prerequisite | 1 | BL-003 |
| gui | 1 | BL-003 |
| fastapi | 1 | BL-003 |
| proptest | 1 | BL-009 |
| rust | 1 | BL-010 |
| ci | 1 | BL-010 |
| build | 1 | BL-011 |
| complexity | 1 | BL-011 |
| docker | 1 | BL-014 |
| developer-experience | 1 | BL-014 |
| database | 1 | BL-016 |
| consistency | 1 | BL-016 |
| documentation | 1 | BL-018 |
| architecture | 1 | BL-018 |
| c4 | 1 | BL-018 |

## Item Details

### P2: Medium

#### 📋 BL-003: EXP-003: FastAPI static file serving for GUI

**Status:** open
**Tags:** investigation, v005-prerequisite, gui, fastapi

Investigate serving the React/Svelte GUI from FastAPI:

- How do we configure FastAPI to serve static files from Vite build output?
- What's the development workflow — proxy setup for hot reload?
- How do we handle the /gui/* route mounting?
- What about index.html fallback for SPA routing?

This informs v005 (GUI shell).

**Use Case:** This feature addresses: EXP-003: FastAPI static file serving for GUI. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] FastAPI StaticFiles mount configuration documented
- [ ] Vite build output integration explained
- [ ] Development workflow (hot reload) documented
- [ ] Production deployment pattern shown

[↑ Back to list](#bl-003-ref)

#### 📋 BL-009: Add property test guidance to feature design template

**Status:** open
**Tags:** process, testing, proptest

v001 retrospective suggested writing proptest invariants before implementation as executable specifications. Add guidance to feature design templates encouraging this pattern, along with tracking expected test counts.

**Use Case:** This feature addresses: Add property test guidance to feature design template. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Feature design template includes property test section
- [ ] Guidance on writing proptest invariants before implementation
- [ ] Example showing invariant-first design approach
- [ ] Documentation on expected test count tracking

[↑ Back to list](#bl-009-ref)

#### 📋 BL-014: Add Docker-based local testing option

**Status:** open
**Tags:** tooling, docker, process, developer-experience

v002 retrospective identified that Windows Application Control policies can block local Python testing. A Docker-based option would bypass these restrictions and provide consistent dev environments.

**Use Case:** This feature addresses: Add Docker-based local testing option. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] docker-compose.yml with Python + Rust build environment
- [ ] README documents Docker-based testing workflow
- [ ] Tests can run inside container bypassing host restrictions

[↑ Back to list](#bl-014-ref)

#### 📋 BL-018: Create C4 architecture documentation

**Status:** open
**Tags:** documentation, architecture, c4

No C4 architecture documentation currently exists for the project. Establish documentation at appropriate levels (Context, Container, Component, Code) to document the system architecture.

**Use Case:** This feature addresses: Create C4 architecture documentation. It improves the system by resolving the described requirement.

[↑ Back to list](#bl-018-ref)

### P3: Low

#### 📋 BL-010: Configure Rust code coverage with llvm-cov

**Status:** open
**Tags:** testing, coverage, rust, ci

v001 retrospective noted Rust code coverage is not tracked. Configure llvm-cov to measure and report Rust test coverage alongside Python coverage.

**Use Case:** This feature addresses: Configure Rust code coverage with llvm-cov. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] llvm-cov configured for Rust workspace
- [ ] Coverage reports generated during CI
- [ ] Coverage threshold enforced (e.g., 80%)
- [ ] Coverage visible in CI artifacts or dashboard

[↑ Back to list](#bl-010-ref)

#### 📋 BL-011: Consolidate Python/Rust build backends

**Status:** open
**Tags:** tooling, build, complexity

v001 uses hatchling for Python package management and maturin for Rust/PyO3 builds. This dual-backend approach adds complexity. Evaluate whether the build system can be simplified.

**Use Case:** This feature addresses: Consolidate Python/Rust build backends. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Evaluate if hatchling + maturin can be unified
- [ ] Document build system architecture and rationale
- [ ] Simplify if possible without breaking functionality
- [ ] Update developer documentation

[↑ Back to list](#bl-011-ref)

#### 📋 BL-012: Fix coverage reporting gaps for ImportError fallback

**Status:** open
**Tags:** testing, coverage, cleanup

v001 retrospective noted ImportError fallback code is excluded from coverage. Review all coverage exclusions and ensure they are intentional and documented.

**Use Case:** This feature addresses: Fix coverage reporting gaps for ImportError fallback. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] Identify all coverage exclusions in Python code
- [ ] Remove or justify each exclusion
- [ ] ImportError fallback properly tested or documented as intentional exclusion
- [ ] Coverage threshold maintained

[↑ Back to list](#bl-012-ref)

#### 📋 BL-016: Unify InMemory vs FTS5 search behavior

**Status:** open
**Tags:** database, cleanup, testing, consistency

v002 retrospective noted that InMemoryVideoRepository uses substring match while SQLiteVideoRepository uses FTS5 full-text search. Consider unifying search behavior for consistent testing.

**Use Case:** This feature addresses: Unify InMemory vs FTS5 search behavior. It improves the system by resolving the described requirement.

**Acceptance Criteria:**
- [ ] InMemoryVideoRepository uses same search semantics as SQLite FTS5
- [ ] Tests verify consistent behavior across implementations
- [ ] Documentation explains search behavior

[↑ Back to list](#bl-016-ref)

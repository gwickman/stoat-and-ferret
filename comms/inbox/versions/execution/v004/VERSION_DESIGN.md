# v004 Version Design

## Overview

**Version:** v004
**Title:** Testing Infrastructure & Quality Verification
**Themes:** 5

## Backlog Items

- [BL-020](docs/auto-dev/BACKLOG.md#bl-020)
- [BL-021](docs/auto-dev/BACKLOG.md#bl-021)
- [BL-022](docs/auto-dev/BACKLOG.md#bl-022)
- [BL-023](docs/auto-dev/BACKLOG.md#bl-023)
- [BL-024](docs/auto-dev/BACKLOG.md#bl-024)
- [BL-025](docs/auto-dev/BACKLOG.md#bl-025)
- [BL-026](docs/auto-dev/BACKLOG.md#bl-026)
- [BL-027](docs/auto-dev/BACKLOG.md#bl-027)
- [BL-009](docs/auto-dev/BACKLOG.md#bl-009)
- [BL-010](docs/auto-dev/BACKLOG.md#bl-010)
- [BL-012](docs/auto-dev/BACKLOG.md#bl-012)
- [BL-014](docs/auto-dev/BACKLOG.md#bl-014)
- [BL-016](docs/auto-dev/BACKLOG.md#bl-016)

## Design Context

### Rationale

v004 builds comprehensive testing and quality verification infrastructure covering black box testing, recording test doubles, contract tests, and quality verification suite (milestones M1.8–M1.9). This is a prerequisite for v005 (black box tests validate GUI backend).

### Constraints

- v003 baseline: 395 tests, 93% Python coverage, no Rust coverage tracked
- Python 80% coverage minimum, Rust 90% target per AGENTS.md
- BL-020→BL-021→BL-022→BL-023 strict dependency chain
- BL-027 async scan is an API breaking change (pre-v1.0, no external consumers)
- Windows Application Control policies may block local Python testing (BL-014 Docker workaround)

### Assumptions

- No external consumers of scan endpoint — breaking change is safe
- Domain objects are flat scalar dataclasses — deepcopy overhead is negligible
- FTS5 features beyond prefix match (AND/OR/NOT/NEAR/ranking) not used by app
- Rust coverage baseline likely 75-90% based on ~160 existing tests

## Themes

| # | Theme | Goal | Features |
|---|-------|------|----------|
| 1 | 01-test-foundation | Establish core testing infrastructure — test doubles, dependency injection, and fixture factories | 3 |
| 2 | 02-blackbox-contract | Implement end-to-end black box tests, verified fakes for FFmpeg executors, and unified search behavior | 3 |
| 3 | 03-async-scan | Replace synchronous blocking scan with async job queue pattern | 3 |
| 4 | 04-security-performance | Complete M1.9 quality verification — security audit and performance benchmarks | 2 |
| 5 | 05-devex-coverage | Improve developer tooling, testing processes, and coverage infrastructure | 4 |

## Success Criteria

Version is complete when:

- [ ] Theme 01 (test-foundation): Establish core testing infrastructure — test doubles, dependency injection, and fixture factories
- [ ] Theme 02 (blackbox-contract): Implement end-to-end black box tests, verified fakes for FFmpeg executors, and unified search behavior
- [ ] Theme 03 (async-scan): Replace synchronous blocking scan with async job queue pattern
- [ ] Theme 04 (security-performance): Complete M1.9 quality verification — security audit and performance benchmarks
- [ ] Theme 05 (devex-coverage): Improve developer tooling, testing processes, and coverage infrastructure

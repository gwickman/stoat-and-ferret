# RCA: Missing .env.example File

## Summary

The stoat-and-ferret project was delivered through 9 versions without a `.env.example` file despite design documents explicitly specifying environment variable configuration via pydantic-settings with `.env` file support. The root cause is a **systematic blind spot in the design-to-implementation pipeline**: design docs defined the configuration architecture but never included a deliverable for documenting that configuration to developers. No retrospective across 9 versions ever flagged this gap.

## Key Findings

### 1. Configuration Was Well-Designed but Never Documented for Consumers

The design docs (`02-architecture.md`, `04-technical-stack.md`, `07-quality-architecture.md`) all contain identical `Settings(BaseSettings)` class definitions specifying 11 environment variables with `STOAT_` prefix, `.env` file support, and sensible defaults. The architecture was sound. What was missing was the operational artifact (`.env.example`) that translates this design into developer guidance.

### 2. Timeline of Environment Variable Introduction

| Version | What Happened | .env.example? |
|---------|--------------|---------------|
| v001 | Rust/PyO3 foundation -- no config layer | N/A |
| v002 | Database + FFmpeg execution added | No |
| **v003** | **pydantic-settings introduced** (`AppSettings` with `@lru_cache`) | **No** |
| v004-v007 | Settings fields added incrementally; some never wired | No |
| **v008** | All 9 settings finally wired to consumers (BL-056, BL-062) | **No** |
| v009 | Observability + GUI fixes | No |

### 3. Retrospectives Never Flagged It

Across 9 version retrospectives, 9+ theme retrospectives, and 6 retrospective-insights documents, there is **zero mention** of `.env.example`, developer configuration documentation, or onboarding setup guides. The closest references:
- v002 retrospective: "Document CI dependencies centrally" (CI-focused, not developer config)
- v008 retrospective: "Settings consumption lint" (code-level verification, not documentation)

### 4. Root Cause: Never Considered as a Deliverable

**Evidence supports "never considered" rather than "deferred" or "lost track of."**

- No backlog item for `.env.example` existed until BL-071 was created on 2026-02-23 (today, after the issue was identified externally).
- No version design document includes `.env.example` in its deliverables or acceptance criteria.
- No retrospective-insights document flags it as deferred debt.
- The design-to-execution pipeline treats configuration as an *implementation concern* (Settings class, env prefix, validation rules) but not as a *developer experience concern* (what do I set to get started?).

### 5. Already-Addressed Gaps

- **BL-056** (completed v008): Structured logging wired -- `STOAT_LOG_LEVEL` now functional
- **BL-062** (completed v008): Orphaned settings wired -- `STOAT_DEBUG`, `STOAT_WS_HEARTBEAT_INTERVAL` now functional
- **BL-071** (open, P2): Add `.env.example` file -- created today, unassigned to any version

## Current State

The `Settings` class in `src/stoat_ferret/api/settings.py` defines 11 environment variables, all with `STOAT_` prefix, all with sensible defaults, all validated via Pydantic. A developer can run the application with zero configuration. But a developer who *wants* to configure it must read `settings.py` source code to discover available options.

## Recommendations

See [recommendations.md](./recommendations.md) for specific process and tooling changes.

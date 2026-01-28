# Theme 04: clip-model

## Overview

Introduce clip and project data models using Rust timeline math, with basic API endpoints. This theme establishes the editing data model.

## Context

Roadmap milestone M1.7 specifies:
- Design clip data model (source, in/out points, metadata)
- Use Rust timeline math for all calculations
- Build `/clips` API endpoints

Explorations completed:
- `fastapi-testing-patterns`: API testing patterns
- `aiosqlite-migration`: Repository patterns

## Architecture Decisions

### AD-001: Minimal Project Model
Project includes only essential fields for v003:
- id, name, output settings (width, height, fps)
- Full project features (versions, export) deferred to v004+

### AD-002: Clip Wraps Rust
Python Clip model delegates validation to Rust Clip type.

### AD-003: Timeline Position in Frames
All timeline positions stored in frames (integers) for precision.

## Dependencies
- Theme 2 (FastAPI app)
- Theme 3 (videos as clip sources)
- v001 Rust Clip type

## Execution Order
Sequential: 1 → 2 → 3 → 4

## Evidence Sources

| Claim | Source |
|-------|--------|
| Rust Clip type validation | v001 Rust crate `stoat_ferret_core::Clip` |
| Repository pattern (async) | `comms/outbox/exploration/aiosqlite-migration/async-repository-pattern.md` |
| TestClient dependency override | `comms/outbox/exploration/fastapi-testing-patterns/dependency-injection.md` |
| pytest-asyncio fixture patterns | `comms/outbox/exploration/fastapi-testing-patterns/pytest-config.md` |

## Success Criteria
- Project CRUD via API
- Clip CRUD via API
- Clip validation uses Rust core
- Clips reference videos in library
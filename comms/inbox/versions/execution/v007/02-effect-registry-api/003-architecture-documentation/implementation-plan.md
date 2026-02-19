# Implementation Plan: architecture-documentation

## Overview

Update docs/design/02-architecture.md and 05-api-specification.md to reflect the registry refactoring, new audio/transition Rust modules, new endpoints, and effect type additions from T02-F001 and T02-F002. This is a documentation-only feature with no code changes.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `docs/design/02-architecture.md` | Update Rust modules, Effects Service, PyO3 bindings, registered effects, metrics |
| Modify | `docs/design/05-api-specification.md` | Update POST /effects/transition, effect discovery response |

## Test Files

(none — documentation feature)

## Implementation Stages

### Stage 1: Update 02-architecture.md

1. Add `audio.rs` and `transitions.rs` to the Rust module listing
2. Rewrite Effects Service section to describe registry-based dispatch pattern
3. Update PyO3 bindings section with new audio/transition builder classes
4. Update registered effects list (all 9+ effect types)
5. Add `stoat_ferret_effect_applications_total` Prometheus counter to metrics section

**Verification:**
```bash
# Manual review — ensure all sections reflect implemented code
```

### Stage 2: Update 05-api-specification.md

1. Document POST /effects/transition endpoint with request/response schemas
2. Update GET /effects discovery response with new effect types
3. Document registry dispatch pattern

**Verification:**
```bash
# Manual review — ensure endpoint documentation matches implementation
```

## Test Infrastructure Updates

None.

## Quality Gates

```bash
# Documentation quality — no broken markdown, accurate content
uv run ruff check src/ tests/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Documentation may drift from implementation — review against actual code. See `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`

## Commit Message

```
docs: update architecture and API specification for registry refactoring and new effects
```
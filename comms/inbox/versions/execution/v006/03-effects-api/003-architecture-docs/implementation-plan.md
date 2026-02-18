# Implementation Plan: architecture-docs

## Overview

Update the architecture documentation to reflect all v006 changes: new Rust modules (expression, drawtext, speed), filter graph validation/composition extensions, Effects Service with registry and discovery, clip model extension, and updated PyO3 bindings. Also reconcile the roadmap milestones.

## Files to Create/Modify

| File | Action | Purpose |
|------|--------|--------|
| `docs/design/02-architecture.md` | Modify | Add new Rust modules, Effects Service, clip model extension, PyO3 bindings |
| `docs/design/01-roadmap.md` | Modify | Check off M2.1-M2.3 items (Impact #7) |

## Test Files

(none — documentation-only feature)

## Implementation Stages

### Stage 1: Architecture Document Update

1. Update Rust module structure section in `docs/design/02-architecture.md`:
   - Add `expression.rs` — FFmpeg filter expression engine
   - Add `drawtext.rs` — drawtext filter builder
   - Add `speed.rs` — speed control filter builders
   - Document validation and composition additions to `filter.rs`
2. Update Effects Service section:
   - Replace placeholder with actual `EffectRegistry` pattern
   - Document `GET /effects` discovery endpoint
   - Document POST clip effect application endpoint
3. Update data model section:
   - Document `effects_json` field on clips table
   - Document JSON serialization pattern
4. Update PyO3 bindings section:
   - Add expression types
   - Add drawtext builder
   - Add speed control
   - Add validate/validated_to_string methods

**Verification:**
Manual review — ensure all new modules, endpoints, and model changes are documented.

### Stage 2: Roadmap Milestone Updates

1. Update `docs/design/01-roadmap.md` to check off M2.1 (Filter Expression Engine), M2.2 (Text Overlay), M2.3 (Speed Control)

**Verification:**
Manual review — ensure milestones match actual implementation.

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Documentation accuracy — mitigated by running this feature last (after all implementation is final).

## Commit Message

```
docs: update architecture and roadmap for v006 effects engine

Impact #2: Updated 02-architecture.md with new Rust modules, Effects
Service, clip model extension. Checked off M2.1-M2.3 in roadmap.
```
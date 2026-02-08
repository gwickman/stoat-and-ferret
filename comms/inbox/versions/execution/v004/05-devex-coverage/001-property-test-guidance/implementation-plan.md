# Implementation Plan — property-test-guidance

## Overview

Add property test guidance to feature design templates and add `hypothesis` as a dev dependency.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|--------|
| Modify | `pyproject.toml` | Add `hypothesis` to dev dependencies |
| Modify | `docs/auto-dev/TEMPLATES/` or equivalent template files | Add property test section |
| Create | `tests/examples/test_property_example.py` | Example property tests demonstrating invariant-first approach |

## Implementation Stages

### Stage 1: Add Hypothesis Dependency
Add `hypothesis` with version pin to dev dependencies in `pyproject.toml`. Run `uv sync` to verify.

### Stage 2: Template Update
Add "Property Tests" section to feature design template with guidance:
- Identify properties/invariants before writing implementations
- Use `@given` for pure functions, `RuleBasedStateMachine` for stateful systems
- Include expected test count

### Stage 3: Example Property Tests
Create example tests demonstrating the invariant-first approach with stoat-and-ferret domain objects:
- Timeline math round-trip: `Position + Duration - Duration == Position`
- Filter escaping idempotency
- Repository add/get round-trip

## Quality Gates

- `hypothesis` installable via `uv sync`
- Example property tests pass
- Template updated with property test section
- `uv run ruff check tests/` passes

## Risks

| Risk | Mitigation |
|------|------------|
| R8: Hypothesis dependency | Dev dependency only; version pin prevents breaking changes |

## Commit Message

```
feat: add property test guidance and Hypothesis dependency
```
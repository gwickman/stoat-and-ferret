# Implementation Plan: transition-api-endpoint

## Overview

Create POST /effects/transition endpoint for applying transitions between adjacent clips. Validates clip adjacency in the project timeline, uses registry dispatch for filter string generation, and stores the transition persistently. Follows the existing effects router patterns.

## Files to Create/Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `src/stoat_ferret/api/routers/effects.py` | Add POST /effects/transition endpoint with adjacency validation |
| Modify | `src/stoat_ferret/api/schemas/effect.py` | Add TransitionRequest, TransitionResponse Pydantic models |
| Modify | `src/stoat_ferret/db/models.py` | Add transition storage to project/clip model if needed |
| Modify | `src/stoat_ferret/db/clip_repository.py` | Add transition persistence methods if needed |
| Modify | `tests/test_api/test_effects.py` | Add transition endpoint tests |

## Test Files

`tests/test_api/test_effects.py`

## Implementation Stages

### Stage 1: Schema models

1. Add `TransitionRequest` Pydantic model: source_clip_id, target_clip_id, transition_type, parameters
2. Add `TransitionResponse` Pydantic model: transition_type, parameters, filter_string, source_clip_id, target_clip_id
3. Add contract tests for schema round-trip

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "transition and schema"
```

### Stage 2: Clip adjacency validation

1. Implement adjacency check: verify source and target clips are adjacent in timeline
2. Handle edge cases: non-existent clips (404), same clip (400), non-adjacent (400), empty timeline (400)
3. Add unit tests for adjacency validation

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "adjacency"
```

### Stage 3: Endpoint implementation

1. Add `POST /effects/transition` route in effects router
2. Validate request via registry JSON schema
3. Generate filter string via registry dispatch (definition.build_fn)
4. Store transition in project model
5. Return TransitionResponse with filter string

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "transition"
```

### Stage 4: Black-box test

1. Add full-flow test: create project, add adjacent clips, apply transition, verify response
2. Verify filter string in response matches expected xfade output
3. Verify persistent storage (retrieve and check)

**Verification:**
```bash
uv run pytest tests/test_api/test_effects.py -v -k "transition and black_box"
```

## Test Infrastructure Updates

- Extend `tests/test_api/test_effects.py` with transition endpoint tests
- May need test factory helpers for creating adjacent clips

## Quality Gates

```bash
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run pytest tests/ --cov=src --cov-fail-under=80
```

## Risks

- Clip adjacency logic depends on timeline model — may need investigation. See `comms/outbox/versions/design/v007/006-critical-thinking/risk-assessment.md`
- Transition storage format — decide whether to extend effects_json or add separate transitions_json field

## Commit Message

```
feat: add POST /effects/transition endpoint with clip adjacency validation
```
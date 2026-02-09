# Implementation Planning Process

## Purpose

Create a detailed implementation plan with stages and verification points.

## Inputs

- REQUIREMENTS.md - What needs to be built
- Codebase analysis - Current architecture
- LEARNINGS.md - Past lessons

## Process

### 1. Analyze Architecture Impact

Determine:
- Which components are affected
- What new components needed
- Integration points

### 2. Define Stages

Break implementation into stages:
- Each stage is independently verifiable
- Stages build on each other
- Natural commit points

### 3. Detail Tasks

For each stage:
- Specific tasks to complete
- Files to create/modify
- Tests to write

### 4. Plan Verification

For each stage define:
- Commands to run
- Expected outcomes
- Rollback approach

### 5. Identify Risks

Document risks and mitigations:
- Technical risks
- Integration risks
- Timeline risks

## Document Template

```markdown
# Version {version} Implementation Plan

## Overview
{Brief description}

## Architecture Changes
{What's changing}

## Stages

### Stage 0: {Name}
**Objective:** {Goal}
**Tasks:**
1. {Task}
**Verification:**
```bash
{command}
```
**Commit:** `{message}`

## Testing Strategy
{Approach}

### Property Tests
If the requirements define property test invariants (PT-xxx), implement them
using Hypothesis with `@given` strategies. Mark with `@pytest.mark.property`.

Use `@given` for pure functions and `RuleBasedStateMachine` for stateful systems.
See `tests/examples/test_property_example.py` for patterns.

## Risks
| Risk | Impact | Mitigation |
|------|--------|------------|
| {Risk} | {Level} | {Strategy} |
```

## Outputs

- `v{version}/IMPLEMENTATION_PLAN.md` created
- Clear stages with verification

## Next Step

[04-STARTER-PROMPT.md](./04-STARTER-PROMPT.md) - Generate executable prompt

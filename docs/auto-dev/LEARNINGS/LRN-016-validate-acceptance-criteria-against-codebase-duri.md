## Context

Feature requirements are typically written during design phase before implementation begins. If requirements reference domain models, APIs, or capabilities that don't yet exist, the implementing developer discovers unachievable criteria only during execution.

## Learning

Validate acceptance criteria against the actual codebase during design, not execution. Check that referenced domain models, APIs, dependencies, and capabilities exist before finalizing requirements. Mark criteria that depend on unimplemented prerequisites as explicitly deferred with a stated dependency.

## Evidence

- v004 Theme 01 Feature 003 (fixture-factory): FR-3 (`with_text_overlay()`) was unachievable because the TextOverlay domain model didn't exist. This was only discovered during implementation.
- The version retrospective elevated this to a top-level process improvement recommendation.
- Both the theme and version retrospectives recommended design-time validation.

## Application

- During design review, grep the codebase for referenced types/APIs/models.
- For each acceptance criterion, verify the preconditions are met.
- Mark unachievable criteria as "Deferred: depends on [specific prerequisite]" rather than including them as pass/fail.
- This prevents wasted implementation effort and confusing completion reports with N/A criteria.
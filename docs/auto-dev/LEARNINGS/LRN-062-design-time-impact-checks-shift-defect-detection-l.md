## Context

Recurring issue patterns (async safety violations, missing settings documentation, cross-version wiring gaps, GUI input mechanism mismatches) can be detected during version design rather than during implementation or code review.

## Learning

Codifying recurring issue patterns into a reusable impact assessment document with structured checks (trigger condition, what to check, action required) shifts defect detection from implementation to design phase. These checks act as institutional memory that persists across agent sessions and version boundaries.

## Evidence

v011 Feature 003 (impact-assessment) created `IMPACT_ASSESSMENT.md` with 4 design-time checks derived from patterns observed in prior versions: async safety, settings documentation completeness, cross-version wiring, and GUI input mechanisms. Each check uses a consistent three-section structure (trigger, check, action) consumed during version design Task 003.

## Application

After each version retrospective, review new failure patterns and add them as design-time checks in `IMPACT_ASSESSMENT.md`. Reference this document during version design to catch known patterns before they reach implementation. Keep checks general enough to apply across versions but specific enough to be actionable.
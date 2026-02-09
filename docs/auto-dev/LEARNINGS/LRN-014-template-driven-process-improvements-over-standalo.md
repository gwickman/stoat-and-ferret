## Context

Process improvements (like adopting property testing or adding quality checklists) can be documented as standalone guides, but adoption depends on developers discovering and following them.

## Learning

Embed process improvements directly into the templates that developers already use (requirements templates, implementation plan templates, design documents) rather than writing standalone documentation. This ensures the improvement becomes part of the standard workflow without relying on developers finding separate docs.

## Evidence

- v004 Theme 05 Feature 001 (property-test-guidance): Property test guidance was embedded into `02-REQUIREMENTS.md` and `03-IMPLEMENTATION-PLAN.md` templates with a concrete ID format (PT-xxx) and expected test count tracking.
- The version retrospective called this out as a cross-theme process improvement.
- Contrast with standalone documentation that can be easily overlooked.

## Application

- When introducing a new practice, modify the templates/checklists that people already follow.
- Include concrete formats (ID schemes, section headings) so the practice is actionable, not aspirational.
- This applies to any workflow improvement: code review checklists, security considerations, performance budgets.
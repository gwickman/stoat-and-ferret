# Requirements: dynamic-parameter-forms

## Goal

Build schema-driven form generator supporting number/range, string, enum, boolean, and color picker inputs with validation.

## Background

Backlog Item: BL-049

M2.8 specifies auto-generating parameter forms from JSON schema. Each effect has a unique parameter schema (from the registry), and building static forms per effect doesn't scale. A schema-driven form generator renders the correct input widgets dynamically. A custom lightweight generator is used (not RJSF) given the limited parameter type set of 5-6 types.

## Functional Requirements

**FR-001**: Forms generated dynamically from effect JSON schema definitions
- AC: Given a JSON schema object, the form generator renders appropriate input fields
- AC: Each schema property becomes a labeled form field
- AC: Field ordering follows schema property order

**FR-002**: Supports parameter types: number (with range slider), string, enum (dropdown), boolean, color picker
- AC: `type: "number"` with `minimum`/`maximum` renders a range slider with numeric input
- AC: `type: "string"` renders a text input
- AC: `type: "string"` with `enum` array renders a dropdown select
- AC: `type: "boolean"` renders a checkbox/toggle
- AC: `format: "color"` renders a color picker input

**FR-003**: Inline validation displays error messages from Rust validation
- AC: Backend validation errors displayed inline next to the relevant field
- AC: Client-side schema constraint violations shown immediately (e.g., out of range)
- AC: Error messages are descriptive and actionable

**FR-004**: Live filter string preview updates as parameter values change
- AC: Parameter value changes propagate to the preview component (BL-050)
- AC: Form state stored in effectFormStore for cross-component access

**FR-005**: Default values pre-populated from the JSON schema
- AC: Schema `default` values populate form fields on initial render
- AC: Fields without defaults show placeholder text or empty state

## Non-Functional Requirements

**NFR-001**: Form renders within 100ms of effect selection
- Metric: No perceptible lag between effect selection and form display

**NFR-002**: All form inputs have accessible labels
- Metric: axe-core accessibility scan passes for form components

## Out of Scope

- Nested object schemas
- Array/list parameter types
- Conditional schema fields (if/then/else)
- Schema-based field dependencies

## Test Requirements

- ~5 Vitest tests: Form generator renders correct input type per schema property type
- ~1 Vitest test: Range slider respects min/max from schema
- ~1 Vitest test: Enum dropdown populates from schema enum values
- ~1 Vitest test: Default values pre-populated
- ~2 Vitest tests: Validation error display
- ~2 Vitest tests: effectFormStore parameter and validation state
- ~1 Vitest test: onChange handlers propagate to store

See `comms/outbox/versions/design/v007/005-logical-design/test-strategy.md` for full test breakdown.

## Reference

See `comms/outbox/versions/design/v007/004-research/` for supporting evidence:
- `external-research.md`: RJSF widget mapping (used as design reference), custom generator approach
- `codebase-patterns.md`: Zustand store pattern
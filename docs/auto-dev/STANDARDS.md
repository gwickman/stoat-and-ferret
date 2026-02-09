# Development Standards

## Overview

This document defines development standards for the project.

## Code Style

### General
- Use consistent formatting (configured via tooling)
- Write self-documenting code
- Keep functions small and focused

### Naming Conventions
- Use descriptive names
- Follow language conventions
- Be consistent across codebase

## Testing

### Unit Tests
- Test one behavior per test
- Use descriptive test names
- Mock only external boundaries

### Property Tests
- Use Hypothesis for property-based testing (`@pytest.mark.property`)
- Identify invariants before implementation (invariant-first design)
- Use `@given` for pure functions, `RuleBasedStateMachine` for stateful systems
- See `tests/examples/test_property_example.py` for patterns

### Coverage
- Maintain minimum coverage threshold
- Focus on critical paths

## Documentation

### Code Comments
- Explain why, not what
- Document public APIs
- Keep comments updated

### Commit Messages
- Use conventional commits
- Reference issues when applicable
- Keep messages concise but descriptive

## Review Process

### Pull Requests
- Keep PRs focused and small
- Include tests with changes
- Update documentation as needed

### Code Review
- Review for correctness and clarity
- Suggest improvements constructively
- Approve when standards met

---

*Customize this document for your project's specific standards.*

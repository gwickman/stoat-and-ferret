## Context

When planning version themes, features can be grouped by various criteria: functional area, priority, user story, or modification point (the code paths they change).

## Learning

Grouping features that modify the same code path into a single theme reduces context-switching, makes code review straightforward, and increases the likelihood of first-iteration success. The shared context compounds across features — knowledge gained in the first feature directly benefits subsequent features in the theme.

## Evidence

v008 Theme 01 grouped three features (database startup, logging startup, orphaned settings) that all modified `app.py` lifespan. All three passed quality gates on first iteration. The shared modification point meant context from feature 001 (lifespan structure, ordering constraints) was immediately reusable for features 002 and 003.

## Application

During version planning, when multiple features exist that could be grouped different ways:
1. Identify the primary modification point for each feature (which file/function it changes)
2. Group features sharing a modification point into the same theme
3. Order features within the theme so earlier features establish patterns that later features can follow
## Context

Version planning involves choosing between new feature development and maintenance work (wiring, bug fixes, debt resolution). There's a tendency to combine both, but maintenance-focused versions have different success characteristics.

## Learning

Versions scoped to well-understood, maintenance-focused changes (wiring existing code, fixing diagnosed bugs, resolving known debt) achieve significantly higher first-iteration success rates than feature-development versions. The key factor is that the problem and solution are both well-understood before implementation begins — there's no discovery phase. This validates dedicating entire versions to maintenance when the debt inventory is sufficient.

## Evidence

v008 achieved 100% first-iteration success (4/4 features, 0 quality gate failures) across two themes. All changes were "wiring existing code rather than building new features" — database schema creation, logging configuration, orphaned settings, and a previously-diagnosed E2E flake. Compare this to feature-development versions where some features require 2-3 iterations.

## Application

When planning version scope:
1. Don't mix maintenance work into feature-development versions — dedicate versions to maintenance when debt inventory justifies it
2. Maintenance versions benefit from precise problem statements — "wire X to Y" rather than "implement X"
3. Use maintenance versions to resolve P0/P1 blockers before starting the next feature-development cycle
4. Track first-iteration success rates to quantify the scoping benefit
## Context

When removing unused code (dead functions, deprecated API bindings, legacy bridge modules), the primary risk is breaking an unknown caller. This applies to any cleanup task where code is being deleted rather than modified.

## Learning

Before deleting any function, class, or module, grep the entire codebase for production callers. If the grep returns zero matches outside test files and the code being deleted, proceed with confidence. If any callers exist, the removal must be deferred or the callers must be migrated first. This single verification step converts a risky deletion into a safe, mechanical operation.

## Evidence

Three consecutive cleanup features all used this pattern (grepping for production callers before removal). All three completed with 100% acceptance criteria passing, zero test regressions, and clean quality gates. The pattern was cited by both theme-level and version-level retrospectives as the key risk-mitigation step.

## Application

1. Before any code removal PR, run a project-wide search for the function/class name
2. Exclude test files and the file being deleted from the search results
3. If zero production callers exist, proceed with deletion
4. Document the "zero callers" finding in the PR or completion report for reviewer confidence
5. If callers exist, convert the removal into a migration task instead
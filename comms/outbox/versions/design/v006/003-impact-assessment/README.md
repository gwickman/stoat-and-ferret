# 003 - Impact Assessment

v006 impact assessment identified 7 impacts across documentation, type stubs, and AGENTS.md. Zero MCP tool impacts — all auto-dev tools are project-agnostic and unaffected by application code changes. Classification: 5 small (sub-task scope), 1 substantial (feature scope), 1 cross-version (backlog scope). No project-specific impact checks configured (IMPACT_ASSESSMENT.md does not exist).

## Generic Impacts

### tool_help Currency: 0 impacts

All MCP tools examined (run_quality_gates, design_theme, generate_completion_report, explore_project, start_completion_report, git_write, git_read) are auto-dev infrastructure tools. Their parameters, behavior, and help text are project-agnostic and will not be affected by v006's application-level changes (new Rust modules, new API endpoints, data model extensions).

### Tool Description Accuracy: 0 impacts

Same reasoning as above. No MCP tool descriptions reference project-specific constructs like filter expressions, effects APIs, or the clip data model.

### Documentation Review: 7 impacts

v006 introduces significant new Rust modules (expression engine, graph validation, composition, drawtext, speed builders), new API endpoints (/effects discovery, clip effect application), and a clip model extension. Several design documents and project files reference these areas and will need updates.

See `impact-table.md` for the full inventory and `impact-summary.md` for classification breakdown.

## Project-Specific Impacts

N/A — no `docs/auto-dev/IMPACT_ASSESSMENT.md` configured for this project.

## Work Items Generated

| Classification | Count |
|----------------|-------|
| Small (sub-task) | 5 |
| Substantial (feature) | 1 |
| Cross-version (backlog) | 1 |
| **Total** | **7** |

## Recommendations

1. **Small impacts** (5): Attach as sub-tasks to the features that cause them. AGENTS.md update for Rust module listing should go with the first Rust theme. Type stub regeneration goes with each Rust feature per AGENTS.md workflow. PLAN.md status update and investigation closure should go with the final theme.

2. **Substantial impact** (1): The 02-architecture.md update (new Rust modules, Effects Service details, expanded data model) requires its own feature within v006. The architecture doc is authoritative and references specific module names, code examples, and data flow diagrams that v006 will materially change.

3. **Cross-version impact** (1): C4 architecture documentation regeneration (already noted as tech debt from v005) is too large for v006. Add to backlog or schedule for post-v006 retrospective.

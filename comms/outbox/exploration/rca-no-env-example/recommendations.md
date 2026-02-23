# Recommendations: Preventing Configuration Documentation Gaps

## Already Addressed

| Item | Status | Version |
|------|--------|---------|
| BL-056: Wire structured logging (`STOAT_LOG_LEVEL`) | Completed | v008 |
| BL-062: Wire orphaned settings (`STOAT_DEBUG`, `STOAT_WS_HEARTBEAT_INTERVAL`) | Completed | v008 |
| BL-071: Add `.env.example` file | Open (P2) | Unassigned |

## Recommendation 1: Create .env.example Alongside Settings Class

**Problem:** Settings were implemented in v003 without a corresponding `.env.example`. Six more versions shipped before this was noticed.

**Recommendation:** When a Settings/configuration class is created or modified, the `.env.example` file should be updated in the same feature. This should be an explicit acceptance criterion in any feature that adds environment variables.

**Applies to:** BL-071 (immediate), future versions adding settings.

## Recommendation 2: Add Developer Onboarding to Version Design Checklists

**Problem:** No VERSION_DESIGN.md across 9 versions included developer setup documentation as a deliverable. The design-to-execution pipeline treats configuration as an implementation concern but not a developer experience concern.

**Recommendation:** Version design documents should include a "Developer Experience" section that asks: "Does this version introduce new external dependencies, configuration options, or setup steps? If so, what documentation updates are needed?"

**Applies to:** auto-dev-mcp design_version and design_theme templates.

## Recommendation 3: Add Retrospective Question for Documentation Gaps

**Problem:** 9 retrospectives examined code quality and wiring but never asked whether new capabilities were documented for developers.

**Recommendation:** Retrospective templates should include: "Were new configuration options, dependencies, or setup steps documented?" This catches gaps before they accumulate across multiple versions.

**Applies to:** auto-dev-mcp retrospective generation.

## Recommendation 4: Settings Consumption and Documentation Lint

**Problem:** v008 retrospective recommended a "settings consumption lint" to verify all Settings fields are consumed by production code. This is good but incomplete -- it checks code wiring but not documentation.

**Recommendation:** Extend the concept to verify that every `Settings` field appears in `.env.example`. This can be a simple test that parses both files and compares field names. Example:

```python
def test_env_example_covers_all_settings():
    """Every Settings field should appear in .env.example."""
    settings_fields = {f.name for f in Settings.model_fields.values()}
    env_example_vars = parse_env_example(".env.example")
    missing = settings_fields - env_example_vars
    assert not missing, f"Settings fields missing from .env.example: {missing}"
```

**Applies to:** stoat-and-ferret test suite (after BL-071 is implemented).

## Recommendation 5: Distinguish "Design Exists" from "Wired and Documented"

**Problem:** The project's core recurring issue -- visible in both the settings wiring gaps (BL-056, BL-062) and the missing `.env.example` -- is that design documents describe desired end-states but the pipeline does not verify that all aspects of that end-state are delivered. Code wiring is verified by tests. Documentation is not verified by anything.

**Recommendation:** Feature acceptance criteria should explicitly distinguish:
1. **Implemented** -- code exists
2. **Wired** -- code is connected to application startup/runtime
3. **Documented** -- developer-facing artifacts updated (`.env.example`, README, AGENTS.md)

This is a generalization of the "deferred wiring" lesson that retrospectives have flagged since v007, extended to documentation.

## Process Gaps in auto-dev-mcp (Already Partially Addressed)

The auto-dev-mcp pipeline has improved since v007:
- **Wiring audits** are now recognized as necessary (learned from v008)
- **quality-gaps.md** generation was flagged as missing across early versions
- **C4 documentation** regeneration is now attempted (though it failed in v009)

The remaining gap is that **developer experience artifacts** (`.env.example`, setup guides, onboarding docs) are not part of the standard deliverable checklist. The pipeline checks code quality (ruff, mypy, pytest) but has no mechanism to check documentation completeness.

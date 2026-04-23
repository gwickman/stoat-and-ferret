"""AI-summary / example-prompt coverage for registered effects (BL-270).

Every effect exposed via ``/api/v1/effects`` must carry a non-empty
``ai_summary`` and ``example_prompt`` so agents can both recognise the
effect and invoke it from a natural-language prompt.
"""

from __future__ import annotations

from stoat_ferret.effects.definitions import create_default_registry


def test_all_effects_have_nonempty_ai_summary() -> None:
    """Every registered effect carries a non-empty ai_summary string."""
    registry = create_default_registry()
    all_effects = registry.list_all()
    assert all_effects, "Expected default registry to contain at least one effect"

    missing = [
        effect_type for effect_type, definition in all_effects if not definition.ai_summary.strip()
    ]
    assert not missing, f"Effects missing ai_summary: {missing}"


def test_all_effects_have_nonempty_example_prompt() -> None:
    """Every registered effect carries a non-empty example_prompt string."""
    registry = create_default_registry()
    all_effects = registry.list_all()
    assert all_effects, "Expected default registry to contain at least one effect"

    missing = [
        effect_type
        for effect_type, definition in all_effects
        if not definition.example_prompt.strip()
    ]
    assert not missing, f"Effects missing example_prompt: {missing}"


def test_registry_has_nine_builtin_effects() -> None:
    """Guards against silent removals from the default registry."""
    registry = create_default_registry()
    assert len(registry.list_all()) == 9

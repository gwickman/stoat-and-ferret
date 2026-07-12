# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

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


REQUIRED_EFFECT_TYPES = {
    # All effect types known at v105; adding new types does not require updating this set.
    # This set catches accidental removals — test fails if any required type is missing.
    "acrossfade",
    "audio_ducking",
    "audio_fade",
    "audio_mix",
    "blur",
    "burned_subtitle",
    "chroma_key",
    "chromatic_aberration",
    "color_key",
    "color_lut",
    "convolution_reverb",
    "curves",
    "deesser",
    "deplosive",
    "framerate_convert",
    "freeze_frame",
    "gradient_generator",
    "hue_rotation",
    "lens_distort",
    "loudness_normalize",
    "mastering_limiter",
    "multiband_compressor",
    "noise_generator",
    "noise_reduction",
    "opacity",
    "pan",
    "parametric_eq",
    "reverse",
    "scale",
    "sharpen",
    "speed_control",
    "subtitle_script",
    "text_overlay",
    "time_stretch",
    "variable_speed",
    "video_fade",
    "vignette",
    "volume",
    "xfade",
    "zoompan",
}


def test_registry_has_builtin_effects() -> None:
    """Guards against silent removals from the default registry."""
    registry = create_default_registry()
    registered_names = {name for name, _ in registry.list_all()}
    missing = REQUIRED_EFFECT_TYPES - registered_names
    assert not missing, f"Required effect types missing from registry: {missing}"


def test_value_kind_per_option_populated_for_migrated_builders() -> None:
    """BL-555-AC-5: blur/opacity/scale EffectDefinitions carry value_kind_per_option."""
    registry = create_default_registry()
    effects = dict(registry.list_all())

    blur = effects["blur"]
    assert blur.value_kind_per_option == {"sigma": "numeric"}, (
        f"blur missing expected value_kind_per_option: {blur.value_kind_per_option}"
    )

    opacity = effects["opacity"]
    assert opacity.value_kind_per_option == {"opacity": "numeric"}, (
        f"opacity missing expected value_kind_per_option: {opacity.value_kind_per_option}"
    )

    scale = effects["scale"]
    assert scale.value_kind_per_option == {"scale": "numeric"}, (
        f"scale missing expected value_kind_per_option: {scale.value_kind_per_option}"
    )


def test_requires_path_escape_implies_path_kind_entry() -> None:
    """Hygiene: every builder with requires_path_escape=True must have a 'path' entry
    in value_kind_per_option (guards against silent escape policy drift)."""
    registry = create_default_registry()
    violations = []
    for effect_type, definition in registry.list_all():
        if definition.requires_path_escape:
            has_path_kind = any(v == "path" for v in definition.value_kind_per_option.values())
            if not has_path_kind:
                violations.append(effect_type)
    assert not violations, (
        f"Effects with requires_path_escape=True but no 'path' value_kind entry: {violations}"
    )

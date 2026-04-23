"""Unit tests for the Rust ``ParameterSchema`` translator (BL-270).

Exercises ``parameter_schemas_from_dict`` against both synthetic inputs and
every effect registered in the default registry, ensuring the translator
handles the real-world effect shapes without dropping any schema keys.
"""

from __future__ import annotations

from typing import Any

from stoat_ferret.effects.definitions import create_default_registry
from stoat_ferret_core import ParameterSchema, parameter_schemas_from_dict

# Keys that the translator understands for a single property entry.
_KNOWN_PROPERTY_KEYS: frozenset[str] = frozenset(
    {"type", "default", "minimum", "maximum", "enum", "description", "items"}
)


def test_empty_schema_returns_empty_list() -> None:
    """An empty schema dict produces no ParameterSchema entries."""
    assert parameter_schemas_from_dict({}, {}) == []


def test_schema_without_properties_returns_empty_list() -> None:
    """A schema missing ``properties`` returns an empty list."""
    assert parameter_schemas_from_dict({"type": "object"}, {}) == []


def test_enum_override_maps_to_enum_param_type() -> None:
    """A property with both ``type: string`` and ``enum`` resolves to ``enum``."""
    schema = {
        "properties": {
            "mode": {"type": "string", "enum": ["a", "b"], "description": "m"},
        },
    }
    result = parameter_schemas_from_dict(schema, {})
    assert len(result) == 1
    assert result[0].param_type == "enum"
    assert result[0].enum_values == ["a", "b"]


def test_array_type_supported() -> None:
    """Array-typed properties resolve to ``param_type='array'``."""
    schema = {"properties": {"weights": {"type": "array"}}}
    result = parameter_schemas_from_dict(schema, {})
    assert len(result) == 1
    assert result[0].param_type == "array"


def test_all_effects_translate_without_error() -> None:
    """The translator handles every registered effect without raising."""
    registry = create_default_registry()
    for _, definition in registry.list_all():
        result = parameter_schemas_from_dict(definition.parameter_schema, definition.ai_hints)
        assert isinstance(result, list)
        for entry in result:
            assert isinstance(entry, ParameterSchema)


def test_all_effect_schema_keys_mapped() -> None:
    """Every key in every effect's parameter_schema properties is known.

    Rejects silent drops: if Rust/Python ever disagrees on the allow-list,
    this test fails and the translator must be updated.
    """
    registry = create_default_registry()
    unknown_keys: dict[str, set[str]] = {}

    for effect_type, definition in registry.list_all():
        schema_any: Any = definition.parameter_schema
        props: dict[str, dict[str, Any]] = schema_any.get("properties", {})
        for prop_name, prop in props.items():
            extra = set(prop.keys()) - _KNOWN_PROPERTY_KEYS
            if extra:
                unknown_keys.setdefault(effect_type, set()).update(
                    f"{prop_name}.{key}" for key in extra
                )

    assert not unknown_keys, (
        f"Found unknown property keys the translator does not handle: {unknown_keys}. "
        "Either add handling in rust/stoat_ferret_core/src/schema.rs "
        "or extend _KNOWN_PROPERTY_KEYS after confirming the key is intentionally ignored."
    )


def test_translator_populates_ai_hint_from_hints_dict() -> None:
    """When an ai_hints entry exists for a param name, it appears on the output."""
    schema = {"properties": {"text": {"type": "string", "description": "d"}}}
    hints = {"text": "AI-facing hint"}
    result = parameter_schemas_from_dict(schema, hints)
    assert len(result) == 1
    assert result[0].ai_hint == "AI-facing hint"


def test_translator_defaults_missing_ai_hint_to_empty_string() -> None:
    """Parameters with no matching ai_hints entry get an empty ai_hint."""
    schema = {"properties": {"opaque": {"type": "string"}}}
    result = parameter_schemas_from_dict(schema, {})
    assert result[0].ai_hint == ""


def test_text_overlay_fontsize_parameter_is_complete() -> None:
    """The text_overlay.fontsize parameter round-trips fields used by smoke tests."""
    registry = create_default_registry()
    text_overlay = next(
        definition
        for effect_type, definition in registry.list_all()
        if effect_type == "text_overlay"
    )

    params = parameter_schemas_from_dict(text_overlay.parameter_schema, text_overlay.ai_hints)
    by_name = {p.name: p for p in params}

    assert "fontsize" in by_name
    fontsize = by_name["fontsize"]
    assert fontsize.param_type == "int"
    assert fontsize.default_value == 48
    assert fontsize.ai_hint != ""

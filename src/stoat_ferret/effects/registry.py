"""Effect registry for discovering available effects."""

from __future__ import annotations

from typing import Any

import jsonschema
import structlog

from stoat_ferret.effects.definitions import EffectDefinition

logger = structlog.get_logger(__name__)


class EffectValidationError:
    """Structured validation error from JSON schema validation.

    Attributes:
        path: JSON path to the invalid field (e.g. "fontsize").
        message: Human-readable error description.
    """

    def __init__(self, path: str, message: str) -> None:
        self.path = path
        self.message = message

    def __repr__(self) -> str:
        return f"EffectValidationError(path={self.path!r}, message={self.message!r})"


class EffectRegistry:
    """Registry of available effects with parameter schemas and AI hints.

    Follows the register_handler() pattern from the job queue (LRN-009).
    Effects are registered by type string and can be listed or retrieved.
    """

    def __init__(self) -> None:
        self._effects: dict[str, EffectDefinition] = {}

    def register(self, effect_type: str, definition: EffectDefinition) -> None:
        """Register an effect definition.

        Args:
            effect_type: Unique identifier for the effect (e.g., "text_overlay").
            definition: The effect definition with schema, hints, and preview.
        """
        self._effects[effect_type] = definition
        logger.info("effect_registered", effect_type=effect_type)

    def get(self, effect_type: str) -> EffectDefinition | None:
        """Get an effect definition by type.

        Args:
            effect_type: The effect type identifier.

        Returns:
            The effect definition, or None if not found.
        """
        return self._effects.get(effect_type)

    def list_all(self) -> list[tuple[str, EffectDefinition]]:
        """List all registered effects.

        Returns:
            List of (effect_type, definition) tuples.
        """
        return list(self._effects.items())

    def validate(self, effect_type: str, parameters: dict[str, Any]) -> list[EffectValidationError]:
        """Validate parameters against the effect's JSON schema.

        Args:
            effect_type: The effect type identifier.
            parameters: The parameters to validate.

        Returns:
            List of validation errors. Empty if valid.

        Raises:
            KeyError: If the effect type is not registered.
        """
        definition = self._effects.get(effect_type)
        if definition is None:
            msg = f"Unknown effect type: {effect_type}"
            raise KeyError(msg)

        schema = definition.parameter_schema
        validator = jsonschema.Draft7Validator(schema)
        errors: list[EffectValidationError] = []
        for error in validator.iter_errors(parameters):
            path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else ""
            errors.append(EffectValidationError(path=path, message=error.message))
        return errors

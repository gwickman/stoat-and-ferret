"""Effect registry for discovering available effects."""

from __future__ import annotations

import structlog

from stoat_ferret.effects.definitions import EffectDefinition

logger = structlog.get_logger(__name__)


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

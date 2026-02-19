"""Effect discovery endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from stoat_ferret.api.schemas.effect import EffectListResponse, EffectResponse
from stoat_ferret.effects.definitions import create_default_registry
from stoat_ferret.effects.registry import EffectRegistry

router = APIRouter(prefix="/api/v1/effects", tags=["effects"])

_default_registry: EffectRegistry | None = None


async def get_effect_registry(request: Request) -> EffectRegistry:
    """Get effect registry from app state.

    Falls back to a default registry if not injected via create_app().

    Args:
        request: The incoming HTTP request.

    Returns:
        The effect registry instance.
    """
    registry: EffectRegistry | None = getattr(request.app.state, "effect_registry", None)
    if registry is not None:
        return registry

    # Fallback: create default registry on first use
    global _default_registry  # noqa: PLW0603
    if _default_registry is None:
        _default_registry = create_default_registry()
    return _default_registry


RegistryDep = Annotated[EffectRegistry, Depends(get_effect_registry)]


@router.get("", response_model=EffectListResponse)
async def list_effects(registry: RegistryDep) -> EffectListResponse:
    """List all available effects with metadata, schemas, and previews.

    Returns:
        List of all registered effects with their parameter schemas,
        AI hints, and filter preview strings.
    """
    effects = []
    for effect_type, definition in registry.list_all():
        effects.append(
            EffectResponse(
                effect_type=effect_type,
                name=definition.name,
                description=definition.description,
                parameter_schema=definition.parameter_schema,
                ai_hints=definition.ai_hints,
                filter_preview=definition.preview_fn(),
            )
        )
    return EffectListResponse(effects=effects, total=len(effects))

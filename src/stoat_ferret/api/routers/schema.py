"""Schema introspection endpoint exposing Pydantic JSON Schema for domain entities (BL-271).

The endpoint lets AI agents discover the request/response shape of the six
primary domain entities — ``project``, ``clip``, ``timeline``, ``render_job``,
``effect``, ``video`` — without having to parse the full OpenAPI document.
Each resource maps to a concrete Pydantic response model; the endpoint returns
that model's ``model_json_schema()`` verbatim. Unknown resources return 404.
"""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from stoat_ferret.api.schemas.clip import ClipResponse
from stoat_ferret.api.schemas.effect import EffectResponse
from stoat_ferret.api.schemas.project import ProjectResponse
from stoat_ferret.api.schemas.render import RenderJobResponse
from stoat_ferret.api.schemas.timeline import TimelineResponse
from stoat_ferret.api.schemas.video import VideoResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["schema"])

_RESOURCE_MODELS: dict[str, type[BaseModel]] = {
    "project": ProjectResponse,
    "clip": ClipResponse,
    "timeline": TimelineResponse,
    "render_job": RenderJobResponse,
    "effect": EffectResponse,
    "video": VideoResponse,
}


@router.get("/schema/{resource}")
async def get_resource_schema(resource: str) -> dict[str, Any]:
    """Return the Pydantic JSON Schema for a domain resource.

    The schema is generated directly from the Pydantic response model's
    ``model_json_schema()`` method — no custom serialization. Pydantic V2
    caches the result after the first call, so repeated lookups are cheap.

    Args:
        resource: One of ``project``, ``clip``, ``timeline``, ``render_job``,
            ``effect``, ``video``. Any other value returns 404.

    Returns:
        The JSON Schema dict for the requested resource.

    Raises:
        HTTPException: 404 when ``resource`` is not a supported name.
    """
    model = _RESOURCE_MODELS.get(resource)
    if model is None:
        logger.info("schema.unknown_resource", resource=resource)
        raise HTTPException(
            status_code=404,
            detail=f"Unknown resource: {resource}",
        )
    return model.model_json_schema()

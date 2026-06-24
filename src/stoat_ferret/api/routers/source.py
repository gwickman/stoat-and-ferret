# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Source-offer endpoint for AGPL §13 compliance (BL-525)."""

from __future__ import annotations

import importlib.metadata

from fastapi import APIRouter
from pydantic import BaseModel

from stoat_ferret.api.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["compliance"])


class SourceResponse(BaseModel):
    """Typed response model for GET /api/v1/source (BL-539)."""

    source_url: str
    version: str
    commit: str
    license: str


@router.get("/source", response_model=SourceResponse)
async def get_source() -> SourceResponse:
    """Return source URL, version, commit, and license for AGPL §13 compliance.

    Returns:
        SourceResponse with source_url, version, commit, and license fields.
    """
    settings = get_settings()
    return SourceResponse(
        source_url=settings.source_url,
        version=importlib.metadata.version("stoat-ferret"),
        commit=settings.build_commit,
        license="AGPL-3.0-or-later",
    )

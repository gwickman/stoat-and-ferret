# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Source-offer endpoint for AGPL §13 compliance (BL-525)."""

from __future__ import annotations

import importlib.metadata

from fastapi import APIRouter

from stoat_ferret.api.settings import get_settings

router = APIRouter(prefix="/api/v1", tags=["compliance"])


@router.get("/source")
async def get_source() -> dict[str, str]:
    """Return source URL, version, commit, and license for AGPL §13 compliance.

    Returns:
        JSON with source_url, version, commit, and license fields.
    """
    settings = get_settings()
    return {
        "source_url": settings.source_url,
        "version": importlib.metadata.version("stoat-ferret"),
        "commit": settings.build_commit,
        "license": "AGPL-3.0-or-later",
    }

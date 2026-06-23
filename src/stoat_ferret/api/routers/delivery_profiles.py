# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Delivery profile CRUD API endpoints.

Provides POST/GET/DELETE for DeliveryProfile lifecycle management.
Profiles bind output formats, loudness targets, and metadata for QC-gated export.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import Response

from stoat_ferret.api.schemas.delivery_profiles import (
    CreateDeliveryProfileRequest,
    DeliveryProfileListResponse,
    DeliveryProfileResponse,
    OutputFormatSpec,
)
from stoat_ferret.db.delivery_profiles_repository import (
    AsyncSQLiteDeliveryProfileRepository,
    DeliveryProfile,
    DeliveryProfileRepository,
)

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["delivery_profiles"])


# ---------- Dependency injection ----------


async def get_delivery_profile_repository(request: Request) -> DeliveryProfileRepository:
    """Get delivery profile repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        DeliveryProfileRepository instance.
    """
    repo: DeliveryProfileRepository | None = getattr(
        request.app.state, "delivery_profile_repository", None
    )
    if repo is not None:
        return repo
    return AsyncSQLiteDeliveryProfileRepository(request.app.state.db)


DeliveryProfileRepoDep = Annotated[
    DeliveryProfileRepository, Depends(get_delivery_profile_repository)
]


# ---------- Helpers ----------


def _profile_to_response(profile: DeliveryProfile) -> DeliveryProfileResponse:
    """Convert a DeliveryProfile domain object to a response model."""
    return DeliveryProfileResponse(
        id=profile.id,
        name=profile.name,
        output_formats=[OutputFormatSpec(**fmt) for fmt in profile.output_formats],
        loudness_target_lufs=profile.loudness_target_lufs,
        true_peak_ceiling_dbtp=profile.true_peak_ceiling_dbtp,
        metadata_template=profile.metadata_template,
        created_at=profile.created_at,
    )


# ---------- Endpoints ----------


@router.post(
    "/delivery_profiles",
    response_model=DeliveryProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_delivery_profile(
    body: CreateDeliveryProfileRequest,
    repo: DeliveryProfileRepoDep,
) -> DeliveryProfileResponse:
    """Create a new delivery profile.

    Args:
        body: Profile creation request.
        repo: Delivery profile repository dependency.

    Returns:
        Created delivery profile with 201 status.

    Raises:
        HTTPException: 409 for duplicate name, 422 for validation errors.
    """
    existing = await repo.get_by_name(body.name)
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "DUPLICATE_PROFILE_NAME",
                "message": f"A delivery profile named '{body.name}' already exists",
            },
        )

    profile = DeliveryProfile(
        id=str(uuid.uuid4()),
        name=body.name,
        output_formats=[fmt.model_dump() for fmt in body.output_formats],
        loudness_target_lufs=body.loudness_target_lufs,
        true_peak_ceiling_dbtp=body.true_peak_ceiling_dbtp,
        metadata_template=body.metadata_template,
        created_at=datetime.now(timezone.utc).isoformat(),
    )
    created = await repo.add(profile)
    logger.info("delivery_profile.created", profile_id=created.id, name=created.name)
    return _profile_to_response(created)


@router.get(
    "/delivery_profiles",
    response_model=DeliveryProfileListResponse,
)
async def list_delivery_profiles(
    repo: DeliveryProfileRepoDep,
) -> DeliveryProfileListResponse:
    """List all delivery profiles.

    Args:
        repo: Delivery profile repository dependency.

    Returns:
        List of all delivery profiles.
    """
    profiles = await repo.list_all()
    return DeliveryProfileListResponse(
        items=[_profile_to_response(p) for p in profiles],
        total=len(profiles),
    )


@router.get(
    "/delivery_profiles/{profile_id}",
    response_model=DeliveryProfileResponse,
)
async def get_delivery_profile(
    profile_id: str,
    repo: DeliveryProfileRepoDep,
) -> DeliveryProfileResponse:
    """Get a delivery profile by UUID.

    Args:
        profile_id: The profile UUID to retrieve.
        repo: Delivery profile repository dependency.

    Returns:
        The delivery profile if found.

    Raises:
        HTTPException: 404 if not found.
    """
    profile = await repo.get_by_id(profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_NOT_FOUND", "message": "Delivery profile not found"},
        )
    return _profile_to_response(profile)


@router.delete(
    "/delivery_profiles/{profile_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_delivery_profile(
    profile_id: str,
    repo: DeliveryProfileRepoDep,
) -> Response:
    """Delete a delivery profile by UUID.

    Args:
        profile_id: The profile UUID to delete.
        repo: Delivery profile repository dependency.

    Returns:
        204 No Content on success.

    Raises:
        HTTPException: 404 if not found.
    """
    deleted = await repo.delete(profile_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PROFILE_NOT_FOUND", "message": "Delivery profile not found"},
        )
    logger.info("delivery_profile.deleted", profile_id=profile_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

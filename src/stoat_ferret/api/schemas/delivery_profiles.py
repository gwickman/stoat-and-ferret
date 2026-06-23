# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Request and response schemas for delivery profile endpoints."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class OutputFormatSpec(BaseModel):
    """A single output format specification within a delivery profile."""

    container: str = Field(..., description="Container format (e.g. mp4, webm, mov)")
    codec: str = Field(..., description="Video codec (e.g. h264, h265, vp9)")
    bitrate_kbps: int = Field(..., description="Target video bitrate in kilobits per second")


class DeliveryProfileResponse(BaseModel):
    """Response representing a single delivery profile."""

    id: str
    name: str
    output_formats: list[OutputFormatSpec]
    loudness_target_lufs: float
    true_peak_ceiling_dbtp: float
    metadata_template: dict[str, Any] | None = None
    created_at: str


class CreateDeliveryProfileRequest(BaseModel):
    """Request to create a new delivery profile."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="Unique name for this delivery profile")
    output_formats: list[OutputFormatSpec] = Field(
        ..., description="Output formats to produce", min_length=1
    )
    loudness_target_lufs: float = Field(
        ...,
        le=0.0,
        description="Integrated loudness target in LUFS (must be ≤ 0)",
    )
    true_peak_ceiling_dbtp: float = Field(
        default=-1.0,
        le=0.0,
        description="True-peak ceiling in dBTP (must be ≤ 0)",
    )
    metadata_template: dict[str, Any] | None = Field(
        default=None,
        description="Optional metadata key/value pairs to embed in output",
    )


class DeliveryProfileListResponse(BaseModel):
    """Paginated list of delivery profiles."""

    items: list[DeliveryProfileResponse]
    total: int

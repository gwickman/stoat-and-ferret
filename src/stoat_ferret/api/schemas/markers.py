"""Pydantic schemas for timeline markers."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class MarkerCreate(BaseModel):
    """Schema for creating a new timeline marker."""

    start_time: float
    end_time: float | None = None
    name: str | None = None
    region_type: Literal["point", "section"] = "point"


class MarkerUpdate(BaseModel):
    """Schema for updating a timeline marker.

    region_type is intentionally omitted — it is immutable after create.
    """

    start_time: float | None = None
    end_time: float | None = None
    name: str | None = None


class MarkerResponse(BaseModel):
    """Schema for marker responses."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    project_id: str
    start_time: float
    end_time: float | None
    name: str | None
    region_type: str
    created_at: str

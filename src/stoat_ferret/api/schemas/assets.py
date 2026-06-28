# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Pydantic schemas for the user-asset library API (BL-515)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class AssetRead(BaseModel):
    """Public asset metadata returned by the API.

    The server-side file_path is intentionally excluded.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str = Field(description="Asset UUID.")
    original_filename: str = Field(description="Filename as provided at upload time.")
    content_hash: str = Field(description="SHA-256 hex digest of the file content.")
    mime_type: str = Field(description="MIME type detected from magic bytes.")
    kind: Literal["image", "audio", "subtitle", "font", "lut"] = Field(description="Asset kind.")
    size_bytes: int = Field(description="File size in bytes.")
    deleted_at: str | None = Field(
        default=None, description="ISO 8601 UTC timestamp of soft deletion, if deleted."
    )
    created_at: str = Field(description="ISO 8601 UTC creation timestamp.")
    updated_at: str = Field(description="ISO 8601 UTC last-update timestamp.")


class AssetListResponse(BaseModel):
    """Paginated list of assets."""

    items: list[AssetRead] = Field(description="Page of asset records.")
    offset: int = Field(description="Pagination offset used in this response.")
    limit: int = Field(description="Page size used in this response.")
    total: int = Field(description="Total count of matching active assets.")

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Pydantic schemas for QC analysis reports and requests."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class QCRunRequest(BaseModel):
    """Request body for POST /api/v1/qc/run."""

    artifact_path: str
    delivery_profile_id: str | None = None
    assertions: dict[str, float | None] | None = None
    job_id: str | None = None


class QCReportResponse(BaseModel):
    """Full QC analysis report returned by the API."""

    id: str
    job_id: str | None = None
    artifact_path: str
    delivery_profile_id: str | None = None
    overall_verdict: str
    checks: dict[str, Any]
    created_at: str

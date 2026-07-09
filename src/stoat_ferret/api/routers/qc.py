# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""QC analysis API endpoints.

Exposes three routes:
  POST  /api/v1/qc/run               — run all 11 checks, return QCReport (201)
  GET   /api/v1/qc/reports/{id}      — fetch a QCReport by UUID (200/404)
  GET   /api/v1/render/{job_id}/qc   — latest QCReport for a render job (200/404)
"""

from __future__ import annotations

import json
from typing import Any

import structlog
from fastapi import APIRouter, HTTPException, Request, status

from stoat_ferret.api.schemas.qc import QCReportResponse, QCRunRequest
from stoat_ferret.api.services.qc_service import QCService
from stoat_ferret.db.qc_repository import AsyncSQLiteQCReportRepository, QCReportRecord

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["qc"])


def _get_service(request: Request) -> QCService:
    """Return the QCService from app state (raises 503 if not initialised)."""
    svc: QCService | None = getattr(request.app.state, "qc_service", None)
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "QC_SERVICE_UNAVAILABLE", "message": "QCService not initialised"},
        )
    return svc


def _get_repo(request: Request) -> AsyncSQLiteQCReportRepository:
    """Return a repository bound to the live database connection."""
    qc_repo: Any = getattr(request.app.state, "qc_report_repository", None)
    if qc_repo is not None:
        return qc_repo  # type: ignore[no-any-return]
    db = getattr(request.app.state, "db", None)
    if db is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "DB_UNAVAILABLE", "message": "Database not initialised"},
        )
    return AsyncSQLiteQCReportRepository(db)


def _record_to_response(record: QCReportRecord) -> QCReportResponse:
    """Convert a QCReportRecord to a QCReportResponse."""
    checks: Any = json.loads(record.checks) if isinstance(record.checks, str) else record.checks
    return QCReportResponse(
        id=record.id,
        job_id=record.job_id,
        artifact_path=record.artifact_path,
        delivery_profile_id=record.delivery_profile_id,
        overall_verdict=record.overall_verdict,
        checks=checks,
        created_at=record.created_at,
    )


@router.post("/qc/run", status_code=status.HTTP_201_CREATED, response_model=QCReportResponse)
async def run_qc(body: QCRunRequest, request: Request) -> QCReportResponse:
    """Run all 12 QC checks over a rendered artifact and return a QCReport.

    Returns HTTP 201 with the complete QCReport on success.
    Returns HTTP 422 when the artifact path is missing or invalid.
    Returns HTTP 404 when delivery_profile_id is provided but not found.
    """
    svc = _get_service(request)

    # If delivery_profile_id given, verify it exists (profiles not yet implemented → 404)
    if body.delivery_profile_id is not None:
        # Attempt lookup; fail fast if profile does not exist
        db = getattr(request.app.state, "db", None)
        profile_found = False
        if db is not None:
            try:
                cursor = await db.execute(
                    "SELECT id FROM delivery_profiles WHERE id = ? LIMIT 1",
                    (body.delivery_profile_id,),
                )
                row = await cursor.fetchone()
                profile_found = row is not None
            except Exception:
                profile_found = False
        if not profile_found:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "DELIVERY_PROFILE_NOT_FOUND",
                    "message": f"Delivery profile '{body.delivery_profile_id}' not found",
                },
            )

    try:
        record = await svc.run_checks(
            artifact_path=body.artifact_path,
            job_id=body.job_id,
            delivery_profile_id=body.delivery_profile_id,
            assertions=body.assertions,
        )
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "ARTIFACT_NOT_FOUND", "message": str(exc)},
        ) from exc

    return _record_to_response(record)


@router.get("/qc/reports/{report_id}", response_model=QCReportResponse)
async def get_qc_report(report_id: str, request: Request) -> QCReportResponse:
    """Fetch a QCReport by UUID.

    Returns HTTP 200 with the QCReport.
    Returns HTTP 404 when the report does not exist.
    """
    repo = _get_repo(request)
    record = await repo.get_by_id(report_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "QC_REPORT_NOT_FOUND", "message": f"No report with id={report_id}"},
        )
    return _record_to_response(record)


@router.get("/render/{job_id}/qc", response_model=QCReportResponse)
async def get_render_job_qc(job_id: str, request: Request) -> QCReportResponse:
    """Return the latest QCReport for a render job.

    Uses ORDER BY created_at DESC LIMIT 1 for deterministic lookup.
    Returns HTTP 404 when no report exists for the given job.
    """
    repo = _get_repo(request)
    record = await repo.get_latest_by_job_id(job_id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "QC_REPORT_NOT_FOUND",
                "message": f"No QC report found for render job '{job_id}'",
            },
        )
    return _record_to_response(record)

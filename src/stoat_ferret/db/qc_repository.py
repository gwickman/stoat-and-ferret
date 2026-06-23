# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""QC report repository for persisting QCReport records."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol

import aiosqlite


@dataclass
class QCReportRecord:
    """Runtime data object for a persisted QC report."""

    id: str
    job_id: str | None
    artifact_path: str
    delivery_profile_id: str | None
    overall_verdict: str
    checks: str  # JSON-serialized dict of check results
    created_at: str


class AsyncQCReportRepository(Protocol):
    """Protocol for async QC report persistence."""

    async def create(self, record: QCReportRecord) -> QCReportRecord:
        """Insert a new QC report and return it."""
        ...

    async def get_by_id(self, report_id: str) -> QCReportRecord | None:
        """Fetch a QC report by primary key."""
        ...

    async def get_latest_by_job_id(self, job_id: str) -> QCReportRecord | None:
        """Return the most recent QC report for a render job, or None."""
        ...


class AsyncSQLiteQCReportRepository:
    """Async SQLite implementation of AsyncQCReportRepository."""

    def __init__(self, conn: aiosqlite.Connection) -> None:
        """Initialise with an open aiosqlite connection."""
        self._conn = conn

    async def create(self, record: QCReportRecord) -> QCReportRecord:
        """Insert a new QC report."""
        await self._conn.execute(
            """
            INSERT INTO qc_reports
                (id, job_id, artifact_path, delivery_profile_id,
                 overall_verdict, checks, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record.id,
                record.job_id,
                record.artifact_path,
                record.delivery_profile_id,
                record.overall_verdict,
                record.checks,
                record.created_at,
            ),
        )
        await self._conn.commit()
        return record

    async def get_by_id(self, report_id: str) -> QCReportRecord | None:
        """Fetch a QC report by primary key."""
        cursor = await self._conn.execute(
            "SELECT id, job_id, artifact_path, delivery_profile_id, "
            "overall_verdict, checks, created_at FROM qc_reports WHERE id = ?",
            (report_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return QCReportRecord(
            id=row[0],
            job_id=row[1],
            artifact_path=row[2],
            delivery_profile_id=row[3],
            overall_verdict=row[4],
            checks=row[5],
            created_at=row[6],
        )

    async def get_latest_by_job_id(self, job_id: str) -> QCReportRecord | None:
        """Return the most recent QC report for a render job."""
        cursor = await self._conn.execute(
            "SELECT id, job_id, artifact_path, delivery_profile_id, "
            "overall_verdict, checks, created_at FROM qc_reports "
            "WHERE job_id = ? ORDER BY created_at DESC LIMIT 1",
            (job_id,),
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return QCReportRecord(
            id=row[0],
            job_id=row[1],
            artifact_path=row[2],
            delivery_profile_id=row[3],
            overall_verdict=row[4],
            checks=row[5],
            created_at=row[6],
        )


class InMemoryQCReportRepository:
    """In-memory QC report repository for testing."""

    def __init__(self) -> None:
        """Initialise empty store."""
        self._records: dict[str, QCReportRecord] = {}

    async def create(self, record: QCReportRecord) -> QCReportRecord:
        """Store a QC report."""
        self._records[record.id] = record
        return record

    async def get_by_id(self, report_id: str) -> QCReportRecord | None:
        """Return the record or None."""
        return self._records.get(report_id)

    async def get_latest_by_job_id(self, job_id: str) -> QCReportRecord | None:
        """Return the most recently created report for the given job_id."""
        matches = [r for r in self._records.values() if r.job_id == job_id]
        if not matches:
            return None
        return max(matches, key=lambda r: r.created_at)

    def to_dict(self, record: QCReportRecord) -> dict:  # type: ignore[type-arg]
        """Helper: deserialise checks JSON for assertions in tests."""
        return {
            "id": record.id,
            "job_id": record.job_id,
            "artifact_path": record.artifact_path,
            "delivery_profile_id": record.delivery_profile_id,
            "overall_verdict": record.overall_verdict,
            "checks": json.loads(record.checks),
            "created_at": record.created_at,
        }

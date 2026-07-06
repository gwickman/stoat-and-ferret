# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Evidence hygiene tests for render evidence persistence (BL-554).

Verifies that evidence_json is populated on the RenderJob after FFmpeg
execution, that the render.evidence_persisted event fires, and that
evidence invariants (exit_code, output_size_bytes set before event) hold.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from stoat_ferret.api.settings import Settings
from stoat_ferret.api.websocket.manager import ConnectionManager
from stoat_ferret.render.checkpoints import RenderCheckpointManager
from stoat_ferret.render.executor import RenderExecutor
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from stoat_ferret.render.service import RenderService


def _make_job(output_path: str = "/tmp/out.mp4") -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="test-job-001",
        project_id="proj-001",
        status=RenderStatus.RUNNING,
        output_path=output_path,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=json.dumps({"total_duration": 5.0, "settings": {}}),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


async def test_render_evidence_populated(tmp_path):
    """Evidence dict is built and stored after executor.execute() returns.

    Verifies BL-554-AC-6 (FR-002-AC-1): after a successful FFmpeg run,
    the executor's pop_evidence() returns a dict with all required fields,
    and the RenderJob in the repository has evidence_json set.
    """
    # Build a real command that exits 0 on all platforms
    if sys.platform == "win32":
        command = ["cmd", "/c", "exit", "0"]
    else:
        command = ["true"]

    executor = RenderExecutor()
    job = _make_job(output_path=str(tmp_path / "out.mp4"))

    # Create a dummy output file so output_size_bytes is populated
    out = tmp_path / "out.mp4"
    out.write_bytes(b"fake-mp4-data")

    captured_events: list[str] = []

    def _capture_event(event_name: str, **kwargs):  # type: ignore[no-untyped-def]
        captured_events.append(event_name)
        return MagicMock()

    with patch("stoat_ferret.render.executor.logger") as mock_logger:
        mock_logger.bind.return_value = mock_logger
        mock_logger.debug.return_value = None
        mock_logger.info.side_effect = _capture_event
        mock_logger.warning.return_value = None
        mock_logger.error.return_value = None

        await executor.execute(job, command)

    evidence = executor.pop_evidence(job.id)

    assert evidence is not None, "pop_evidence() must return a dict after execute()"
    assert "command_args" in evidence
    assert "exit_code" in evidence
    assert "stderr_tail" in evidence
    assert "output_path" in evidence
    assert "output_size_bytes" in evidence
    assert "filter_script_path" in evidence

    # exit_code and output_size_bytes must be populated (BL-554 INV-002)
    assert evidence["exit_code"] is not None, "exit_code must be set"
    assert evidence["output_size_bytes"] is not None, "output_size_bytes must be set"
    assert evidence["output_size_bytes"] > 0

    # render.evidence_persisted event must have fired in executor (BL-554-AC-7)
    assert "render.evidence_persisted" in captured_events, (
        "render.evidence_persisted event must fire in executor"
    )


async def test_evidence_json_persisted_to_repository(tmp_path):
    """After run_job(), evidence_json is saved to the repository (BL-554-AC-1).

    Uses a noop-style approach: mock executor.execute() to return True and
    stub pop_evidence() with a synthetic evidence dict, then verify
    update_evidence was called on the repo.
    """
    repo = InMemoryRenderRepository()
    job = _make_job(output_path=str(tmp_path / "out.mp4"))
    await repo.create(job)

    # Create a dummy output file
    (tmp_path / "out.mp4").write_bytes(b"x" * 100)

    fake_evidence = {
        "command_args": ["ffmpeg", "-i", "input.mp4", "out.mp4"],
        "exit_code": 0,
        "stderr_tail": "",
        "output_path": str(tmp_path / "out.mp4"),
        "output_size_bytes": 100,
        "filter_script_path": None,
    }

    executor = MagicMock(spec=RenderExecutor)
    executor.execute = AsyncMock(return_value=True)
    executor.pop_evidence = MagicMock(return_value=fake_evidence)
    executor._progress_callback = None

    settings = MagicMock(spec=Settings)
    settings.render_retry_count = 0
    settings.render_mode = "real"

    service = RenderService(
        repository=repo,
        queue=MagicMock(spec=RenderQueue),
        executor=executor,
        checkpoint_manager=MagicMock(spec=RenderCheckpointManager),
        connection_manager=MagicMock(spec=ConnectionManager),
        settings=settings,
    )
    service._ffmpeg_available = True

    # Patch _output_file_ok to return True (simulate valid output)
    with (
        patch.object(service, "_output_file_ok", return_value=True),
        patch.object(service, "_complete_job", new_callable=AsyncMock),
        patch.object(service, "_broadcast_event", new_callable=AsyncMock),
        patch.object(service, "_broadcast_queue_status", new_callable=AsyncMock),
    ):
        await service.run_job(job, ["ffmpeg", "-i", "input.mp4", "out.mp4"])

    # Verify evidence was persisted
    saved = await repo.get(job.id)
    assert saved is not None
    assert saved.evidence_json is not None, "evidence_json must be set after run_job"
    parsed = json.loads(saved.evidence_json)
    assert parsed["exit_code"] == 0
    assert parsed["output_size_bytes"] == 100


async def test_evidence_schema_fields():
    """Evidence dict contains all required fields with correct types (BL-554 FR-001)."""
    if sys.platform == "win32":
        command = ["cmd", "/c", "exit", "1"]
    else:
        command = ["false"]

    executor = RenderExecutor()
    job = _make_job(output_path="/nonexistent/out.mp4")

    with patch("stoat_ferret.render.executor.logger") as mock_logger:
        mock_logger.bind.return_value = mock_logger
        mock_logger.debug.return_value = None
        mock_logger.info.return_value = None
        mock_logger.warning.return_value = None
        mock_logger.error.return_value = None

        await executor.execute(job, command)

    evidence = executor.pop_evidence(job.id)
    assert evidence is not None

    assert isinstance(evidence["command_args"], list)
    assert isinstance(evidence["exit_code"], int)
    assert isinstance(evidence["stderr_tail"], str)
    assert isinstance(evidence["output_path"], str)
    assert evidence["output_size_bytes"] is None or isinstance(evidence["output_size_bytes"], int)
    assert evidence["filter_script_path"] is None or isinstance(evidence["filter_script_path"], str)


async def test_render_evidence_fields_populated(tmp_path):
    """Evidence dict exposes the BL-505-AC-6 required fields after executor.execute().

    Verifies that command_args, exit_code, stderr_tail, output_size_bytes are all
    present and populated in the evidence dict returned by pop_evidence(). This is
    the authoritative verification gate for BL-505-AC-6 and BL-553-AC-6: evidence
    is populated via executor._persist_evidence() through the service.run_job() chain,
    not directly in worker.py.
    """
    if sys.platform == "win32":
        command = ["cmd", "/c", "exit", "0"]
    else:
        command = ["true"]

    executor = RenderExecutor()
    job = _make_job(output_path=str(tmp_path / "out.mp4"))

    (tmp_path / "out.mp4").write_bytes(b"fake-mp4-data")

    with patch("stoat_ferret.render.executor.logger") as mock_logger:
        mock_logger.bind.return_value = mock_logger
        mock_logger.debug.return_value = None
        mock_logger.info.return_value = None
        mock_logger.warning.return_value = None
        mock_logger.error.return_value = None

        await executor.execute(job, command)

    evidence = executor.pop_evidence(job.id)

    assert evidence is not None, "pop_evidence() must return a dict after execute()"
    # BL-505-AC-6 required fields
    assert "command_args" in evidence, "command_args must be present in evidence"
    assert "exit_code" in evidence, "exit_code must be present in evidence"
    assert "stderr_tail" in evidence, "stderr_tail must be present in evidence"
    assert "output_size_bytes" in evidence, "output_size_bytes must be present in evidence"
    assert isinstance(evidence["command_args"], list)
    assert evidence["exit_code"] is not None, "exit_code must be set after execution"
    assert isinstance(evidence["stderr_tail"], str)
    assert evidence["output_size_bytes"] is not None, (
        "output_size_bytes must be set when output exists"
    )
    assert evidence["output_size_bytes"] > 0

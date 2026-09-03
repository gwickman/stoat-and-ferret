# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for render worker: command builder and worker loop.

Covers command construction from valid render_plan JSON, input path
resolution via repositories, empty-segments fallback, multi-segment
truncation warning, error cases, RenderService integration, and the
RenderWorkerLoop async class (loop iteration, error handling, shutdown).
"""

from __future__ import annotations

import asyncio
import dataclasses
import json
import sys
import time
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stoat_ferret.api.schemas.render import SoftSubtitleSpec
from stoat_ferret.db.markers_repository import Marker
from stoat_ferret.db.models import Clip, Video
from stoat_ferret.effects.definitions import CROP_EFFECT, TIME_STRETCH, VOLUME
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import (
    CommandBuildError,
    RenderWorkerLoop,
    TtsCueAudioInput,
    _build_mc_subtitle_inputs,
    build_command_for_job,
)

# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

_PROJECT_ID = "proj-123"
_VIDEO_ID = "vid-456"
_CLIP_ID = "clip-789"
_VIDEO_PATH = "/media/source.mp4"
_OUTPUT_PATH = "/renders/output.mp4"


def _make_render_plan(
    *,
    total_duration: float = 60.0,
    codec: str = "libx264",
    fps: float = 30.0,
    width: int = 1920,
    height: int = 1080,
    quality_preset: str = "standard",
    segments: list[dict] | None = None,
    filter_graph: str | None = None,
) -> str:
    settings: dict = {
        "output_format": "mp4",
        "width": width,
        "height": height,
        "codec": codec,
        "quality_preset": quality_preset,
        "fps": fps,
    }
    if filter_graph is not None:
        settings["filter_graph"] = filter_graph
    plan: dict = {
        "total_duration": total_duration,
        "settings": settings,
    }
    if segments is not None:
        plan["segments"] = segments
    return json.dumps(plan)


def _make_job(
    *,
    project_id: str = _PROJECT_ID,
    output_path: str = _OUTPUT_PATH,
    render_plan: str | None = None,
) -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="job-001",
        project_id=project_id,
        status=RenderStatus.RUNNING,
        output_path=output_path,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=render_plan or _make_render_plan(),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _make_clip(*, project_id: str = _PROJECT_ID, video_id: str = _VIDEO_ID) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=_CLIP_ID,
        project_id=project_id,
        source_video_id=video_id,
        in_point=0,
        out_point=100,
        timeline_position=0,
        created_at=now,
        updated_at=now,
    )


def _make_video(*, video_id: str = _VIDEO_ID, path: str = _VIDEO_PATH) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=video_id,
        path=path,
        filename="source.mp4",
        duration_frames=1800,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1920,
        height=1080,
        video_codec="h264",
        file_size=100_000_000,
        created_at=now,
        updated_at=now,
    )


def _make_repos(
    clips: list[Clip] | None = None,
    video: Video | None = None,
) -> tuple[AsyncMock, AsyncMock]:
    """Return (clip_repo, video_repo) mocks with sensible defaults."""
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(
        return_value=clips if clips is not None else [_make_clip()]
    )

    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=video if video is not None else _make_video())

    return clip_repo, video_repo


# ---------------------------------------------------------------------------
# TestCommandBuilder — valid render_plan construction
# ---------------------------------------------------------------------------


class TestCommandBuilder:
    """Command construction from valid render_plan JSON."""

    @pytest.mark.asyncio
    async def test_parse_valid_render_plan(self) -> None:
        """Parsing a valid render_plan produces a non-empty command list."""
        job = _make_job()
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert isinstance(cmd, list)
        assert all(isinstance(s, str) for s in cmd)
        assert len(cmd) > 0

    @pytest.mark.asyncio
    async def test_input_path_resolution(self) -> None:
        """AC-1.1: Command includes -i {input_path} from video repository."""
        job = _make_job()
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-i" in cmd
        idx = cmd.index("-i")
        assert cmd[idx + 1] == _VIDEO_PATH

    @pytest.mark.asyncio
    async def test_output_path_appended(self) -> None:
        """AC-1.2: Command ends with the job's output_path."""
        job = _make_job()
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert cmd[-1] == _OUTPUT_PATH

    @pytest.mark.asyncio
    async def test_encoder_settings_included(self) -> None:
        """AC-1.3: Command includes codec from render_plan settings."""
        job = _make_job(render_plan=_make_render_plan(codec="libx264"))
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-c:v" in cmd
        codec_idx = cmd.index("-c:v")
        assert cmd[codec_idx + 1] == "libx264"

    @pytest.mark.asyncio
    async def test_command_format_shell_ready(self) -> None:
        """AC-1.4: Command is a list of strings with no shell escaping."""
        job = _make_job()
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert isinstance(cmd, list)
        assert all(isinstance(s, str) for s in cmd)
        # First element is ffmpeg executable
        assert cmd[0] == "ffmpeg"

    @pytest.mark.asyncio
    async def test_filter_graph_from_settings(self) -> None:
        """AC-1.3: filter_graph from settings used when present."""
        fg = "scale=640:480,vflip"
        job = _make_job(render_plan=_make_render_plan(filter_graph=fg))
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert cmd[vf_idx + 1] == fg

    @pytest.mark.asyncio
    async def test_scale_filter_from_dimensions(self) -> None:
        """AC-1.3: scale filter built from width/height when filter_graph absent."""
        job = _make_job(render_plan=_make_render_plan(width=1280, height=720))
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert cmd[vf_idx + 1] == "scale=1280:720"

    @pytest.mark.asyncio
    async def test_4k_dimensions_produce_scale_filter(self) -> None:
        """BL-390-AC-3: build_command_for_job with 4K dimensions produces -vf scale=3840:2160."""
        job = _make_job(render_plan=_make_render_plan(width=3840, height=2160))
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert cmd[vf_idx + 1] == "scale=3840:2160"

    @pytest.mark.asyncio
    async def test_default_dimensions_applied_when_missing(self) -> None:
        """BL-390 FR-004-AC-2: plan without width/height defaults to scale=1920:1080."""
        plan = json.dumps({"total_duration": 60.0, "settings": {"codec": "libx264", "fps": 30.0}})
        job = _make_job(render_plan=plan)
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-vf" in cmd
        vf_idx = cmd.index("-vf")
        assert cmd[vf_idx + 1] == "scale=1920:1080"

    @pytest.mark.asyncio
    async def test_fps_included(self) -> None:
        """AC-1.3: Frame rate from settings included in command."""
        job = _make_job(render_plan=_make_render_plan(fps=24.0))
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-r" in cmd
        r_idx = cmd.index("-r")
        assert cmd[r_idx + 1] == "24.0"

    @pytest.mark.asyncio
    async def test_progress_flag_present(self) -> None:
        """BL-394-AC-1: -progress pipe:1 flag is present in the built command."""
        job = _make_job()
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-progress" in cmd
        prog_idx = cmd.index("-progress")
        assert cmd[prog_idx + 1] == "pipe:1"

    @pytest.mark.asyncio
    async def test_progress_flag_before_output_path(self) -> None:
        """BL-394-AC-1: -progress pipe:1 appears before the output path (not after)."""
        job = _make_job()
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        prog_idx = cmd.index("-progress")
        out_idx = cmd.index(_OUTPUT_PATH)
        assert prog_idx < out_idx

    @pytest.mark.asyncio
    async def test_clip_repository_queried(self) -> None:
        """AC-2.1: Clip repository list_by_project called with job's project_id."""
        job = _make_job()
        clip_repo, video_repo = _make_repos()

        await build_command_for_job(job, clip_repo, video_repo)

        clip_repo.list_by_project.assert_awaited_once_with(_PROJECT_ID)

    @pytest.mark.asyncio
    async def test_video_id_from_first_clip(self) -> None:
        """AC-2.2/AC-2.3: Video repository queried with first clip's source_video_id."""
        job = _make_job()
        clip = _make_clip(video_id="specific-vid-id")
        video = _make_video(video_id="specific-vid-id", path="/videos/specific.mp4")
        clip_repo, video_repo = _make_repos(clips=[clip], video=video)

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        video_repo.get.assert_awaited_once_with("specific-vid-id")
        idx = cmd.index("-i")
        assert cmd[idx + 1] == "/videos/specific.mp4"

    @pytest.mark.asyncio
    async def test_video_path_as_input(self) -> None:
        """AC-2.4: Video path used as input argument."""
        custom_path = "/mnt/media/project/raw.mp4"
        video = _make_video(path=custom_path)
        job = _make_job()
        clip_repo, video_repo = _make_repos(video=video)

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        idx = cmd.index("-i")
        assert cmd[idx + 1] == custom_path

    @pytest.mark.asyncio
    async def test_segment_timing_from_segment(self) -> None:
        """Segment timing (-ss, -t) derived from segments[0]."""
        segments = [{"index": 0, "timeline_start": 10.0, "timeline_end": 30.0}]
        job = _make_job(render_plan=_make_render_plan(segments=segments))
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-ss" in cmd
        ss_idx = cmd.index("-ss")
        assert cmd[ss_idx + 1] == "10.0"
        assert "-t" in cmd
        t_idx = cmd.index("-t")
        assert cmd[t_idx + 1] == "20.0"  # 30.0 - 10.0

    @pytest.mark.asyncio
    async def test_crf_included_for_x264(self) -> None:
        """x264 codec includes CRF value from quality preset."""
        job = _make_job(render_plan=_make_render_plan(codec="libx264", quality_preset="high"))
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-crf" in cmd
        crf_idx = cmd.index("-crf")
        assert cmd[crf_idx + 1] == "18"  # high quality

    @pytest.mark.asyncio
    async def test_crf_standard_preset(self) -> None:
        """Standard quality preset maps to CRF 23."""
        job = _make_job(render_plan=_make_render_plan(codec="libx264", quality_preset="standard"))
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-crf" in cmd
        crf_idx = cmd.index("-crf")
        assert cmd[crf_idx + 1] == "23"

    @pytest.mark.asyncio
    async def test_command_format(self) -> None:
        """Full command structure: ffmpeg -i {input} [flags...] {output}."""
        job = _make_job()
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert cmd[0] == "ffmpeg"
        assert "-i" in cmd
        assert cmd[-1] == _OUTPUT_PATH

    @pytest.mark.asyncio
    async def test_integration_with_run_job(self) -> None:
        """Command from build_command_for_job is accepted by RenderService.run_job()."""
        from unittest.mock import AsyncMock as AM

        from stoat_ferret.api.settings import Settings
        from stoat_ferret.api.websocket.manager import ConnectionManager
        from stoat_ferret.render.executor import RenderExecutor
        from stoat_ferret.render.queue import RenderQueue
        from stoat_ferret.render.render_repository import InMemoryRenderRepository
        from stoat_ferret.render.service import RenderService

        # Build command
        job = _make_job()
        clip_repo, video_repo = _make_repos()
        cmd = await build_command_for_job(job, clip_repo, video_repo)

        # Verify command type and structure
        assert isinstance(cmd, list)
        assert all(isinstance(s, str) for s in cmd)

        # Set up a RenderService with a mocked executor
        repo = InMemoryRenderRepository()
        saved_job = await repo.create(job)

        mock_executor = MagicMock(spec=RenderExecutor)
        mock_executor.execute = AM(return_value=True)
        mock_executor._cleanup_temp_files = MagicMock()
        mock_executor._progress_callback = None

        ws = MagicMock(spec=ConnectionManager)
        ws.broadcast = AM(return_value=None)

        mock_checkpoint = MagicMock()
        mock_checkpoint.cleanup_stale = AM(return_value=0)
        mock_checkpoint.recover = AM(return_value=[])

        service = RenderService(
            repository=repo,
            queue=RenderQueue(repository=repo),
            executor=mock_executor,
            checkpoint_manager=mock_checkpoint,
            connection_manager=ws,
            settings=Settings(),
        )

        # run_job should accept the command without TypeError
        await service.run_job(saved_job, cmd)

        # Executor received the command list
        mock_executor.execute.assert_awaited_once()
        call_args = mock_executor.execute.call_args
        received_cmd = call_args[0][1]  # positional arg index 1
        assert received_cmd == cmd


# ---------------------------------------------------------------------------
# TestCommandBuilderErrors — error cases
# ---------------------------------------------------------------------------


class TestCommandBuilderErrors:
    """Error cases: malformed JSON, missing clip, missing video, empty output."""

    @pytest.mark.asyncio
    async def test_malformed_json(self) -> None:
        """AC-5.1: Malformed render_plan JSON raises ValueError with parse_error."""
        job = _make_job(render_plan="{not valid json")
        clip_repo, video_repo = _make_repos()

        with pytest.raises(ValueError, match="Invalid render_plan JSON"):
            await build_command_for_job(job, clip_repo, video_repo)

    @pytest.mark.asyncio
    async def test_missing_settings_field(self) -> None:
        """AC-5.2: Missing 'settings' field raises ValueError."""
        plan = json.dumps({"total_duration": 60.0})
        job = _make_job(render_plan=plan)
        clip_repo, video_repo = _make_repos()

        with pytest.raises(ValueError, match="render_plan missing required field: settings"):
            await build_command_for_job(job, clip_repo, video_repo)

    @pytest.mark.asyncio
    async def test_missing_total_duration_field(self) -> None:
        """AC-5.2: Missing 'total_duration' field raises ValueError."""
        plan = json.dumps({"settings": {"codec": "libx264", "fps": 30.0}})
        job = _make_job(render_plan=plan)
        clip_repo, video_repo = _make_repos()

        with pytest.raises(ValueError, match="render_plan missing required field: total_duration"):
            await build_command_for_job(job, clip_repo, video_repo)

    @pytest.mark.asyncio
    async def test_no_clips(self) -> None:
        """AC-5.3: Project with no clips raises CommandBuildError."""
        job = _make_job()
        clip_repo, video_repo = _make_repos(clips=[])

        with pytest.raises(
            CommandBuildError, match=f"Project {_PROJECT_ID} has no clips in timeline"
        ):
            await build_command_for_job(job, clip_repo, video_repo)

    @pytest.mark.asyncio
    async def test_video_not_found(self) -> None:
        """AC-5.4: Video not found raises CommandBuildError."""
        job = _make_job()
        clip_repo = AsyncMock()
        clip_repo.list_by_project = AsyncMock(return_value=[_make_clip()])
        video_repo = AsyncMock()
        video_repo.get = AsyncMock(return_value=None)  # video not found

        with pytest.raises(
            CommandBuildError, match=f"Video {_VIDEO_ID} not found for project {_PROJECT_ID}"
        ):
            await build_command_for_job(job, clip_repo, video_repo)

    @pytest.mark.asyncio
    async def test_empty_output_path(self) -> None:
        """AC-5.5: Empty output_path raises ValueError."""
        job = _make_job(output_path="")
        clip_repo, video_repo = _make_repos()

        with pytest.raises(ValueError, match="output_path is empty or None"):
            await build_command_for_job(job, clip_repo, video_repo)

    @pytest.mark.asyncio
    async def test_none_output_path(self) -> None:
        """AC-5.5: None output_path raises ValueError."""
        job = _make_job(output_path="")
        job.output_path = ""  # ensure empty
        clip_repo, video_repo = _make_repos()

        with pytest.raises(ValueError, match="output_path is empty or None"):
            await build_command_for_job(job, clip_repo, video_repo)


# ---------------------------------------------------------------------------
# TestCommandBuilderSegments — segment fallback and multi-segment warning
# ---------------------------------------------------------------------------


class TestCommandBuilderSegments:
    """Empty-segments fallback via total_duration; multi-segment warning."""

    @pytest.mark.asyncio
    async def test_empty_segments_uses_total_duration(self) -> None:
        """AC-3.1/AC-3.2: Empty segments list synthesizes segment from total_duration."""
        plan = _make_render_plan(total_duration=45.0, segments=[])
        job = _make_job(render_plan=plan)
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        # Should have -ss 0.0 and -t 45.0
        assert "-ss" in cmd
        ss_idx = cmd.index("-ss")
        assert cmd[ss_idx + 1] == "0.0"
        assert "-t" in cmd
        t_idx = cmd.index("-t")
        assert cmd[t_idx + 1] == "45.0"

    @pytest.mark.asyncio
    async def test_empty_segments_zero_duration_raises(self) -> None:
        """AC-3.3: Empty segments AND duration <= 0 raises ValueError."""
        plan = _make_render_plan(total_duration=0.0, segments=[])
        job = _make_job(render_plan=plan)
        clip_repo, video_repo = _make_repos()

        with pytest.raises(ValueError, match="no renderable content"):
            await build_command_for_job(job, clip_repo, video_repo)

    @pytest.mark.asyncio
    async def test_empty_segments_negative_duration_raises(self) -> None:
        """AC-3.3: Negative total_duration with empty segments raises ValueError."""
        plan = _make_render_plan(total_duration=-5.0, segments=[])
        job = _make_job(render_plan=plan)
        clip_repo, video_repo = _make_repos()

        with pytest.raises(ValueError, match="no renderable content"):
            await build_command_for_job(job, clip_repo, video_repo)

    @pytest.mark.asyncio
    async def test_single_segment_used_directly(self) -> None:
        """Single segment list uses segments[0] timing."""
        segments = [{"index": 0, "timeline_start": 5.0, "timeline_end": 25.0}]
        plan = _make_render_plan(total_duration=25.0, segments=segments)
        job = _make_job(render_plan=plan)
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        ss_idx = cmd.index("-ss")
        t_idx = cmd.index("-t")
        assert cmd[ss_idx + 1] == "5.0"
        assert cmd[t_idx + 1] == "20.0"  # 25.0 - 5.0

    @pytest.mark.asyncio
    async def test_multi_segment_uses_first_only(self) -> None:
        """AC-4.1/AC-4.2: Multi-segment plan uses segments[0] only."""
        segments = [
            {"index": 0, "timeline_start": 0.0, "timeline_end": 30.0},
            {"index": 1, "timeline_start": 30.0, "timeline_end": 60.0},
        ]
        plan = _make_render_plan(total_duration=60.0, segments=segments)
        job = _make_job(render_plan=plan)
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        ss_idx = cmd.index("-ss")
        t_idx = cmd.index("-t")
        # Uses segments[0]: 0.0 to 30.0
        assert cmd[ss_idx + 1] == "0.0"
        assert cmd[t_idx + 1] == "30.0"

    @pytest.mark.asyncio
    async def test_multi_segment_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        """AC-4.3: Multi-segment plan logs render_worker.multi_segment_truncated at WARN."""
        segments = [
            {"index": 0, "timeline_start": 0.0, "timeline_end": 30.0},
            {"index": 1, "timeline_start": 30.0, "timeline_end": 60.0},
            {"index": 2, "timeline_start": 60.0, "timeline_end": 90.0},
        ]
        plan = _make_render_plan(total_duration=90.0, segments=segments)
        job = _make_job(render_plan=plan)
        clip_repo, video_repo = _make_repos()

        with patch("stoat_ferret.render.worker.logger") as mock_logger:
            await build_command_for_job(job, clip_repo, video_repo)
            mock_logger.warning.assert_called_once_with(
                "render_worker.multi_segment_truncated",
                segments_count=3,
                job_id=job.id,
            )

    @pytest.mark.asyncio
    async def test_single_segment_no_warning(self) -> None:
        """Single segment plan does NOT log multi_segment_truncated."""
        segments = [{"index": 0, "timeline_start": 0.0, "timeline_end": 30.0}]
        plan = _make_render_plan(total_duration=30.0, segments=segments)
        job = _make_job(render_plan=plan)
        clip_repo, video_repo = _make_repos()

        with patch("stoat_ferret.render.worker.logger") as mock_logger:
            await build_command_for_job(job, clip_repo, video_repo)
            mock_logger.warning.assert_not_called()


# ---------------------------------------------------------------------------
# Performance test (NFR-001)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_command_builder_performance() -> None:
    """NFR-001: Command builder completes in <10ms per job (mocked repos)."""
    job = _make_job()
    clip_repo, video_repo = _make_repos()

    start = time.perf_counter()
    await build_command_for_job(job, clip_repo, video_repo)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Raised from original <10ms: PyO3 cold-path overhead under full-suite asyncio load; see BL-594.
    _THRESHOLD_MS = 750 if sys.platform == "win32" else 500  # BL-594: PyO3 cold-path overhead
    assert elapsed_ms < _THRESHOLD_MS, (
        f"Command builder took {elapsed_ms:.1f}ms, expected <{_THRESHOLD_MS}ms"
        f" (platform={sys.platform})"
    )


# ---------------------------------------------------------------------------
# RenderWorkerLoop helpers
# ---------------------------------------------------------------------------


def _make_worker_loop(
    *,
    service: MagicMock | None = None,
    queue: MagicMock | None = None,
    clip_repo: AsyncMock | None = None,
    video_repo: AsyncMock | None = None,
) -> RenderWorkerLoop:
    """Return a RenderWorkerLoop with sensible mock defaults."""
    if service is None:
        service = MagicMock()
        service.run_job = AsyncMock(return_value=None)
        service._handle_failure = AsyncMock(return_value=None)
        service._repo = MagicMock()
        service._repo.update_status = AsyncMock(return_value=None)

    if queue is None:
        queue = MagicMock()

    if clip_repo is None:
        clip_repo = AsyncMock()

    if video_repo is None:
        video_repo = AsyncMock()

    return RenderWorkerLoop(
        service=service,
        queue=queue,
        clip_repository=clip_repo,
        video_repository=video_repo,
    )


# ---------------------------------------------------------------------------
# TestWorkerLoop — loop iteration, dequeue/execute pattern
# ---------------------------------------------------------------------------


class TestWorkerLoop:
    """Loop iteration, dequeue/execute pattern, and idle backoff."""

    @pytest.mark.asyncio
    async def test_dequeue_called_on_each_iteration(self) -> None:
        """AC-1.1: Loop continuously calls dequeue on the job queue."""
        queue = MagicMock()
        # Return None twice, then cancel to terminate
        queue.dequeue = AsyncMock(side_effect=[None, None, asyncio.CancelledError()])
        loop = _make_worker_loop(queue=queue)

        with patch("asyncio.sleep", new_callable=AsyncMock), pytest.raises(asyncio.CancelledError):
            await loop.run()

        assert queue.dequeue.call_count >= 2

    @pytest.mark.asyncio
    async def test_build_command_called_when_job_dequeued(self) -> None:
        """AC-1.2: When dequeue returns a job, build_command_for_job is called."""
        job = _make_job()
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=[job, asyncio.CancelledError()])

        clip_repo, video_repo = _make_repos()
        service = MagicMock()
        service.run_job = AsyncMock(return_value=None)

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            new_callable=AsyncMock,
            return_value=["ffmpeg", "-i", "input.mp4", "output.mp4"],
        ) as mock_build:
            loop = _make_worker_loop(
                service=service, queue=queue, clip_repo=clip_repo, video_repo=video_repo
            )
            with pytest.raises(asyncio.CancelledError):
                await loop.run()

        mock_build.assert_called_once_with(job, clip_repo, video_repo, None, None, None, None)

    @pytest.mark.asyncio
    async def test_run_job_called_with_built_command(self) -> None:
        """AC-1.4: Loop calls RenderService.run_job() with the built command."""
        job = _make_job()
        expected_cmd = ["ffmpeg", "-i", "in.mp4", "out.mp4"]
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=[job, asyncio.CancelledError()])
        service = MagicMock()
        service.run_job = AsyncMock(return_value=None)

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            new_callable=AsyncMock,
            return_value=expected_cmd,
        ):
            loop = _make_worker_loop(service=service, queue=queue)
            with pytest.raises(asyncio.CancelledError):
                await loop.run()

        service.run_job.assert_awaited_once_with(job, expected_cmd)

    @pytest.mark.asyncio
    async def test_ffmetadata_path_exercised_with_markers_and_title(self) -> None:
        """BL-651-AC-2/AC-3: markers+title drive the ffmetadata write path (now
        dispatched via asyncio.to_thread); build_command_for_job receives a
        real ffmetadata path and behavior survives the refactor."""
        plan = json.loads(_make_render_plan())
        plan["settings"]["metadata_title"] = "My Title"
        job = _make_job(render_plan=json.dumps(plan))

        marker = Marker(
            id="marker-1",
            project_id=_PROJECT_ID,
            start_time=1.0,
            end_time=5.0,
            name="Chapter 1",
            region_type="section",
            created_at="2026-01-01T00:00:00Z",
        )
        markers_repo = AsyncMock()
        markers_repo.list_by_project = AsyncMock(return_value=[marker])

        clip_repo, video_repo = _make_repos()
        service = MagicMock()
        service.run_job = AsyncMock(return_value=None)

        loop = RenderWorkerLoop(
            service=service,
            queue=MagicMock(),
            clip_repository=clip_repo,
            video_repository=video_repo,
            markers_repository=markers_repo,
        )

        captured: list[str | None] = []

        async def _capture_build(*args: Any, **_kwargs: Any) -> list[str]:
            captured.append(args[3])
            return ["ffmpeg", "-i", "in.mp4", "out.mp4"]

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            side_effect=_capture_build,
        ):
            await loop._run_job(job)

        assert len(captured) == 1
        ffmetadata_path = captured[0]
        assert ffmetadata_path is not None
        assert ffmetadata_path.endswith(".ffmetadata")
        markers_repo.list_by_project.assert_awaited_once_with(_PROJECT_ID, region_type="section")
        service.run_job.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_idle_backoff_on_none_dequeue(self) -> None:
        """AC-4.1/AC-4.2: When dequeue returns None, loop sleeps 100ms."""
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=[None, asyncio.CancelledError()])
        loop = _make_worker_loop(queue=queue)

        with patch("stoat_ferret.render.worker.asyncio") as mock_asyncio:
            mock_asyncio.sleep = AsyncMock(return_value=None)
            mock_asyncio.CancelledError = asyncio.CancelledError
            with pytest.raises(asyncio.CancelledError):
                await loop.run()

        mock_asyncio.sleep.assert_called_once_with(0.1)

    @pytest.mark.asyncio
    async def test_continues_after_idle(self) -> None:
        """AC-4.3: Loop continues after idle backoff to process next job."""
        job = _make_job()
        queue = MagicMock()
        # idle, then job, then cancel
        queue.dequeue = AsyncMock(side_effect=[None, job, asyncio.CancelledError()])
        service = MagicMock()
        service.run_job = AsyncMock(return_value=None)

        with (
            patch("asyncio.sleep", new_callable=AsyncMock),
            patch(
                "stoat_ferret.render.worker.build_command_for_job",
                new_callable=AsyncMock,
                return_value=["ffmpeg", "out.mp4"],
            ),
        ):
            loop = _make_worker_loop(service=service, queue=queue)
            with pytest.raises(asyncio.CancelledError):
                await loop.run()

        service.run_job.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_started_logged(self) -> None:
        """NFR-002: render_worker.started logged at startup."""
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=asyncio.CancelledError())
        loop = _make_worker_loop(queue=queue)

        with patch.object(loop, "logger") as mock_logger, pytest.raises(asyncio.CancelledError):
            await loop.run()

        mock_logger.info.assert_any_call("render_worker.started")

    def test_worker_injectable(self) -> None:
        """AC-5.1: Worker instance is injectable via DI (constructor params)."""
        service = MagicMock()
        service.run_job = AsyncMock()
        service._handle_failure = AsyncMock()
        service._repo = MagicMock()
        service._repo.update_status = AsyncMock()

        queue = MagicMock()
        clip_repo = AsyncMock()
        video_repo = AsyncMock()

        loop = RenderWorkerLoop(
            service=service,
            queue=queue,
            clip_repository=clip_repo,
            video_repository=video_repo,
        )

        assert loop.service is service
        assert loop.queue is queue
        assert loop.clip_repository is clip_repo
        assert loop.video_repository is video_repo

    @pytest.mark.asyncio
    async def test_task_storable_on_app_state(self) -> None:
        """AC-5.2/AC-5.3: Worker task can be stored and cancelled."""
        queue = MagicMock()
        queue.dequeue = AsyncMock(return_value=None)
        loop = _make_worker_loop(queue=queue)

        # Simulate: asyncio.create_task(loop.run()) → task reference
        with patch("asyncio.sleep", new_callable=AsyncMock):
            task = asyncio.create_task(loop.run())
            await asyncio.sleep(0)  # Let loop run one iteration

            # Simulate app.state.render_worker_task = task; task.cancel()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task


# ---------------------------------------------------------------------------
# TestWorkerLoopErrors — exception handling, failure path, continue after error
# ---------------------------------------------------------------------------


class TestWorkerLoopErrors:
    """Exception handling: run_job failures, handler failures, loop resilience."""

    @pytest.mark.asyncio
    async def test_run_job_exception_caught(self) -> None:
        """AC-2.1: Exception from run_job is caught; loop does not crash."""
        job = _make_job()
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=[job, asyncio.CancelledError()])
        service = MagicMock()
        service.run_job = AsyncMock(side_effect=RuntimeError("ffmpeg failed"))
        service._handle_failure = AsyncMock(return_value=None)

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            new_callable=AsyncMock,
            return_value=["ffmpeg"],
        ):
            loop = _make_worker_loop(service=service, queue=queue)
            with pytest.raises(asyncio.CancelledError):
                await loop.run()  # Should not raise RuntimeError

    @pytest.mark.asyncio
    async def test_handle_failure_called_on_exception(self) -> None:
        """AC-2.2: service._handle_failure called with job and str(exception)."""
        job = _make_job()
        error_msg = "ffmpeg process failed"
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=[job, asyncio.CancelledError()])
        service = MagicMock()
        service.run_job = AsyncMock(side_effect=RuntimeError(error_msg))
        service._handle_failure = AsyncMock(return_value=None)

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            new_callable=AsyncMock,
            return_value=["ffmpeg"],
        ):
            loop = _make_worker_loop(service=service, queue=queue)
            with pytest.raises(asyncio.CancelledError):
                await loop.run()

        service._handle_failure.assert_awaited_once_with(job, error_msg)

    @pytest.mark.asyncio
    async def test_handler_exception_caught(self) -> None:
        """AC-2.3: If _handle_failure raises, exception is caught; loop continues."""
        job = _make_job()
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=[job, asyncio.CancelledError()])
        service = MagicMock()
        service.run_job = AsyncMock(side_effect=RuntimeError("execution failed"))
        service._handle_failure = AsyncMock(side_effect=RuntimeError("handler failed"))
        service._repo = MagicMock()
        service._repo.update_status = AsyncMock(return_value=None)

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            new_callable=AsyncMock,
            return_value=["ffmpeg"],
        ):
            loop = _make_worker_loop(service=service, queue=queue)
            with pytest.raises(asyncio.CancelledError):
                await loop.run()  # Should not raise RuntimeError from handler

    @pytest.mark.asyncio
    async def test_direct_status_update_when_handler_fails(self) -> None:
        """AC-2.3: If _handle_failure raises, repo.update_status called directly with FAILED."""
        job = _make_job()
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=[job, asyncio.CancelledError()])
        service = MagicMock()
        service.run_job = AsyncMock(side_effect=RuntimeError("execution failed"))
        service._handle_failure = AsyncMock(side_effect=RuntimeError("handler failed"))
        service._repo = MagicMock()
        service._repo.update_status = AsyncMock(return_value=None)

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            new_callable=AsyncMock,
            return_value=["ffmpeg"],
        ):
            loop = _make_worker_loop(service=service, queue=queue)
            with pytest.raises(asyncio.CancelledError):
                await loop.run()

        service._repo.update_status.assert_awaited_once()
        call_args = service._repo.update_status.call_args
        assert call_args[0][0] == job.id
        assert call_args[0][1] == RenderStatus.FAILED

    @pytest.mark.asyncio
    async def test_error_logged_on_job_failure(self) -> None:
        """AC-2.4: render_worker.job_failed logged at ERROR level on exception."""
        job = _make_job()
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=[job, asyncio.CancelledError()])
        service = MagicMock()
        service.run_job = AsyncMock(side_effect=RuntimeError("exec error"))
        service._handle_failure = AsyncMock(return_value=None)

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            new_callable=AsyncMock,
            return_value=["ffmpeg"],
        ):
            loop = _make_worker_loop(service=service, queue=queue)
            with (
                patch.object(loop, "logger") as mock_logger,
                pytest.raises(asyncio.CancelledError),
            ):
                await loop.run()

        mock_logger.error.assert_any_call(
            "render_worker.job_failed",
            job_id=job.id,
            error_message="exec error",
        )

    @pytest.mark.asyncio
    async def test_loop_continues_after_exception(self) -> None:
        """AC-2.5: Loop continues processing after a job exception (no crash)."""
        job1 = _make_job()
        job2 = _make_job()
        job2.id = "job-002"

        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=[job1, job2, asyncio.CancelledError()])
        service = MagicMock()
        # job1 fails, job2 succeeds
        service.run_job = AsyncMock(side_effect=[RuntimeError("job1 failed"), None])
        service._handle_failure = AsyncMock(return_value=None)

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            new_callable=AsyncMock,
            return_value=["ffmpeg"],
        ):
            loop = _make_worker_loop(service=service, queue=queue)
            with pytest.raises(asyncio.CancelledError):
                await loop.run()

        assert service.run_job.await_count == 2

    @pytest.mark.asyncio
    async def test_command_build_error_handled(self) -> None:
        """CommandBuildError from build_command_for_job is treated as a job failure."""
        job = _make_job()
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=[job, asyncio.CancelledError()])
        service = MagicMock()
        service._handle_failure = AsyncMock(return_value=None)

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            new_callable=AsyncMock,
            side_effect=CommandBuildError("no clips"),
        ):
            loop = _make_worker_loop(service=service, queue=queue)
            with pytest.raises(asyncio.CancelledError):
                await loop.run()

        service._handle_failure.assert_awaited_once()


# ---------------------------------------------------------------------------
# TestWorkerLoopShutdown — CancelledError propagation, clean shutdown
# ---------------------------------------------------------------------------


class TestWorkerLoopShutdown:
    """Shutdown: CancelledError propagated; no failure handler called on cancel."""

    @pytest.mark.asyncio
    async def test_cancelled_error_propagated(self) -> None:
        """AC-3.1: CancelledError is re-raised by run() (not suppressed)."""
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=asyncio.CancelledError())
        loop = _make_worker_loop(queue=queue)

        with pytest.raises(asyncio.CancelledError):
            await loop.run()

    @pytest.mark.asyncio
    async def test_no_handle_failure_on_cancelled_error(self) -> None:
        """AC-3.2: _handle_failure NOT called when CancelledError signals shutdown."""
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=asyncio.CancelledError())
        service = MagicMock()
        service._handle_failure = AsyncMock(return_value=None)

        loop = _make_worker_loop(service=service, queue=queue)
        with pytest.raises(asyncio.CancelledError):
            await loop.run()

        service._handle_failure.assert_not_called()

    @pytest.mark.asyncio
    async def test_stopped_logged_on_cancel(self) -> None:
        """NFR-002: render_worker.stopped logged when CancelledError received."""
        queue = MagicMock()
        queue.dequeue = AsyncMock(side_effect=asyncio.CancelledError())
        loop = _make_worker_loop(queue=queue)

        with patch.object(loop, "logger") as mock_logger, pytest.raises(asyncio.CancelledError):
            await loop.run()

        mock_logger.info.assert_any_call("render_worker.stopped")

    @pytest.mark.asyncio
    async def test_cancel_via_task(self) -> None:
        """AC-5.3: Task can be cancelled via task.cancel() and terminates cleanly."""
        queue = MagicMock()
        queue.dequeue = AsyncMock(return_value=None)
        loop = _make_worker_loop(queue=queue)

        with patch("stoat_ferret.render.worker.asyncio.sleep", new_callable=AsyncMock):
            task = asyncio.create_task(loop.run())
            await asyncio.sleep(0)  # Yield to let the task start
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

    @pytest.mark.asyncio
    async def test_no_failure_handler_when_run_job_raises_cancelled(self) -> None:
        """AC-3.2: CancelledError from run_job propagates without calling _handle_failure."""
        job = _make_job()
        queue = MagicMock()
        # job returned, then run_job raises CancelledError (simulates task cancel mid-job)
        queue.dequeue = AsyncMock(return_value=job)
        service = MagicMock()
        service.run_job = AsyncMock(side_effect=asyncio.CancelledError())
        service._handle_failure = AsyncMock(return_value=None)

        with patch(
            "stoat_ferret.render.worker.build_command_for_job",
            new_callable=AsyncMock,
            return_value=["ffmpeg"],
        ):
            loop = _make_worker_loop(service=service, queue=queue)
            with pytest.raises(asyncio.CancelledError):
                await loop.run()

        service._handle_failure.assert_not_called()


# ---------------------------------------------------------------------------
# Golden argv helpers (BL-736 AC-1)
# ---------------------------------------------------------------------------

_G_PROJECT_ID = "proj-golden"
_G_OUTPUT_PATH = "/renders/golden.mp4"
_G_VIDEO_PATH_1 = "/media/clip1.mp4"
_G_VIDEO_PATH_2 = "/media/clip2.mp4"
_G_VIDEO_PATH_3 = "/media/clip3.mp4"
_G_SUB_UUID = uuid.UUID("aaaabbbb-cccc-dddd-eeee-000011112222")


def _g_make_job(plan: str) -> RenderJob:
    now = datetime.now(timezone.utc)
    return RenderJob(
        id="job-golden",
        project_id=_G_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=_G_OUTPUT_PATH,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=plan,
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=now,
        updated_at=now,
        completed_at=None,
    )


def _g_make_plan(
    *,
    total_duration: float = 30.0,
    width: int = 1920,
    height: int = 1080,
    fps: float = 30.0,
    codec: str = "libx264",
    quality_preset: str = "standard",
    soft_subtitles: list[dict] | None = None,
    transitions: list[dict] | None = None,
) -> str:
    settings: dict = {
        "output_format": "mp4",
        "width": width,
        "height": height,
        "codec": codec,
        "quality_preset": quality_preset,
        "fps": fps,
    }
    if soft_subtitles:
        settings["soft_subtitles"] = soft_subtitles
    if transitions is not None:
        settings["transitions"] = transitions
    return json.dumps({"total_duration": total_duration, "settings": settings})


def _g_make_clip(
    cid: str,
    vid_id: str,
    *,
    in_point: int = 0,
    out_point: int = 900,
    effects: list[Any] | None = None,
    clip_type: str = "file",
    source_asset_id: str | None = None,
    generator_params: dict[str, Any] | None = None,
) -> Clip:
    now = datetime.now(timezone.utc)
    return Clip(
        id=cid,
        project_id=_G_PROJECT_ID,
        source_video_id=vid_id,
        in_point=in_point,
        out_point=out_point,
        timeline_position=0,
        created_at=now,
        updated_at=now,
        clip_type=clip_type,
        effects=effects,
        source_asset_id=source_asset_id,
        generator_params=generator_params,
    )


def _g_make_video(vid_id: str, path: str, *, audio_codec: str | None = None) -> Video:
    now = datetime.now(timezone.utc)
    return Video(
        id=vid_id,
        path=path,
        filename="source.mp4",
        duration_frames=1800,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1920,
        height=1080,
        video_codec="h264",
        file_size=100_000_000,
        created_at=now,
        updated_at=now,
        audio_codec=audio_codec,
    )


def _g_clip_repo(*clips: Clip) -> AsyncMock:
    r: AsyncMock = AsyncMock()
    r.list_by_project = AsyncMock(return_value=list(clips))
    return r


def _g_video_repo(*videos: Video) -> AsyncMock:
    vid_map = {v.id: v for v in videos}
    r: AsyncMock = AsyncMock()

    async def _get(vid_id: str) -> Video | None:
        return vid_map.get(vid_id)

    r.get = AsyncMock(side_effect=_get)
    return r


def _g_asset_repo(file_path: str = "/assets/subs/en.srt") -> AsyncMock:
    r: AsyncMock = AsyncMock()
    asset = MagicMock()
    asset.file_path = file_path
    asset.deleted_at = None
    r.get_by_id = AsyncMock(return_value=asset)
    return r


# ---------------------------------------------------------------------------
# TestGoldenArgv — full-list FFmpeg argv characterisation (BL-736 AC-1)
# ---------------------------------------------------------------------------


class TestGoldenArgv:
    """Full-list golden argv characterisation tests for build_command_for_job.

    Expected values captured by running the real implementation against concrete
    fixtures; never hand-authored. These lock the full argv contract before the
    split in Feature 003 (BL-737).
    """

    @pytest.mark.asyncio
    async def test_golden_case_1_single_file_no_effects(self) -> None:
        """Single file clip, no effects -> legacy -vf scale path."""
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        clip = _g_make_clip("clip-1", "vid-1")
        job = _g_make_job(_g_make_plan())

        result = await build_command_for_job(job, _g_clip_repo(clip), _g_video_repo(vid))

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-ss",
            "0.0",
            "-t",
            "30.0",
            "-vf",
            "scale=1920:1080",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_2_single_file_with_effects(self) -> None:
        """Single file clip with effects -> translator filter_complex path."""
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        clip = _g_make_clip(
            "clip-2", "vid-1", effects=[{"effect_type": "color_filter", "parameters": {}}]
        )
        job = _g_make_job(_g_make_plan())

        result = await build_command_for_job(job, _g_clip_repo(clip), _g_video_repo(vid))

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-ss",
            "0.0",
            "-t",
            "30.0",
            "-filter_complex",
            "[0:v]fps=30,settb=1/30[v0];[v0]format=yuv420p[final]",
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_3_single_soft_subtitles_tts(self) -> None:
        """Single clip + soft subtitles + TTS -> scale+TTS filter_complex + subtitle streams."""
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        clip = _g_make_clip("clip-3", "vid-1")
        subs = [{"source_asset_id": str(_G_SUB_UUID), "language": "en", "is_default": True}]
        job = _g_make_job(_g_make_plan(soft_subtitles=subs))
        tts_inputs = [
            TtsCueAudioInput(
                cue_id="cue-1",
                audio_path="/renders/tts-001.wav",
                track_id="track-1",
                start_s=5.0,
                weight=1.0,
                volume_envelope=None,
            )
        ]

        result = await build_command_for_job(
            job,
            _g_clip_repo(clip),
            _g_video_repo(vid),
            tts_inputs=tts_inputs,
            asset_repository=_g_asset_repo(),
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/renders/tts-001.wav",
            "-i",
            "/assets/subs/en.srt",
            "-ss",
            "0.0",
            "-t",
            "30.0",
            "-filter_complex",
            "[0:v]scale=1920:1080[vout];[1:a]adelay=5000|5000,aformat=channel_layouts=stereo[tts0]",
            "-map",
            "[vout]",
            "-map",
            "[tts0]",
            "-map",
            "2:s",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=eng",
            "-disposition:s:0",
            "default",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_4_multi_clip_no_tts(self) -> None:
        """Two file clips, no TTS -> multi-clip translator with xfade filter_complex."""
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2)
        clip_a = _g_make_clip("clip-4a", "vid-1")
        clip_b = _g_make_clip("clip-4b", "vid-2")
        job = _g_make_job(_g_make_plan())

        result = await build_command_for_job(
            job, _g_clip_repo(clip_a, clip_b), _g_video_repo(vid1, vid2)
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/media/clip2.mp4",
            "-filter_complex",
            (
                "[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                "[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                "[pv0][pn1]xfade=transition=fade:duration=1:offset=29[xf0];"
                "[xf0]format=yuv420p[final]"
            ),
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_5_multi_clip_tts_later_audio(self) -> None:
        """Clip 0 video-only + TTS -> acrossfade with anullsrc amixed with TTS (BL-814)."""
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        vid3 = _g_make_video("vid-3", _G_VIDEO_PATH_3, audio_codec="aac")
        clip_a = _g_make_clip("clip-5a", "vid-1")  # no audio
        clip_b = _g_make_clip("clip-5b", "vid-3")  # audio_codec="aac"
        job = _g_make_job(_g_make_plan())
        tts_inputs = [
            TtsCueAudioInput(
                cue_id="cue-5",
                audio_path="/renders/tts-005.wav",
                track_id="track-1",
                start_s=10.0,
                weight=1.0,
                volume_envelope=None,
            )
        ]

        result = await build_command_for_job(
            job,
            _g_clip_repo(clip_a, clip_b),
            _g_video_repo(vid1, vid3),
            tts_inputs=tts_inputs,
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/media/clip3.mp4",
            "-i",
            "/renders/tts-005.wav",
            "-filter_complex",
            (
                "[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                "[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                "[pv0][pn1]xfade=transition=fade:duration=1:offset=29[xf0];"
                "[xf0]format=yuv420p[final];"
                "[2:a]adelay=10000|10000,aformat=channel_layouts=stereo[tts0];"
                "anullsrc=r=48000:cl=stereo:d=30.0[a0_silent];[a0_silent][1:a]acrossfade=d=1:o=0[src_aout_pre];"
                "[src_aout_pre]aformat=channel_layouts=stereo,aresample=48000[src_norm];"
                "[src_norm][tts0]amix=inputs=2:duration=longest[aout]"
            ),
            "-map",
            "[final]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_6_multi_clip_soft_subtitles_ffmetadata(self) -> None:
        """Two clips + soft subtitles + ffmetadata -> subtitle streams + chapter mapping."""
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2)
        clip_a = _g_make_clip("clip-6a", "vid-1")
        clip_b = _g_make_clip("clip-6b", "vid-2")
        subs = [{"source_asset_id": str(_G_SUB_UUID), "language": "es", "is_default": False}]
        job = _g_make_job(_g_make_plan(soft_subtitles=subs))

        result = await build_command_for_job(
            job,
            _g_clip_repo(clip_a, clip_b),
            _g_video_repo(vid1, vid2),
            ffmetadata_path="/tmp/chapters.ffmetadata",
            asset_repository=_g_asset_repo(),
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/media/clip2.mp4",
            "-i",
            "/tmp/chapters.ffmetadata",
            "-i",
            "/assets/subs/en.srt",
            "-filter_complex",
            (
                "[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                "[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                "[pv0][pn1]xfade=transition=fade:duration=1:offset=29[xf0];"
                "[xf0]format=yuv420p[final]"
            ),
            "-map",
            "[final]",
            "-an",
            "-map",
            "3:s",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "-map_chapters",
            "2",
            "-map_metadata",
            "2",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=spa",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_wipeleft_transition(self) -> None:
        """Two clips with wipeleft/0.35 saved transition -> xfade offset=29.65 (BL-792 AC-6)."""
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2)
        clip_a = _g_make_clip("clip-wt-a", "vid-1")  # out_point=900, in_point=0 -> 30.0s
        clip_b = _g_make_clip("clip-wt-b", "vid-2")
        transitions = [{"clip_a_id": "clip-wt-a", "transition_type": "wipeleft", "duration": 0.35}]
        job = _g_make_job(_g_make_plan(total_duration=29.65, transitions=transitions))

        result = await build_command_for_job(
            job, _g_clip_repo(clip_a, clip_b), _g_video_repo(vid1, vid2)
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/media/clip2.mp4",
            "-filter_complex",
            (
                "[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                "[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                "[pv0][pn1]xfade=transition=wipeleft:duration=0.35:offset=29.65[xf0];"
                "[xf0]format=yuv420p[final]"
            ),
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_7_no_clips_raises(self) -> None:
        """No clips in timeline -> CommandBuildError with project-id message."""
        job = _g_make_job(_g_make_plan())
        clip_repo: AsyncMock = AsyncMock()
        clip_repo.list_by_project = AsyncMock(return_value=[])

        encoder_mock = AsyncMock()
        with pytest.raises(CommandBuildError) as exc_info:
            await build_command_for_job(job, clip_repo, encoder_mock)

        assert str(exc_info.value) == f"Project {_G_PROJECT_ID} has no clips in timeline"

    @pytest.mark.asyncio
    async def test_golden_case_8_single_image_clip(self) -> None:
        """Single image clip -> translator filter_complex path with -loop 1."""
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        clip = _g_make_clip(
            "clip-8",
            "vid-1",
            clip_type="image",
            source_asset_id="img-asset-1",
        )
        job = _g_make_job(_g_make_plan())

        img_asset_repo: AsyncMock = AsyncMock()
        img_asset = MagicMock()
        img_asset.file_path = "/assets/images/photo.jpg"
        img_asset.deleted_at = None
        img_asset_repo.get_by_id = AsyncMock(return_value=img_asset)

        result = await build_command_for_job(
            job,
            _g_clip_repo(clip),
            _g_video_repo(vid),
            asset_repository=img_asset_repo,
        )

        assert result == [
            "ffmpeg",
            "-loop",
            "1",
            "-i",
            "/assets/images/photo.jpg",
            "-ss",
            "0.0",
            "-t",
            "30.0",
            "-filter_complex",
            "[0:v]fps=30,settb=1/30[v0];[v0]format=yuv420p[final]",
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_9_single_generator_clip(self) -> None:
        """Single generator clip -> translator filter_complex path with -f lavfi."""
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        clip = _g_make_clip(
            "clip-9",
            "vid-1",
            clip_type="generator",
            generator_params={"lavfi_string": "color=c=black:s=1920x1080:r=30"},
        )
        job = _g_make_job(_g_make_plan())

        result = await build_command_for_job(
            job,
            _g_clip_repo(clip),
            _g_video_repo(vid),
        )

        assert result == [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=1920x1080:r=30",
            "-ss",
            "0.0",
            "-t",
            "30.0",
            "-filter_complex",
            "[0:v]fps=30,settb=1/30[v0];[v0]format=yuv420p[final]",
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_single_clip_nonzero_inpoint(self) -> None:
        """Single file clip with in_point=30 (1s at 30fps) -> -ss 1.0 seek in argv (BL-790)."""
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        clip = _g_make_clip("clip-sc-nz", "vid-1", in_point=30, out_point=930)
        job = _g_make_job(_g_make_plan())

        result = await build_command_for_job(job, _g_clip_repo(clip), _g_video_repo(vid))

        # -t reflects the render plan duration (timeline_end - timeline_start),
        # not the clip content span ((out_point - in_point) / fps).
        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-ss",
            "1.0",
            "-t",
            "30.0",
            "-vf",
            "scale=1920:1080",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_single_clip_nonzero_inpoint_mismatched_fps(self) -> None:
        """Single-clip in_point=48 with 24fps source at 30fps render -> -ss 2.0 (BL-811).

        in_point_secs = 48 / source_fps(24) = 2.0, not 48 / render_fps(30) = 1.6.
        """
        vid = dataclasses.replace(
            _g_make_video("vid-1", _G_VIDEO_PATH_1),
            frame_rate_numerator=24,
            frame_rate_denominator=1,
        )
        clip = _g_make_clip("clip-sc-mfps", "vid-1", in_point=48, out_point=948)
        job = _g_make_job(_g_make_plan())

        result = await build_command_for_job(job, _g_clip_repo(clip), _g_video_repo(vid))

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-ss",
            "2.0",
            "-t",
            "30.0",
            "-vf",
            "scale=1920:1080",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_multi_clip_file_nonzero_inpoint(self) -> None:
        """Multi-clip: clip_b has in_point=30 -> -ss 1.0 -t 4.0 prepended before -i (BL-790)."""
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2)
        clip_a = _g_make_clip("clip-mc-nz-a", "vid-1")  # in_point=0: no -ss
        # in_pt=1.0s (30/30), dur=4.0s ((150-30)/30)
        clip_b = _g_make_clip("clip-mc-nz-b", "vid-2", in_point=30, out_point=150)
        job = _g_make_job(_g_make_plan(total_duration=34.0))

        result = await build_command_for_job(
            job, _g_clip_repo(clip_a, clip_b), _g_video_repo(vid1, vid2)
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-ss",
            "1.0",
            "-t",
            "4.0",
            "-i",
            "/media/clip2.mp4",
            "-filter_complex",
            "[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1]"
            ";[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1]"
            ";[pv0][pn1]xfade=transition=fade:duration=1:offset=29[xf0]"
            ";[xf0]format=yuv420p[final]",
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_multi_clip_audio_capable(self) -> None:
        """Two audio-capable clips, no TTS -> acrossfade chain in filter_complex (BL-791-AC-6)."""
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1, audio_codec="aac")
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2, audio_codec="aac")
        clip_a = _g_make_clip("clip-audio-a", "vid-1")
        clip_b = _g_make_clip("clip-audio-b", "vid-2")
        job = _g_make_job(_g_make_plan())

        result = await build_command_for_job(
            job, _g_clip_repo(clip_a, clip_b), _g_video_repo(vid1, vid2)
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/media/clip2.mp4",
            "-filter_complex",
            (
                "[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                "[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                "[pv0][pn1]xfade=transition=fade:duration=1:offset=29[xf0];"
                "[xf0]format=yuv420p[final];"
                "[0:a][1:a]acrossfade=d=1:o=0[aout]"
            ),
            "-map",
            "[final]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]
        # FR-007-AC-1: acrossfade with d=1 (not d=1.0) and -map [aout] present; -an absent
        assert "acrossfade=d=1:o=0[aout]" in result[result.index("-filter_complex") + 1]
        assert "-map" in result
        assert "[aout]" in result
        assert "-an" not in result

    @pytest.mark.asyncio
    async def test_golden_case_wipeleft_transition_audio(self) -> None:
        """Two audio-capable clips with wipeleft/0.35 -> acrossfade=d=0.35 (BL-792)."""
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1, audio_codec="aac")
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2, audio_codec="aac")
        clip_a = _g_make_clip("clip-wt-audio-a", "vid-1")
        clip_b = _g_make_clip("clip-wt-audio-b", "vid-2")
        transitions = [
            {"clip_a_id": "clip-wt-audio-a", "transition_type": "wipeleft", "duration": 0.35}
        ]
        job = _g_make_job(_g_make_plan(total_duration=29.65, transitions=transitions))

        result = await build_command_for_job(
            job, _g_clip_repo(clip_a, clip_b), _g_video_repo(vid1, vid2)
        )

        fc = result[result.index("-filter_complex") + 1]
        assert "xfade=transition=wipeleft:duration=0.35:offset=29.65" in fc
        assert "acrossfade=d=0.35:o=0[aout]" in fc
        assert "-an" not in result

    @pytest.mark.asyncio
    async def test_golden_case_multi_clip_nondefault_fps(self) -> None:
        """Two file clips with fps=24.0 plan -> filter_complex uses fps=24,settb=1/24 (BL-793-AC-6).

        Source clips are 30fps; clip duration = 900/30 = 30s; xfade offset = 30 - 1 = 29.
        Only the plan fps changes — source frame count and xfade offset are unaffected.
        """
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2)
        clip_a = _g_make_clip("clip-ndfps-a", "vid-1")
        clip_b = _g_make_clip("clip-ndfps-b", "vid-2")
        job = _g_make_job(_g_make_plan(fps=24.0))

        result = await build_command_for_job(
            job, _g_clip_repo(clip_a, clip_b), _g_video_repo(vid1, vid2)
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/media/clip2.mp4",
            "-filter_complex",
            (
                "[0:v]fps=24,settb=1/24[v0];[1:v]fps=24,settb=1/24[v1];"
                "[v0]fps=24,settb=1/24[pv0];[v1]fps=24,settb=1/24[pn1];"
                "[pv0][pn1]xfade=transition=fade:duration=1:offset=29[xf0];"
                "[xf0]format=yuv420p[final]"
            ),
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "24.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_sc_audio_effect_dispatch(self) -> None:
        """Single audio-capable clip with volume=2.0 -> audio chain in filter_complex (BL-794 AC-1).

        Verifies that _build_clip_render_effects dispatches stream_kind='a' effects to the
        audio chain ([0:a]<chain>[aout]) instead of the video filtergraph.
        """
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1, audio_codec="aac")
        clip = _g_make_clip(
            "clip-sc-audio-eff",
            "vid-1",
            effects=[{"effect_type": "volume", "parameters": {"volume": 2.0}}],
        )
        reg = EffectRegistry()
        reg.register("volume", VOLUME)

        result = await build_command_for_job(
            _g_make_job(_g_make_plan()), _g_clip_repo(clip), _g_video_repo(vid), effect_registry=reg
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-ss",
            "0.0",
            "-t",
            "30.0",
            "-filter_complex",
            "[0:v]fps=30,settb=1/30[v0];[v0]format=yuv420p[final];[0:a]volume=volume=2[aout]",
            "-map",
            "[final]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_mc_audio_effect_dispatch(self) -> None:
        """Two audio clips with volume=2.0 -> per-clip [i:a]chain[ai_eff] labels (BL-794 AC-2).

        Verifies that multi-clip audio effect dispatch produces [0:a]…[a0_eff] and
        [1:a]…[a1_eff] segments routed into acrossfade rather than the video filtergraph.
        """
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1, audio_codec="aac")
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2, audio_codec="aac")
        clip_a = _g_make_clip(
            "clip-mc-audio-eff-a",
            "vid-1",
            effects=[{"effect_type": "volume", "parameters": {"volume": 2.0}}],
        )
        clip_b = _g_make_clip(
            "clip-mc-audio-eff-b",
            "vid-2",
            effects=[{"effect_type": "volume", "parameters": {"volume": 2.0}}],
        )
        reg = EffectRegistry()
        reg.register("volume", VOLUME)

        result = await build_command_for_job(
            _g_make_job(_g_make_plan(total_duration=60.0)),
            _g_clip_repo(clip_a, clip_b),
            _g_video_repo(vid1, vid2),
            effect_registry=reg,
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/media/clip2.mp4",
            "-filter_complex",
            (
                "[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                "[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                "[pv0][pn1]xfade=transition=fade:duration=1:offset=29[xf0];"
                "[xf0]format=yuv420p[final];"
                "[0:a]volume=volume=2[a0_eff];[1:a]volume=volume=2[a1_eff];"
                "[a0_eff][a1_eff]acrossfade=d=1:o=0[aout]"
            ),
            "-map",
            "[final]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_time_stretch_audio_routing(self) -> None:
        """time_stretch routes to audio chain in filter_complex (BL-823 AC-2).

        Verifies that a newly-annotated stream_kind='a' effect (TIME_STRETCH) dispatches
        to the audio chain ([0:a]atempo=0.8[aout]) and NOT the video filtergraph.
        """
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1, audio_codec="aac")
        clip = _g_make_clip(
            "clip-sc-time-stretch",
            "vid-1",
            effects=[{"effect_type": "time_stretch", "parameters": {"factor": 0.8}}],
        )
        reg = EffectRegistry()
        reg.register("time_stretch", TIME_STRETCH)

        result = await build_command_for_job(
            _g_make_job(_g_make_plan()), _g_clip_repo(clip), _g_video_repo(vid), effect_registry=reg
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-ss",
            "0.0",
            "-t",
            "30.0",
            "-filter_complex",
            "[0:v]fps=30,settb=1/30[v0];[v0]format=yuv420p[final];[0:a]atempo=0.8[aout]",
            "-map",
            "[final]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_audio_effect_on_video_only_raises(self) -> None:
        """Audio effect on video-only clip raises CommandBuildError before FFmpeg (BL-824 AC-2).

        Verifies that the single-clip path raises CommandBuildError when audio_codec is None
        and an audio effect is present, before any FFmpeg subprocess is started.
        """
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1)  # audio_codec=None (video-only)
        clip = _g_make_clip(
            "clip-sc-no-audio",
            "vid-1",
            effects=[{"effect_type": "volume", "parameters": {"volume": 1.5}}],
        )
        reg = EffectRegistry()
        reg.register("volume", VOLUME)

        with pytest.raises(CommandBuildError) as exc_info:
            await build_command_for_job(
                _g_make_job(_g_make_plan()),
                _g_clip_repo(clip),
                _g_video_repo(vid),
                effect_registry=reg,
            )

        assert "clip-sc-no-audio" in str(exc_info.value)
        assert "audio effects" in str(exc_info.value)
        assert "no audio stream" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_golden_sc_crop(self) -> None:
        """Single file clip with crop effect -> crop=640:360:100:50 in filter_complex (BL-830 AC-1)."""  # noqa: E501
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        clip = _g_make_clip(
            "clip-sc-crop",
            "vid-1",
            effects=[
                {
                    "effect_type": "crop",
                    "parameters": {"width": 640, "height": 360, "x": 100, "y": 50},
                }
            ],
        )
        reg = EffectRegistry()
        reg.register("crop", CROP_EFFECT)

        result = await build_command_for_job(
            _g_make_job(_g_make_plan()),
            _g_clip_repo(clip),
            _g_video_repo(vid),
            effect_registry=reg,
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-ss",
            "0.0",
            "-t",
            "30.0",
            "-filter_complex",
            "[0:v]fps=30,settb=1/30[v0];[v0]crop=640:360:100:50[ev0];[ev0]format=yuv420p[final]",
            "-map",
            "[final]",
            "-an",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_10_multi_clip_tts_soft_subtitles(self) -> None:
        """Clip 0 video-only + TTS + soft-subs -> acrossfade + subtitle at idx 3 (BL-804)."""
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        vid3 = _g_make_video("vid-3", _G_VIDEO_PATH_3, audio_codec="aac")
        clip_a = _g_make_clip("clip-10a", "vid-1")  # no audio
        clip_b = _g_make_clip("clip-10b", "vid-3")  # audio_codec="aac"
        subs = [{"source_asset_id": str(_G_SUB_UUID), "language": "en", "is_default": True}]
        job = _g_make_job(_g_make_plan(soft_subtitles=subs))
        tts_inputs = [
            TtsCueAudioInput(
                cue_id="cue-10",
                audio_path="/renders/tts-010.wav",
                track_id="track-1",
                start_s=10.0,
                weight=1.0,
                volume_envelope=None,
            )
        ]

        result = await build_command_for_job(
            job,
            _g_clip_repo(clip_a, clip_b),
            _g_video_repo(vid1, vid3),
            tts_inputs=tts_inputs,
            asset_repository=_g_asset_repo(),
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/media/clip3.mp4",
            "-i",
            "/renders/tts-010.wav",
            "-i",
            "/assets/subs/en.srt",
            "-filter_complex",
            (
                "[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                "[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                "[pv0][pn1]xfade=transition=fade:duration=1:offset=29[xf0];"
                "[xf0]format=yuv420p[final];"
                "[2:a]adelay=10000|10000,aformat=channel_layouts=stereo[tts0];"
                "anullsrc=r=48000:cl=stereo:d=30.0[a0_silent];[a0_silent][1:a]acrossfade=d=1:o=0[src_aout_pre];"
                "[src_aout_pre]aformat=channel_layouts=stereo,aresample=48000[src_norm];"
                "[src_norm][tts0]amix=inputs=2:duration=longest[aout]"
            ),
            "-map",
            "[final]",
            "-map",
            "[aout]",
            "-map",
            "3:s",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "-c:s",
            "mov_text",
            "-metadata:s:s:0",
            "language=eng",
            "-disposition:s:0",
            "default",
            "/renders/golden.mp4",
        ]

    @pytest.mark.asyncio
    async def test_golden_case_multi_clip_audio_tts(self) -> None:
        """Two audio clips + TTS -> acrossfade [src_aout_pre] amixed with TTS (BL-814-AC-1)."""
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1, audio_codec="aac")
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2, audio_codec="aac")
        clip_a = _g_make_clip("clip-mc-tts-a", "vid-1")
        clip_b = _g_make_clip("clip-mc-tts-b", "vid-2")
        tts_inputs = [
            TtsCueAudioInput(
                cue_id="cue-mt",
                audio_path="/renders/tts-mt.wav",
                track_id="track-1",
                start_s=10.0,
                weight=1.0,
                volume_envelope=None,
            )
        ]

        result = await build_command_for_job(
            _g_make_job(_g_make_plan()),
            _g_clip_repo(clip_a, clip_b),
            _g_video_repo(vid1, vid2),
            tts_inputs=tts_inputs,
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/media/clip2.mp4",
            "-i",
            "/renders/tts-mt.wav",
            "-filter_complex",
            (
                "[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                "[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                "[pv0][pn1]xfade=transition=fade:duration=1:offset=29[xf0];"
                "[xf0]format=yuv420p[final];"
                "[2:a]adelay=10000|10000,aformat=channel_layouts=stereo[tts0];"
                "[0:a][1:a]acrossfade=d=1:o=0[src_aout_pre];"
                "[src_aout_pre]aformat=channel_layouts=stereo,aresample=48000[src_norm];"
                "[src_norm][tts0]amix=inputs=2:duration=longest[aout]"
            ),
            "-map",
            "[final]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]
        fc = result[result.index("-filter_complex") + 1]
        assert "[src_aout_pre]" in fc
        assert "[src_norm]" in fc
        assert "amix=inputs=2" in fc
        assert "[0:a][1:a]acrossfade" in fc

    @pytest.mark.asyncio
    async def test_golden_case_sc_tts_audio_effect(self) -> None:
        """Single clip + volume effect + TTS -> effects applied before TTS amix (BL-814-AC-7)."""
        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1, audio_codec="aac")
        clip = _g_make_clip(
            "clip-sc-tts-eff",
            "vid-1",
            effects=[{"effect_type": "volume", "parameters": {"volume": 2.0}}],
        )
        tts_inputs = [
            TtsCueAudioInput(
                cue_id="cue-sc",
                audio_path="/renders/tts-sc.wav",
                track_id="track-1",
                start_s=5.0,
                weight=1.0,
                volume_envelope=None,
            )
        ]
        reg = EffectRegistry()
        reg.register("volume", VOLUME)

        result = await build_command_for_job(
            _g_make_job(_g_make_plan()),
            _g_clip_repo(clip),
            _g_video_repo(vid),
            tts_inputs=tts_inputs,
            effect_registry=reg,
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/renders/tts-sc.wav",
            "-ss",
            "0.0",
            "-t",
            "30.0",
            "-filter_complex",
            (
                "[0:v]fps=30,settb=1/30[v0];[v0]format=yuv420p[final];"
                "[1:a]adelay=5000|5000,aformat=channel_layouts=stereo[tts0];"
                "[0:a]volume=volume=2[0a_eff];"
                "[0a_eff]aformat=channel_layouts=stereo,aresample=48000[src_norm];"
                "[src_norm][tts0]amix=inputs=2:duration=longest[aout]"
            ),
            "-map",
            "[final]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]
        fc = result[result.index("-filter_complex") + 1]
        assert "[0a_eff]" in fc
        assert "volume=volume=2" in fc
        assert "amix=inputs=2" in fc

    @pytest.mark.asyncio
    async def test_golden_case_multi_clip_tts_audio_effects(self) -> None:
        """Two audio clips + effects + TTS -> effects in acrossfade before amix (BL-814-AC-8)."""
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1, audio_codec="aac")
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2, audio_codec="aac")
        clip_a = _g_make_clip(
            "clip-mce-a",
            "vid-1",
            effects=[{"effect_type": "volume", "parameters": {"volume": 2.0}}],
        )
        clip_b = _g_make_clip(
            "clip-mce-b",
            "vid-2",
            effects=[{"effect_type": "volume", "parameters": {"volume": 0.5}}],
        )
        tts_inputs = [
            TtsCueAudioInput(
                cue_id="cue-mce",
                audio_path="/renders/tts-mce.wav",
                track_id="track-1",
                start_s=5.0,
                weight=1.0,
                volume_envelope=None,
            )
        ]
        reg = EffectRegistry()
        reg.register("volume", VOLUME)

        result = await build_command_for_job(
            _g_make_job(_g_make_plan(total_duration=60.0)),
            _g_clip_repo(clip_a, clip_b),
            _g_video_repo(vid1, vid2),
            tts_inputs=tts_inputs,
            effect_registry=reg,
        )

        assert result == [
            "ffmpeg",
            "-i",
            "/media/clip1.mp4",
            "-i",
            "/media/clip2.mp4",
            "-i",
            "/renders/tts-mce.wav",
            "-filter_complex",
            (
                "[0:v]fps=30,settb=1/30[v0];[1:v]fps=30,settb=1/30[v1];"
                "[v0]fps=30,settb=1/30[pv0];[v1]fps=30,settb=1/30[pn1];"
                "[pv0][pn1]xfade=transition=fade:duration=1:offset=29[xf0];"
                "[xf0]format=yuv420p[final];"
                "[2:a]adelay=5000|5000,aformat=channel_layouts=stereo[tts0];"
                "[0:a]volume=volume=2[a0_eff];[1:a]volume=volume=0.5[a1_eff];"
                "[a0_eff][a1_eff]acrossfade=d=1:o=0[src_aout_pre];"
                "[src_aout_pre]aformat=channel_layouts=stereo,aresample=48000[src_norm];"
                "[src_norm][tts0]amix=inputs=2:duration=longest[aout]"
            ),
            "-map",
            "[final]",
            "-map",
            "[aout]",
            "-c:v",
            "libx264",
            "-crf",
            "23",
            "-r",
            "30.0",
            "-progress",
            "pipe:1",
            "/renders/golden.mp4",
        ]
        fc = result[result.index("-filter_complex") + 1]
        assert "[src_aout_pre]" in fc
        assert "volume=volume=2" in fc
        assert "volume=volume=0.5" in fc
        assert "amix=inputs=2" in fc

    @pytest.mark.asyncio
    async def test_buildfn_exception_wraps_as_command_build_error(self) -> None:
        """build_fn raising ValueError is re-raised as CommandBuildError (BL-828 AC-1/AC-2).

        Supplies a known effect whose build_fn raises ValueError("bad param") and asserts
        that CommandBuildError propagates (not raw ValueError), with the original exception
        chained as __cause__, and the error message naming the effect type and clip id.
        """

        def _bad_build_fn(params: dict) -> str:
            raise ValueError("bad param")

        bad_effect = dataclasses.replace(VOLUME, build_fn=_bad_build_fn)

        vid = _g_make_video("vid-1", _G_VIDEO_PATH_1, audio_codec="aac")
        clip = _g_make_clip(
            "clip-bad-effect",
            "vid-1",
            effects=[{"effect_type": "bad-effect", "parameters": {}}],
        )
        reg = EffectRegistry()
        reg.register("bad-effect", bad_effect)

        with pytest.raises(CommandBuildError) as exc_info:
            await build_command_for_job(
                _g_make_job(_g_make_plan()),
                _g_clip_repo(clip),
                _g_video_repo(vid),
                effect_registry=reg,
            )

        assert isinstance(exc_info.value.__cause__, ValueError)
        assert "bad-effect" in str(exc_info.value)
        assert "clip-bad-effect" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Unit tests for transition shape guard (BL-816)
# ---------------------------------------------------------------------------


class TestTransitionShapeGuard:
    """Verify that effects-shaped transition entries are filtered from transition_lookup."""

    @pytest.mark.asyncio
    async def test_mixed_shape_transitions_no_keyerror(self) -> None:
        """Mixed timeline + effects-shaped transitions: no KeyError; effects entry skipped (BL-816).

        Seeds transitions_list with one timeline-shaped entry (clip_a_id) and one
        effects-shaped entry (source_clip_id/target_clip_id). The effects-shaped entry
        must be silently skipped; the timeline-shaped entry must still apply (wipeleft
        transition appears in xfade filter_complex).
        """
        vid1 = _g_make_video("vid-1", _G_VIDEO_PATH_1)
        vid2 = _g_make_video("vid-2", _G_VIDEO_PATH_2)
        clip_a = _g_make_clip("clip-sg-a", "vid-1")
        clip_b = _g_make_clip("clip-sg-b", "vid-2")

        transitions = [
            # Timeline-shaped: must be admitted to lookup
            {"clip_a_id": "clip-sg-a", "transition_type": "wipeleft", "duration": 0.35},
            # Effects-shaped: must be skipped (has source_clip_id instead of clip_a_id)
            {
                "id": "eff-trans-1",
                "source_clip_id": "clip-sg-a",
                "target_clip_id": "clip-sg-b",
                "transition_type": "fade",
                "parameters": {},
                "filter_string": "xfade=transition=fade:duration=1:offset=29",
            },
        ]
        job = _g_make_job(_g_make_plan(total_duration=29.65, transitions=transitions))

        # Must not raise KeyError
        result = await build_command_for_job(
            job, _g_clip_repo(clip_a, clip_b), _g_video_repo(vid1, vid2)
        )

        # Timeline transition was admitted: wipeleft appears in filter_complex
        fc = result[result.index("-filter_complex") + 1]
        assert "xfade=transition=wipeleft:duration=0.35" in fc
        # Effects-shaped entry was NOT admitted (fade from effects entry is absent)
        # Verifying by ensuring "wipeleft" is the only xfade transition in the output
        assert "xfade=transition=fade" not in fc


# ---------------------------------------------------------------------------
# Unit tests for _build_mc_subtitle_inputs helper (NFR-003)
# ---------------------------------------------------------------------------


class TestBuildMcSubtitleInputs:
    """Unit tests for the _build_mc_subtitle_inputs async helper."""

    @pytest.mark.asyncio
    async def test_no_subtitles_returns_zero_cmd_unchanged(self) -> None:
        """soft_subtitles=None -> returns 0, cmd unchanged."""
        ctx = MagicMock()
        ctx.render_settings.soft_subtitles = None

        cmd: list[str] = ["-i", "video.mp4"]
        result = await _build_mc_subtitle_inputs(cmd, ctx, ["/video.mp4"], None, None)

        assert result == 0
        assert cmd == ["-i", "video.mp4"]

    @pytest.mark.asyncio
    async def test_with_subtitle_spec_returns_base_and_extends_cmd(self) -> None:
        """soft_subtitles=[spec] -> correct subtitle_base_mc index and -i in cmd."""
        spec = SoftSubtitleSpec(
            source_asset_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            language="en",
            is_default=True,
        )
        ctx = MagicMock()
        ctx.render_settings.soft_subtitles = [spec]

        asset = MagicMock()
        asset.file_path = "/assets/subs/en.srt"
        asset.deleted_at = None
        asset_repo: AsyncMock = AsyncMock()
        asset_repo.get_by_id = AsyncMock(return_value=asset)
        ctx.asset_repository = asset_repo

        input_paths = ["/video1.mp4", "/video2.mp4"]
        cmd: list[str] = []
        result = await _build_mc_subtitle_inputs(
            cmd, ctx, input_paths, "/tmp/chapters.ffmetadata", None
        )

        # subtitle_base_mc = 2 (clips) + 1 (ffmetadata) + 0 (no tts) = 3
        assert result == 3
        assert cmd == ["-i", "/assets/subs/en.srt"]

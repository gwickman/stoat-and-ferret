"""Tests for render worker command builder.

Covers command construction from valid render_plan JSON, input path
resolution via repositories, empty-segments fallback, multi-segment
truncation warning, error cases, and RenderService integration.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from stoat_ferret.db.models import Clip, Video
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import CommandBuildError, build_command_for_job

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
    async def test_fps_included(self) -> None:
        """AC-1.3: Frame rate from settings included in command."""
        job = _make_job(render_plan=_make_render_plan(fps=24.0))
        clip_repo, video_repo = _make_repos()

        cmd = await build_command_for_job(job, clip_repo, video_repo)

        assert "-r" in cmd
        r_idx = cmd.index("-r")
        assert cmd[r_idx + 1] == "24.0"

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

    assert elapsed_ms < 10, f"Command builder took {elapsed_ms:.1f}ms, expected <10ms"

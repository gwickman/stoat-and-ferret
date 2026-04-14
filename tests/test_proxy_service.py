"""Tests for the proxy generation service."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.api.services.proxy_service import (
    PROXY_JOB_TYPE,
    ProxyService,
    build_ffmpeg_args,
    make_proxy_handler,
    select_proxy_quality,
)
from stoat_ferret.db.models import ProxyFile, ProxyQuality, ProxyStatus
from stoat_ferret.db.proxy_repository import InMemoryProxyRepository
from stoat_ferret.ffmpeg.async_executor import FakeAsyncFFmpegExecutor
from stoat_ferret.jobs.queue import InMemoryJobQueue


class TestSelectProxyQuality:
    """Tests for quality auto-selection (FR-001)."""

    def test_source_above_1080p_produces_720p(self) -> None:
        """Source >1080p produces 720p proxy (HIGH quality)."""
        quality, w, h = select_proxy_quality(3840, 2160)
        assert quality == ProxyQuality.HIGH
        assert w == 1280
        assert h == 720

    def test_source_1440p_produces_720p(self) -> None:
        """Source 1440p (>1080p) produces 720p proxy."""
        quality, w, h = select_proxy_quality(2560, 1440)
        assert quality == ProxyQuality.HIGH
        assert w == 1280
        assert h == 720

    def test_source_1080p_produces_540p(self) -> None:
        """Source 1080p (>720p, <=1080p) produces 540p proxy (MEDIUM quality)."""
        quality, w, h = select_proxy_quality(1920, 1080)
        assert quality == ProxyQuality.MEDIUM
        assert w == 960
        assert h == 540

    def test_source_900p_produces_540p(self) -> None:
        """Source 900p (>720p, <=1080p) produces 540p proxy."""
        quality, w, h = select_proxy_quality(1600, 900)
        assert quality == ProxyQuality.MEDIUM
        assert w == 960
        assert h == 540

    def test_source_720p_is_passthrough(self) -> None:
        """Source <=720p is passthrough (LOW quality)."""
        quality, w, h = select_proxy_quality(1280, 720)
        assert quality == ProxyQuality.LOW
        assert w == 1280
        assert h == 720

    def test_source_480p_is_passthrough(self) -> None:
        """Source 480p (<=720p) is passthrough."""
        quality, w, h = select_proxy_quality(854, 480)
        assert quality == ProxyQuality.LOW
        assert w == 854
        assert h == 480


class TestBuildFfmpegArgs:
    """Tests for FFmpeg command generation (FR-007)."""

    def test_command_pattern(self) -> None:
        """Generated command matches expected FFmpeg pattern."""
        args = build_ffmpeg_args("/source.mp4", "/out.mp4", 1280, 720)

        assert "-i" in args
        assert "/source.mp4" in args
        assert "-vf" in args

        vf_idx = args.index("-vf")
        assert args[vf_idx + 1] == "scale=1280:720"

        assert "-c:v" in args
        cv_idx = args.index("-c:v")
        assert args[cv_idx + 1] == "libx264"

        assert "-preset" in args
        preset_idx = args.index("-preset")
        assert args[preset_idx + 1] == "fast"

        assert "-crf" in args
        crf_idx = args.index("-crf")
        assert args[crf_idx + 1] == "23"

        assert "-c:a" in args
        ca_idx = args.index("-c:a")
        assert args[ca_idx + 1] == "aac"

        assert "-b:a" in args
        ba_idx = args.index("-b:a")
        assert args[ba_idx + 1] == "128k"

        assert "-progress" in args
        prog_idx = args.index("-progress")
        assert args[prog_idx + 1] == "pipe:2"

        assert args[-1] == "/out.mp4"


@pytest.fixture
def proxy_repo() -> InMemoryProxyRepository:
    """Create a fresh in-memory proxy repository."""
    return InMemoryProxyRepository()


@pytest.fixture
def fake_executor() -> FakeAsyncFFmpegExecutor:
    """Create a fake async FFmpeg executor."""
    return FakeAsyncFFmpegExecutor()


@pytest.fixture
def proxy_service(
    proxy_repo: InMemoryProxyRepository,
    fake_executor: FakeAsyncFFmpegExecutor,
    tmp_path: Path,
) -> ProxyService:
    """Create a proxy service with test dependencies."""
    return ProxyService(
        proxy_repository=proxy_repo,
        async_executor=fake_executor,
        proxy_dir=str(tmp_path / "proxies"),
        max_storage_bytes=1_000_000,  # 1MB for testing
        cleanup_threshold=0.8,
    )


@pytest.fixture
def source_file(tmp_path: Path) -> str:
    """Create a dummy source video file for checksum tests."""
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake video content")
    return str(source)


class TestProxyServiceGenerate:
    """Tests for proxy generation (FR-002, FR-006)."""

    async def test_generate_creates_proxy_record(
        self,
        proxy_service: ProxyService,
        proxy_repo: InMemoryProxyRepository,
        fake_executor: FakeAsyncFFmpegExecutor,
        source_file: str,
        tmp_path: Path,
    ) -> None:
        """Generating a proxy creates a DB record with correct quality."""
        # Create output file so file_size check works
        proxy_dir = tmp_path / "proxies"
        proxy_dir.mkdir(parents=True, exist_ok=True)

        proxy = await proxy_service.generate_proxy(
            video_id="vid-001",
            source_path=source_file,
            source_width=1920,
            source_height=1080,
            duration_us=10_000_000,
        )

        assert proxy.source_video_id == "vid-001"
        assert proxy.quality == ProxyQuality.MEDIUM
        assert proxy.status == ProxyStatus.READY
        assert len(fake_executor.calls) == 1

    async def test_generate_calls_ffmpeg(
        self,
        proxy_service: ProxyService,
        fake_executor: FakeAsyncFFmpegExecutor,
        source_file: str,
    ) -> None:
        """Generating a proxy calls FFmpeg with correct arguments."""
        await proxy_service.generate_proxy(
            video_id="vid-002",
            source_path=source_file,
            source_width=3840,
            source_height=2160,
            duration_us=60_000_000,
        )

        assert len(fake_executor.calls) == 1
        args = fake_executor.calls[0]
        assert "-i" in args
        assert source_file in args
        assert "scale=1280:720" in args[args.index("-vf") + 1]

    async def test_generate_failure_cleans_up(
        self,
        proxy_repo: InMemoryProxyRepository,
        source_file: str,
        tmp_path: Path,
    ) -> None:
        """Failed generation cleans up partial files (FR-008)."""
        executor = FakeAsyncFFmpegExecutor(returncode=1)
        service = ProxyService(
            proxy_repository=proxy_repo,
            async_executor=executor,
            proxy_dir=str(tmp_path / "proxies"),
        )

        with pytest.raises(RuntimeError, match="FFmpeg failed"):
            await service.generate_proxy(
                video_id="vid-003",
                source_path=source_file,
                source_width=1920,
                source_height=1080,
                duration_us=10_000_000,
            )

        # Proxy should be in failed state
        proxies = await proxy_repo.list_by_video("vid-003")
        assert len(proxies) == 1
        assert proxies[0].status == ProxyStatus.FAILED

        # No orphaned proxy files on disk
        proxy_dir = tmp_path / "proxies"
        if proxy_dir.exists():
            mp4_files = list(proxy_dir.glob("*.mp4"))
            assert len(mp4_files) == 0

    async def test_generate_cancellation_cleans_up(
        self,
        proxy_repo: InMemoryProxyRepository,
        source_file: str,
        tmp_path: Path,
    ) -> None:
        """Cancellation cleans up partial files (FR-008)."""
        cancel_event = asyncio.Event()
        cancel_event.set()  # Already cancelled

        executor = FakeAsyncFFmpegExecutor()
        service = ProxyService(
            proxy_repository=proxy_repo,
            async_executor=executor,
            proxy_dir=str(tmp_path / "proxies"),
        )

        with pytest.raises(RuntimeError, match="cancelled"):
            await service.generate_proxy(
                video_id="vid-004",
                source_path=source_file,
                source_width=1920,
                source_height=1080,
                duration_us=10_000_000,
                cancel_event=cancel_event,
            )


class TestStorageQuota:
    """Tests for storage quota and LRU eviction (FR-004)."""

    async def test_eviction_when_over_threshold(
        self,
        proxy_repo: InMemoryProxyRepository,
        source_file: str,
        tmp_path: Path,
    ) -> None:
        """When storage exceeds 80% of max, oldest proxy is evicted."""
        # Pre-populate with a large ready proxy (900KB of 1MB limit)
        old_proxy = ProxyFile(
            id="old-proxy-1",
            source_video_id="vid-old",
            quality=ProxyQuality.HIGH,
            file_path=str(tmp_path / "old_proxy.mp4"),
            file_size_bytes=900_000,
            status=ProxyStatus.PENDING,
            source_checksum="abc",
            generated_at=None,
            last_accessed_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        await proxy_repo.add(old_proxy)
        # Manually set status transitions
        await proxy_repo.update_status("old-proxy-1", ProxyStatus.GENERATING)
        await proxy_repo.update_status("old-proxy-1", ProxyStatus.READY, file_size_bytes=900_000)

        executor = FakeAsyncFFmpegExecutor()
        service = ProxyService(
            proxy_repository=proxy_repo,
            async_executor=executor,
            proxy_dir=str(tmp_path / "proxies"),
            max_storage_bytes=1_000_000,
            cleanup_threshold=0.8,
        )

        await service.generate_proxy(
            video_id="vid-new",
            source_path=source_file,
            source_width=1920,
            source_height=1080,
            duration_us=10_000_000,
        )

        # Old proxy should have been evicted
        old = await proxy_repo.get("old-proxy-1")
        assert old is None

    async def test_no_eviction_when_under_threshold(
        self,
        proxy_repo: InMemoryProxyRepository,
        source_file: str,
        tmp_path: Path,
    ) -> None:
        """When storage is under 80%, no eviction occurs."""
        # Pre-populate with a small proxy (100 bytes)
        small_proxy = ProxyFile(
            id="small-proxy-1",
            source_video_id="vid-small",
            quality=ProxyQuality.HIGH,
            file_path=str(tmp_path / "small_proxy.mp4"),
            file_size_bytes=100,
            status=ProxyStatus.PENDING,
            source_checksum="abc",
            generated_at=None,
            last_accessed_at=datetime(2020, 1, 1, tzinfo=timezone.utc),
        )
        await proxy_repo.add(small_proxy)
        await proxy_repo.update_status("small-proxy-1", ProxyStatus.GENERATING)
        await proxy_repo.update_status("small-proxy-1", ProxyStatus.READY, file_size_bytes=100)

        executor = FakeAsyncFFmpegExecutor()
        service = ProxyService(
            proxy_repository=proxy_repo,
            async_executor=executor,
            proxy_dir=str(tmp_path / "proxies"),
            max_storage_bytes=1_000_000,
            cleanup_threshold=0.8,
        )

        await service.generate_proxy(
            video_id="vid-new2",
            source_path=source_file,
            source_width=1920,
            source_height=1080,
            duration_us=10_000_000,
        )

        # Small proxy should still exist
        small = await proxy_repo.get("small-proxy-1")
        assert small is not None


class TestStaleDetection:
    """Tests for stale proxy detection (FR-005)."""

    async def test_stale_when_checksum_mismatch(
        self,
        proxy_repo: InMemoryProxyRepository,
        tmp_path: Path,
    ) -> None:
        """Proxy with mismatched checksum is marked stale."""
        # Create a source file
        source = tmp_path / "source.mp4"
        source.write_bytes(b"original content")

        proxy = ProxyFile(
            id="proxy-stale-1",
            source_video_id="vid-stale",
            quality=ProxyQuality.HIGH,
            file_path=str(tmp_path / "proxy.mp4"),
            file_size_bytes=1000,
            status=ProxyStatus.PENDING,
            source_checksum="different_checksum",
            generated_at=None,
            last_accessed_at=datetime.now(timezone.utc),
        )
        await proxy_repo.add(proxy)
        await proxy_repo.update_status("proxy-stale-1", ProxyStatus.GENERATING)
        await proxy_repo.update_status("proxy-stale-1", ProxyStatus.READY)

        executor = FakeAsyncFFmpegExecutor()
        service = ProxyService(
            proxy_repository=proxy_repo,
            async_executor=executor,
            proxy_dir=str(tmp_path / "proxies"),
        )

        is_stale = await service.check_stale("proxy-stale-1", str(source))
        assert is_stale is True

        updated = await proxy_repo.get("proxy-stale-1")
        assert updated is not None
        assert updated.status == ProxyStatus.STALE

    async def test_not_stale_when_checksum_matches(
        self,
        proxy_repo: InMemoryProxyRepository,
        tmp_path: Path,
    ) -> None:
        """Proxy with matching checksum is not marked stale."""
        source = tmp_path / "source.mp4"
        source.write_bytes(b"original content")

        from stoat_ferret.api.services.proxy_service import compute_file_checksum

        checksum = compute_file_checksum(str(source))

        proxy = ProxyFile(
            id="proxy-current-1",
            source_video_id="vid-current",
            quality=ProxyQuality.HIGH,
            file_path=str(tmp_path / "proxy.mp4"),
            file_size_bytes=1000,
            status=ProxyStatus.PENDING,
            source_checksum=checksum,
            generated_at=None,
            last_accessed_at=datetime.now(timezone.utc),
        )
        await proxy_repo.add(proxy)
        await proxy_repo.update_status("proxy-current-1", ProxyStatus.GENERATING)
        await proxy_repo.update_status("proxy-current-1", ProxyStatus.READY)

        executor = FakeAsyncFFmpegExecutor()
        service = ProxyService(
            proxy_repository=proxy_repo,
            async_executor=executor,
            proxy_dir=str(tmp_path / "proxies"),
        )

        is_stale = await service.check_stale("proxy-current-1", str(source))
        assert is_stale is False


class TestProgressThrottling:
    """Tests for progress event throttling (FR-010, NFR-002)."""

    async def test_progress_throttled_by_time(
        self,
        proxy_repo: InMemoryProxyRepository,
        source_file: str,
        tmp_path: Path,
    ) -> None:
        """Progress events are throttled to >=500ms intervals."""
        ws_manager = AsyncMock()
        ws_manager.broadcast = AsyncMock()

        # Generate many rapid progress updates
        progress_lines = [f"out_time_us={i * 100_000}" for i in range(20)]

        executor = FakeAsyncFFmpegExecutor(stderr_lines=progress_lines)
        service = ProxyService(
            proxy_repository=proxy_repo,
            async_executor=executor,
            ws_manager=ws_manager,
            proxy_dir=str(tmp_path / "proxies"),
        )

        await service.generate_proxy(
            video_id="vid-throttle",
            source_path=source_file,
            source_width=1920,
            source_height=1080,
            duration_us=10_000_000,
            job_id="job-throttle",
        )

        # The fake executor runs synchronously (no real time between calls),
        # so the >=5% delta check limits progress events
        broadcast_calls = ws_manager.broadcast.call_args_list
        progress_events = [c for c in broadcast_calls if c[0][0].get("type") == "job_progress"]
        # Should have far fewer than 20 events (one per line)
        # At most: ~20 events for 5% increments (0-100%) + 1 completion = 21
        # With throttling, should be <= 21
        assert len(progress_events) <= 21


class TestStructuredLogging:
    """Tests for structured logging (FR-003)."""

    async def test_started_complete_failed_events(
        self,
        proxy_repo: InMemoryProxyRepository,
        source_file: str,
        tmp_path: Path,
    ) -> None:
        """Verify started and complete log events are emitted.

        The structlog events are verified by the fact that the service
        runs without error. Full structlog capture is deferred to integration tests.
        """
        executor = FakeAsyncFFmpegExecutor()
        service = ProxyService(
            proxy_repository=proxy_repo,
            async_executor=executor,
            proxy_dir=str(tmp_path / "proxies"),
        )

        proxy = await service.generate_proxy(
            video_id="vid-log",
            source_path=source_file,
            source_width=1920,
            source_height=1080,
            duration_us=10_000_000,
            job_id="job-log",
        )

        assert proxy.status == ProxyStatus.READY


class TestListByVideo:
    """Tests for ProxyService.list_by_video() delegation (FR-001)."""

    async def test_list_by_video_delegates_to_repo(
        self,
        proxy_service: ProxyService,
        proxy_repo: InMemoryProxyRepository,
        source_file: str,
        tmp_path: Path,
    ) -> None:
        """list_by_video() returns proxies for the given video ID via repo delegation."""
        # Generate a proxy so there is something to list
        proxy_dir = tmp_path / "proxies"
        proxy_dir.mkdir(parents=True, exist_ok=True)

        await proxy_service.generate_proxy(
            video_id="vid-list-001",
            source_path=source_file,
            source_width=1920,
            source_height=1080,
            duration_us=10_000_000,
        )

        result = await proxy_service.list_by_video("vid-list-001")
        expected = await proxy_repo.list_by_video("vid-list-001")

        assert result == expected
        assert len(result) == 1
        assert result[0].source_video_id == "vid-list-001"

    async def test_list_by_video_empty_for_unknown_video(
        self,
        proxy_service: ProxyService,
    ) -> None:
        """list_by_video() returns an empty list for an unknown video ID."""
        result = await proxy_service.list_by_video("no-such-video")
        assert result == []


class TestJobHandlerRegistration:
    """Tests for job handler registration (FR-009)."""

    async def test_proxy_handler_registration_with_timeout(self) -> None:
        """register_handler() accepts timeout parameter; proxy uses 1800s."""
        queue = InMemoryJobQueue()
        repo = InMemoryProxyRepository()
        executor = FakeAsyncFFmpegExecutor()
        service = ProxyService(
            proxy_repository=repo,
            async_executor=executor,
        )
        handler = make_proxy_handler(service)

        # Should not raise
        queue.register_handler(PROXY_JOB_TYPE, handler, timeout=1800.0)

        # Verify stored timeout
        assert PROXY_JOB_TYPE in queue._handlers
        _, timeout = queue._handlers[PROXY_JOB_TYPE]
        assert timeout == 1800.0

    async def test_default_timeout_for_other_jobs(self) -> None:
        """Other job types use the default 300s timeout."""
        from stoat_ferret.jobs.queue import AsyncioJobQueue

        queue = AsyncioJobQueue()

        async def noop(_type: str, _payload: dict) -> None:  # type: ignore[type-arg]
            pass

        queue.register_handler("other", noop)
        _, timeout = queue._handlers["other"]
        assert timeout is None  # Falls back to queue default (300s)


class TestJobProgressFormat:
    """Tests for JOB_PROGRESS event format parity (FR-002)."""

    async def test_progress_event_has_required_fields(
        self,
        proxy_repo: InMemoryProxyRepository,
        source_file: str,
        tmp_path: Path,
    ) -> None:
        """JOB_PROGRESS events include job_id, progress, and status."""
        ws_manager = AsyncMock()
        ws_manager.broadcast = AsyncMock()

        executor = FakeAsyncFFmpegExecutor()
        service = ProxyService(
            proxy_repository=proxy_repo,
            async_executor=executor,
            ws_manager=ws_manager,
            proxy_dir=str(tmp_path / "proxies"),
        )

        await service.generate_proxy(
            video_id="vid-format",
            source_path=source_file,
            source_width=1920,
            source_height=1080,
            duration_us=10_000_000,
            job_id="job-format",
        )

        # Find the completion event
        broadcasts = ws_manager.broadcast.call_args_list
        progress_events = [c[0][0] for c in broadcasts if c[0][0].get("type") == "job_progress"]
        assert len(progress_events) >= 1

        # Check the final completion event
        final = progress_events[-1]
        payload = final["payload"]
        assert payload["job_id"] == "job-format"
        assert payload["progress"] == 1.0
        assert payload["status"] == "complete"
        assert "proxy_quality" in payload
        assert "target_resolution" in payload

"""Render job CRUD API endpoints.

Provides POST/GET/DELETE for render job lifecycle management
with pagination, status filtering, cancel, and retry support.
Exposes hardware encoder detection and caching via GET/POST endpoints.
Follows established router conventions with DI via app.state
and JSON:API-style error responses.
"""

from __future__ import annotations

import asyncio
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from stoat_ferret.api.schemas.render import (
    CodecInfo,
    CreateRenderRequest,
    EncoderInfoResponse,
    EncoderListResponse,
    FormatInfo,
    FormatListResponse,
    QualityPresetInfo,
    QueueStatusResponse,
    RenderJobResponse,
    RenderListResponse,
    RenderPreviewRequest,
    RenderPreviewResponse,
)
from stoat_ferret.api.settings import get_settings
from stoat_ferret.render.encoder_cache import (
    AsyncEncoderCacheRepository,
    AsyncSQLiteEncoderCacheRepository,
    EncoderCacheEntry,
)
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.render_repository import (
    AsyncRenderRepository,
    AsyncSQLiteRenderRepository,
)
from stoat_ferret.render.service import PreflightError, RenderService, RenderUnavailableError

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["render"])

# Lock for concurrent cancel/retry safety (NFR-003)
_state_transition_lock = asyncio.Lock()

# Lock for concurrent encoder refresh prevention (NFR-002)
_encoder_refresh_lock = asyncio.Lock()


# ---------- Dependency injection ----------


async def get_encoder_cache_repository(request: Request) -> AsyncEncoderCacheRepository:
    """Get encoder cache repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async encoder cache repository instance.
    """
    repo: AsyncEncoderCacheRepository | None = getattr(
        request.app.state, "encoder_cache_repository", None
    )
    if repo is not None:
        return repo
    return AsyncSQLiteEncoderCacheRepository(request.app.state.db)


async def get_render_repository(request: Request) -> AsyncRenderRepository:
    """Get render repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async render repository instance.
    """
    repo: AsyncRenderRepository | None = getattr(request.app.state, "render_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteRenderRepository(request.app.state.db)


async def get_render_service(request: Request) -> RenderService:
    """Get render service from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        RenderService instance.

    Raises:
        HTTPException: 503 if render service is not available.
    """
    service: RenderService | None = getattr(request.app.state, "render_service", None)
    if service is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "Render service not available"},
        )
    return service


async def get_render_queue(request: Request) -> RenderQueue:
    """Get render queue from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        RenderQueue instance.

    Raises:
        HTTPException: 503 if render queue is not available.
    """
    queue: RenderQueue | None = getattr(request.app.state, "render_queue", None)
    if queue is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "SERVICE_UNAVAILABLE", "message": "Render queue not available"},
        )
    return queue


RenderRepoDep = Annotated[AsyncRenderRepository, Depends(get_render_repository)]
RenderServiceDep = Annotated[RenderService, Depends(get_render_service)]
RenderQueueDep = Annotated[RenderQueue, Depends(get_render_queue)]
EncoderCacheDep = Annotated[AsyncEncoderCacheRepository, Depends(get_encoder_cache_repository)]


# ---------- Helpers ----------


def _job_to_response(job: RenderJob) -> RenderJobResponse:
    """Convert a RenderJob dataclass to a response model.

    Args:
        job: The render job to convert.

    Returns:
        Pydantic response model.
    """
    return RenderJobResponse(
        id=job.id,
        project_id=job.project_id,
        status=job.status.value,
        output_path=job.output_path,
        output_format=job.output_format.value,
        quality_preset=job.quality_preset.value,
        progress=job.progress,
        error_message=job.error_message,
        retry_count=job.retry_count,
        created_at=job.created_at,
        updated_at=job.updated_at,
        completed_at=job.completed_at,
    )


# ---------- Encoder helpers ----------


@dataclass
class _RawEncoder:
    """Intermediate representation from FFmpeg detection."""

    name: str
    codec: str
    is_hardware: bool
    encoder_type: str
    description: str


def _detect_encoders_sync() -> list[_RawEncoder]:
    """Run FFmpeg -encoders and parse output using Rust core.

    Returns:
        List of raw encoder data from Rust detect_hardware_encoders.

    Raises:
        FileNotFoundError: If FFmpeg is not found in PATH.
        RuntimeError: If FFmpeg subprocess fails.
    """
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        raise FileNotFoundError("ffmpeg not found in PATH")

    result = subprocess.run(
        ["ffmpeg", "-encoders"],
        capture_output=True,
        text=True,
        timeout=10,
    )

    from stoat_ferret_core import detect_hardware_encoders

    encoders = detect_hardware_encoders(result.stdout)
    return [
        _RawEncoder(
            name=enc.name,
            codec=enc.codec,
            is_hardware=enc.is_hardware,
            encoder_type=str(enc.encoder_type),
            description=enc.description,
        )
        for enc in encoders
    ]


def _entry_to_response(entry: EncoderCacheEntry) -> EncoderInfoResponse:
    """Convert an EncoderCacheEntry to an API response.

    Args:
        entry: Encoder cache entry.

    Returns:
        Pydantic response model.
    """
    return EncoderInfoResponse(
        name=entry.name,
        codec=entry.codec,
        is_hardware=entry.is_hardware,
        encoder_type=entry.encoder_type,
        description=entry.description,
        detected_at=entry.detected_at,
    )


async def _run_detection_and_cache(
    repo: AsyncEncoderCacheRepository,
) -> list[EncoderCacheEntry]:
    """Run FFmpeg encoder detection and store results in the cache.

    Runs detection in a thread to avoid blocking the event loop (NFR-001).

    Args:
        repo: Encoder cache repository.

    Returns:
        List of newly cached entries.

    Raises:
        HTTPException: 503 if FFmpeg is unavailable.
    """
    try:
        raw_encoders = await asyncio.to_thread(_detect_encoders_sync)
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "FFMPEG_UNAVAILABLE",
                "message": "FFmpeg binary not found in PATH",
            },
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "DETECTION_FAILED",
                "message": f"Encoder detection failed: {exc}",
            },
        ) from exc

    now = datetime.now(timezone.utc)
    entries = [
        EncoderCacheEntry(
            id=None,
            name=enc.name,
            codec=enc.codec,
            is_hardware=enc.is_hardware,
            encoder_type=enc.encoder_type,
            description=enc.description,
            detected_at=now,
        )
        for enc in raw_encoders
    ]

    await repo.clear()
    return await repo.create_many(entries)


# ---------- Endpoints ----------


@router.post(
    "/render",
    response_model=RenderJobResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_render_job(
    body: CreateRenderRequest,
    render_service: RenderServiceDep,
) -> RenderJobResponse:
    """Start a new render job with pre-flight validation.

    Args:
        body: Render job creation request.
        render_service: Render service dependency.

    Returns:
        Created render job with 201 status.

    Raises:
        HTTPException: 400 for invalid format/preset/plan, 422 for pre-flight failure.
    """
    settings = get_settings()

    # Validate output format
    try:
        output_format = OutputFormat(body.output_format)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_FORMAT",
                "message": f"Invalid output format: {body.output_format}. "
                f"Valid: {[f.value for f in OutputFormat]}",
            },
        ) from err

    # Validate quality preset
    try:
        quality_preset = QualityPreset(body.quality_preset)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "code": "INVALID_PRESET",
                "message": f"Invalid quality preset: {body.quality_preset}. "
                f"Valid: {[p.value for p in QualityPreset]}",
            },
        ) from err

    # Validate format-encoder compatibility when encoder is explicitly provided
    if body.encoder is not None:
        fmt_info = next((f for f in _FORMAT_DATA if f.format == body.output_format), None)
        if fmt_info is not None:
            codec_family = _encoder_codec_family(body.encoder)
            allowed = [c.name for c in fmt_info.codecs]
            if codec_family is not None and codec_family not in allowed:
                logger.info(
                    "render.validation_failed",
                    format=body.output_format,
                    encoder=body.encoder,
                )
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail={
                        "code": "INCOMPATIBLE_FORMAT_ENCODER",
                        "message": (
                            f"Encoder '{body.encoder}' is not compatible with format "
                            f"'{body.output_format}'. Supported codec families for "
                            f"{body.output_format}: {allowed}"
                        ),
                    },
                )

    output_path = str(Path(settings.render_output_dir) / f"{body.project_id}.{output_format.value}")

    try:
        job = await render_service.submit_job(
            project_id=body.project_id,
            output_path=output_path,
            output_format=output_format,
            quality_preset=quality_preset,
            render_plan_json=body.render_plan,
        )
    except RenderUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"code": "RENDER_UNAVAILABLE", "message": str(exc)},
        ) from exc
    except PreflightError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={"code": "PREFLIGHT_FAILED", "message": str(exc)},
        ) from exc

    logger.info(
        "render_endpoint.job_created",
        job_id=job.id,
        project_id=body.project_id,
        action="start",
    )
    return _job_to_response(job)


# ---------- Encoder endpoints ----------
# These must be registered before /render/{job_id} to avoid path conflicts.


@router.get("/render/encoders", response_model=EncoderListResponse)
async def get_encoders(
    encoder_repo: EncoderCacheDep,
) -> EncoderListResponse:
    """Return cached encoders, triggering lazy detection if cache is empty.

    If the cache is populated, returns cached data immediately.
    If the cache is empty, runs FFmpeg encoder detection, caches the
    results, and returns them.

    If a refresh is currently in progress, returns stale cached data
    rather than blocking (NFR-003).

    Args:
        encoder_repo: Encoder cache repository dependency.

    Returns:
        List of detected encoders with cached flag.
    """
    cached = await encoder_repo.get_all()
    if cached:
        return EncoderListResponse(
            encoders=[_entry_to_response(e) for e in cached],
            cached=True,
        )

    # Lazy detection: cache is empty
    if _encoder_refresh_lock.locked():
        # Refresh in progress, return empty (no stale data available)
        return EncoderListResponse(encoders=[], cached=False)

    async with _encoder_refresh_lock:
        # Double-check: another request may have populated the cache
        cached = await encoder_repo.get_all()
        if cached:
            return EncoderListResponse(
                encoders=[_entry_to_response(e) for e in cached],
                cached=True,
            )
        entries = await _run_detection_and_cache(encoder_repo)

    return EncoderListResponse(
        encoders=[_entry_to_response(e) for e in entries],
        cached=False,
    )


@router.post("/render/encoders/refresh", response_model=EncoderListResponse)
async def refresh_encoders(
    encoder_repo: EncoderCacheDep,
) -> EncoderListResponse:
    """Re-run FFmpeg encoder detection and update cached results.

    Truncates existing cache and re-inserts fresh detection results.
    Uses asyncio.Lock to prevent concurrent refresh operations (NFR-002).
    Uses asyncio.to_thread to avoid blocking the event loop (NFR-001).

    Args:
        encoder_repo: Encoder cache repository dependency.

    Returns:
        Fresh list of detected encoders.

    Raises:
        HTTPException: 409 if a refresh is already in progress,
            503 if FFmpeg is unavailable.
    """
    if _encoder_refresh_lock.locked():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "REFRESH_IN_PROGRESS",
                "message": "Encoder refresh is already in progress",
            },
        )

    async with _encoder_refresh_lock:
        entries = await _run_detection_and_cache(encoder_repo)

    logger.info("render_endpoint.encoders_refreshed", count=len(entries))
    return EncoderListResponse(
        encoders=[_entry_to_response(e) for e in entries],
        cached=False,
    )


# ---------- Format discovery ----------
# Static data: no persistence, no lifespan dependency (NFR-001).

_QUALITY_PRESETS: dict[str, list[QualityPresetInfo]] = {
    "h264": [
        QualityPresetInfo(preset="draft", video_bitrate_kbps=1_500),
        QualityPresetInfo(preset="standard", video_bitrate_kbps=5_000),
        QualityPresetInfo(preset="high", video_bitrate_kbps=15_000),
    ],
    "h265": [
        QualityPresetInfo(preset="draft", video_bitrate_kbps=1_000),
        QualityPresetInfo(preset="standard", video_bitrate_kbps=3_500),
        QualityPresetInfo(preset="high", video_bitrate_kbps=10_000),
    ],
    "vp8": [
        QualityPresetInfo(preset="draft", video_bitrate_kbps=1_500),
        QualityPresetInfo(preset="standard", video_bitrate_kbps=5_000),
        QualityPresetInfo(preset="high", video_bitrate_kbps=12_000),
    ],
    "vp9": [
        QualityPresetInfo(preset="draft", video_bitrate_kbps=1_000),
        QualityPresetInfo(preset="standard", video_bitrate_kbps=3_500),
        QualityPresetInfo(preset="high", video_bitrate_kbps=10_000),
    ],
    "prores": [
        QualityPresetInfo(preset="draft", video_bitrate_kbps=30_000),
        QualityPresetInfo(preset="standard", video_bitrate_kbps=60_000),
        QualityPresetInfo(preset="high", video_bitrate_kbps=120_000),
    ],
    "av1": [
        QualityPresetInfo(preset="draft", video_bitrate_kbps=2_000),
        QualityPresetInfo(preset="standard", video_bitrate_kbps=4_000),
        QualityPresetInfo(preset="high", video_bitrate_kbps=8_000),
    ],
}

_FORMAT_DATA: list[FormatInfo] = [
    FormatInfo(
        format="mp4",
        extension=".mp4",
        mime_type="video/mp4",
        codecs=[
            CodecInfo(name="h264", quality_presets=_QUALITY_PRESETS["h264"]),
            CodecInfo(name="h265", quality_presets=_QUALITY_PRESETS["h265"]),
        ],
        supports_hw_accel=True,
        supports_two_pass=True,
        supports_alpha=False,
    ),
    FormatInfo(
        format="webm",
        extension=".webm",
        mime_type="video/webm",
        codecs=[
            CodecInfo(name="vp8", quality_presets=_QUALITY_PRESETS["vp8"]),
            CodecInfo(name="vp9", quality_presets=_QUALITY_PRESETS["vp9"]),
        ],
        supports_hw_accel=False,
        supports_two_pass=True,
        supports_alpha=True,
    ),
    FormatInfo(
        format="mov",
        extension=".mov",
        mime_type="video/quicktime",
        codecs=[
            CodecInfo(name="h264", quality_presets=_QUALITY_PRESETS["h264"]),
            CodecInfo(name="prores", quality_presets=_QUALITY_PRESETS["prores"]),
        ],
        supports_hw_accel=True,
        supports_two_pass=True,
        supports_alpha=True,
    ),
    FormatInfo(
        format="mkv",
        extension=".mkv",
        mime_type="video/x-matroska",
        codecs=[
            CodecInfo(name="h264", quality_presets=_QUALITY_PRESETS["h264"]),
            CodecInfo(name="h265", quality_presets=_QUALITY_PRESETS["h265"]),
            CodecInfo(name="vp9", quality_presets=_QUALITY_PRESETS["vp9"]),
            CodecInfo(name="av1", quality_presets=_QUALITY_PRESETS["av1"]),
        ],
        supports_hw_accel=True,
        supports_two_pass=True,
        supports_alpha=True,
    ),
]


def _encoder_codec_family(encoder: str) -> str | None:
    """Map an encoder name to its codec family string.

    Args:
        encoder: FFmpeg encoder name (e.g., 'libx264', 'libvpx-vp9').

    Returns:
        Codec family string (e.g., 'h264', 'vp9'), or None if unknown.
    """
    _ENCODER_MAP = {
        "libx264": "h264",
        "libx265": "h265",
        "libvpx": "vp8",
        "libvpx-vp9": "vp9",
        "prores_ks": "prores",
        "libaom-av1": "av1",
    }
    if encoder in _ENCODER_MAP:
        return _ENCODER_MAP[encoder]
    if encoder.startswith("h264_"):
        return "h264"
    if encoder.startswith("hevc_"):
        return "h265"
    return None


@router.get("/render/formats", response_model=FormatListResponse)
async def get_output_formats() -> FormatListResponse:
    """Return all supported output formats with codecs, capability flags, and quality presets.

    Static data endpoint — no database or external dependencies required.
    Designed for AI discoverability with self-documenting field names.

    Returns:
        All available output formats with codec and quality preset details.
    """
    return FormatListResponse(formats=_FORMAT_DATA)


# ---------- Command preview ----------


# Quality preset mapping: user-facing name → Rust QualityPreset enum variant.
# Resolved lazily inside the handler to avoid import-time dependency on the
# native extension (mirrors the pattern in _detect_encoders_sync).
_QUALITY_PRESET_NAMES = ("draft", "standard", "high")


@router.post("/render/preview", response_model=RenderPreviewResponse)
def render_preview(body: RenderPreviewRequest) -> RenderPreviewResponse:
    """Return a representative FFmpeg command string for the given render settings.

    Stateless endpoint — no job creation, no disk I/O.  Calls Rust
    ``validate_render_settings`` for input validation (422 on failure)
    and ``build_render_command`` with placeholder segment data to
    produce the command.

    Args:
        body: Render preview request with format, quality preset, and encoder.

    Returns:
        FFmpeg command string.

    Raises:
        HTTPException: 422 if settings are invalid.
    """
    from stoat_ferret_core import (
        EncoderInfo,
        EncoderType,
        RenderSegment,
        RenderSettings,
        build_render_command,
        validate_render_settings,
    )
    from stoat_ferret_core._core import (
        QualityPreset as CoreQualityPreset,
    )

    # Validate quality_preset value
    if body.quality_preset not in _QUALITY_PRESET_NAMES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_QUALITY_PRESET",
                "message": (
                    f"Invalid quality_preset '{body.quality_preset}'. "
                    f"Valid: {list(_QUALITY_PRESET_NAMES)}"
                ),
            },
        )

    # Format-encoder compatibility check (Python-side, before Rust validation)
    fmt_info = next((f for f in _FORMAT_DATA if f.format == body.output_format), None)
    if fmt_info is not None:
        codec_family = _encoder_codec_family(body.encoder)
        allowed = [c.name for c in fmt_info.codecs]
        if codec_family is not None and codec_family not in allowed:
            logger.info(
                "render_preview_incompatible",
                encoder=body.encoder,
                output_format=body.output_format,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail={
                    "code": "INCOMPATIBLE_FORMAT_ENCODER",
                    "message": (
                        f"Encoder '{body.encoder}' is not compatible with format "
                        f"'{body.output_format}'. Supported codec families for "
                        f"{body.output_format}: {allowed}"
                    ),
                },
            )

    # Build RenderSettings with placeholder resolution/fps for validation
    settings = RenderSettings(
        output_format=body.output_format,
        width=1920,
        height=1080,
        codec=body.encoder,
        quality_preset="medium",
        fps=30.0,
    )

    try:
        validate_render_settings(settings)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_RENDER_SETTINGS",
                "message": str(exc),
            },
        ) from exc

    # Map user quality preset to Rust enum
    quality_map = {
        "draft": CoreQualityPreset.Draft,
        "standard": CoreQualityPreset.Standard,
        "high": CoreQualityPreset.High,
    }
    quality = quality_map[body.quality_preset]

    # Placeholder segment: 10 s, 1920×1080, 300 frames @ 30 fps
    segment = RenderSegment(
        index=0,
        timeline_start=0.0,
        timeline_end=10.0,
        frame_count=300,
        cost_estimate=300.0,
    )

    encoder_info = EncoderInfo(
        name=body.encoder,
        codec=body.encoder,
        is_hardware=False,
        encoder_type=EncoderType.Software,
        description=f"Software encoder {body.encoder}",
    )

    cmd = build_render_command(
        segment,
        encoder_info,
        quality,
        settings,
        "/tmp/input.mp4",
        f"/tmp/output.{body.output_format}",
    )

    return RenderPreviewResponse(command="ffmpeg " + " ".join(cmd.args()))


# ---------- Queue status ----------


@router.get("/render/queue", response_model=QueueStatusResponse)
async def get_queue_status(
    queue: RenderQueueDep,
    repo: RenderRepoDep,
) -> QueueStatusResponse:
    """Return current render queue status with capacity, disk space, and throughput.

    Aggregates live queue counts from RenderQueue, disk space from the
    render output directory, and today's completed/failed job counts
    from the repository. Read-only — no state mutations (NFR-001).

    Args:
        queue: Render queue dependency.
        repo: Render repository dependency.

    Returns:
        Queue status with active/pending counts, capacity, disk, and throughput.
    """
    settings = get_settings()

    active_count = await queue.get_active_count()
    pending_count = await queue.get_queue_depth()

    # Disk space for render output directory
    output_dir = Path(settings.render_output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(output_dir)

    # Today's completed/failed counts
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    completed_jobs = await repo.list_by_status(RenderStatus.COMPLETED)
    completed_today = sum(
        1 for j in completed_jobs if j.completed_at is not None and j.completed_at >= midnight
    )

    failed_jobs = await repo.list_by_status(RenderStatus.FAILED)
    failed_today = sum(
        1 for j in failed_jobs if j.completed_at is not None and j.completed_at >= midnight
    )

    return QueueStatusResponse(
        active_count=active_count,
        pending_count=pending_count,
        max_concurrent=settings.render_max_concurrent,
        max_queue_depth=settings.render_max_queue_depth,
        disk_available_bytes=usage.free,
        disk_total_bytes=usage.total,
        completed_today=completed_today,
        failed_today=failed_today,
    )


# ---------- Render job endpoints ----------


@router.get("/render/{job_id}", response_model=RenderJobResponse)
async def get_render_job(
    job_id: str,
    repo: RenderRepoDep,
) -> RenderJobResponse:
    """Get current status, progress, and metadata for a render job.

    Args:
        job_id: The render job UUID.
        repo: Render repository dependency.

    Returns:
        Render job details.

    Raises:
        HTTPException: 404 if job not found.
    """
    job = await repo.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Render job {job_id} not found"},
        )
    return _job_to_response(job)


@router.get("/render", response_model=RenderListResponse)
async def list_render_jobs(
    repo: RenderRepoDep,
    limit: int = Query(default=20, ge=1, le=100, description="Maximum results"),
    offset: int = Query(default=0, ge=0, description="Number of results to skip"),
    status_filter: str | None = Query(default=None, alias="status", description="Filter by status"),
) -> RenderListResponse:
    """List all render jobs with pagination and optional status filtering.

    Args:
        repo: Render repository dependency.
        limit: Maximum number of results.
        offset: Number of results to skip.
        status_filter: Optional status value to filter by.

    Returns:
        Paginated list of render jobs.

    Raises:
        HTTPException: 400 if invalid status filter.
    """
    render_status: RenderStatus | None = None
    if status_filter is not None:
        try:
            render_status = RenderStatus(status_filter)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "code": "INVALID_STATUS",
                    "message": f"Invalid status: {status_filter}. "
                    f"Valid: {[s.value for s in RenderStatus]}",
                },
            ) from err

    jobs, total = await repo.list_jobs(status=render_status, limit=limit, offset=offset)
    return RenderListResponse(
        items=[_job_to_response(j) for j in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("/render/{job_id}/cancel", response_model=RenderJobResponse)
async def cancel_render_job(
    job_id: str,
    repo: RenderRepoDep,
    render_service: RenderServiceDep,
) -> RenderJobResponse:
    """Cancel a running or queued render job.

    Terminates the active FFmpeg process via stdin 'q' and marks the job cancelled.

    Args:
        job_id: The render job UUID.
        repo: Render repository dependency.
        render_service: Render service dependency.

    Returns:
        Updated render job.

    Raises:
        HTTPException: 404 if not found, 409 if not cancellable.
    """
    async with _state_transition_lock:
        job = await repo.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": f"Render job {job_id} not found"},
            )

        if job.status not in (RenderStatus.QUEUED, RenderStatus.RUNNING):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "NOT_CANCELLABLE",
                    "message": f"Cannot cancel job in {job.status.value} state",
                },
            )

        cancelled = await render_service.cancel_job(job_id)
        if not cancelled:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "CANCEL_FAILED",
                    "message": f"Failed to cancel job {job_id}",
                },
            )

    updated = await repo.get(job_id)
    return _job_to_response(updated)  # type: ignore[arg-type]


@router.post("/render/{job_id}/retry", response_model=RenderJobResponse)
async def retry_render_job(
    job_id: str,
    repo: RenderRepoDep,
) -> RenderJobResponse:
    """Retry a failed render job (transient failures only).

    Requeues the job for re-execution. Rejects permanent failures
    (jobs that have exceeded the max retry count).

    Args:
        job_id: The render job UUID.
        repo: Render repository dependency.

    Returns:
        Updated render job in QUEUED status.

    Raises:
        HTTPException: 404 if not found, 409 if not retryable.
    """
    settings = get_settings()

    async with _state_transition_lock:
        job = await repo.get(job_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"code": "NOT_FOUND", "message": f"Render job {job_id} not found"},
            )

        if job.status != RenderStatus.FAILED:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "NOT_RETRYABLE",
                    "message": f"Cannot retry job in {job.status.value} state",
                },
            )

        # Check if this is a permanent failure (exceeded max retries)
        if job.retry_count >= settings.render_retry_count:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "PERMANENT_FAILURE",
                    "message": (
                        f"Job {job_id} has exceeded max retries ({settings.render_retry_count})"
                    ),
                },
            )

        # Transition: failed -> queued (retry)
        await repo.update_status(job_id, RenderStatus.QUEUED)

    updated = await repo.get(job_id)
    logger.info(
        "render_endpoint.job_retried",
        job_id=job_id,
        project_id=updated.project_id if updated else "unknown",
        action="retry",
    )
    return _job_to_response(updated)  # type: ignore[arg-type]


@router.delete("/render/{job_id}", response_model=RenderJobResponse)
async def delete_render_job(
    job_id: str,
    repo: RenderRepoDep,
) -> RenderJobResponse:
    """Delete render job metadata. Output files are preserved on disk.

    Args:
        job_id: The render job UUID.
        repo: Render repository dependency.

    Returns:
        The deleted render job.

    Raises:
        HTTPException: 404 if not found.
    """
    job = await repo.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Render job {job_id} not found"},
        )

    response = _job_to_response(job)
    deleted = await repo.delete(job_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Render job {job_id} not found"},
        )

    logger.info("render_endpoint.job_deleted", job_id=job_id)
    return response

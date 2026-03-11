"""Timeline endpoints for track and clip management."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from stoat_ferret.api.schemas.timeline import (
    AdjustedClipPosition,
    TimelineClipCreate,
    TimelineClipResponse,
    TimelineClipUpdate,
    TimelineResponse,
    TrackCreate,
    TrackResponse,
    TransitionCreate,
    TransitionResponse,
)
from stoat_ferret.db.clip_repository import AsyncClipRepository, AsyncSQLiteClipRepository
from stoat_ferret.db.models import Track
from stoat_ferret.db.project_repository import (
    AsyncProjectRepository,
    AsyncSQLiteProjectRepository,
)
from stoat_ferret.db.timeline_repository import (
    AsyncSQLiteTimelineRepository,
    AsyncTimelineRepository,
)

router = APIRouter(prefix="/api/v1/projects", tags=["timeline"])


# ---------------------------------------------------------------------------
# Dependency injection
# ---------------------------------------------------------------------------


async def get_timeline_repository(request: Request) -> AsyncTimelineRepository:
    """Get timeline repository from app state.

    Returns an injected repository if one was provided to create_app(),
    otherwise constructs a SQLite repository from the database connection.

    Args:
        request: The FastAPI request object.

    Returns:
        Async timeline repository instance.
    """
    repo: AsyncTimelineRepository | None = getattr(request.app.state, "timeline_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteTimelineRepository(request.app.state.db)


async def get_project_repository(request: Request) -> AsyncProjectRepository:
    """Get project repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async project repository instance.
    """
    repo: AsyncProjectRepository | None = getattr(request.app.state, "project_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteProjectRepository(request.app.state.db)


async def get_clip_repository(request: Request) -> AsyncClipRepository:
    """Get clip repository from app state.

    Args:
        request: The FastAPI request object.

    Returns:
        Async clip repository instance.
    """
    repo: AsyncClipRepository | None = getattr(request.app.state, "clip_repository", None)
    if repo is not None:
        return repo
    return AsyncSQLiteClipRepository(request.app.state.db)


# Type aliases for dependencies
TimelineRepoDep = Annotated[AsyncTimelineRepository, Depends(get_timeline_repository)]
ProjectRepoDep = Annotated[AsyncProjectRepository, Depends(get_project_repository)]
ClipRepoDep = Annotated[AsyncClipRepository, Depends(get_clip_repository)]


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _build_timeline_response(
    project_id: str,
    tracks: list[Track],
    clips_by_track: dict[str, list[TimelineClipResponse]],
) -> TimelineResponse:
    """Build a TimelineResponse from tracks and clips.

    Args:
        project_id: The project ID.
        tracks: List of Track domain objects ordered by z_index.
        clips_by_track: Mapping of track_id to list of clip responses.

    Returns:
        A complete TimelineResponse.
    """
    track_responses = []
    max_end: float = 0.0
    for track in tracks:
        track_clips = clips_by_track.get(track.id, [])
        for clip in track_clips:
            if clip.timeline_end is not None and clip.timeline_end > max_end:
                max_end = clip.timeline_end
        track_responses.append(
            TrackResponse(
                id=track.id,
                project_id=track.project_id,
                track_type=track.track_type,
                label=track.label,
                z_index=track.z_index,
                muted=track.muted,
                locked=track.locked,
                clips=track_clips,
            )
        )
    return TimelineResponse(
        project_id=project_id,
        tracks=track_responses,
        duration=max_end,
        version=1,
    )


async def _get_clips_by_track(
    clip_repo: AsyncClipRepository, project_id: str
) -> dict[str, list[TimelineClipResponse]]:
    """Get all clips for a project grouped by track_id.

    Args:
        clip_repo: Clip repository.
        project_id: The project ID.

    Returns:
        Dict mapping track_id to sorted list of TimelineClipResponse.
    """
    all_clips = await clip_repo.list_by_project(project_id)
    result: dict[str, list[TimelineClipResponse]] = {}
    for clip in all_clips:
        if clip.track_id is None:
            continue
        resp = TimelineClipResponse(
            id=clip.id,
            project_id=clip.project_id,
            source_video_id=clip.source_video_id,
            track_id=clip.track_id,
            timeline_start=clip.timeline_start,
            timeline_end=clip.timeline_end,
            in_point=clip.in_point,
            out_point=clip.out_point,
        )
        result.setdefault(clip.track_id, []).append(resp)
    # Sort clips within each track by timeline_start
    for track_id in result:
        result[track_id].sort(key=lambda c: c.timeline_start or 0.0)
    return result


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.put("/{project_id}/timeline", response_model=TimelineResponse)
async def put_timeline(
    project_id: str,
    tracks_data: list[TrackCreate],
    project_repo: ProjectRepoDep,
    timeline_repo: TimelineRepoDep,
    clip_repo: ClipRepoDep,
) -> TimelineResponse:
    """Create or replace timeline tracks for a project.

    Replaces all existing tracks with the provided list.

    Args:
        project_id: The unique project identifier.
        tracks_data: List of track creation requests.
        project_repo: Project repository dependency.
        timeline_repo: Timeline repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        Full timeline response with tracks, clips, and duration.

    Raises:
        HTTPException: 404 if project not found.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    # Delete existing tracks
    existing_tracks = await timeline_repo.get_tracks_by_project(project_id)
    for track in existing_tracks:
        await timeline_repo.delete_track(track.id)

    # Create new tracks with auto-assigned z_index where needed
    new_tracks: list[Track] = []
    for i, td in enumerate(tracks_data):
        track = Track(
            id=Track.new_id(),
            project_id=project_id,
            track_type=td.track_type,
            label=td.label,
            z_index=td.z_index if td.z_index is not None else i,
            muted=td.muted,
            locked=td.locked,
        )
        await timeline_repo.create_track(track)
        new_tracks.append(track)

    clips_by_track = await _get_clips_by_track(clip_repo, project_id)
    return _build_timeline_response(project_id, new_tracks, clips_by_track)


@router.get("/{project_id}/timeline", response_model=TimelineResponse)
async def get_timeline(
    project_id: str,
    project_repo: ProjectRepoDep,
    timeline_repo: TimelineRepoDep,
    clip_repo: ClipRepoDep,
) -> TimelineResponse:
    """Get complete timeline for a project.

    Returns tracks ordered by z_index with clips ordered by timeline_start.

    Args:
        project_id: The unique project identifier.
        project_repo: Project repository dependency.
        timeline_repo: Timeline repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        Full timeline response.

    Raises:
        HTTPException: 404 if project not found.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    tracks = await timeline_repo.get_tracks_by_project(project_id)
    clips_by_track = await _get_clips_by_track(clip_repo, project_id)
    return _build_timeline_response(project_id, tracks, clips_by_track)


@router.post(
    "/{project_id}/timeline/clips",
    response_model=TimelineClipResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_timeline_clip(
    project_id: str,
    request: TimelineClipCreate,
    project_repo: ProjectRepoDep,
    timeline_repo: TimelineRepoDep,
    clip_repo: ClipRepoDep,
) -> TimelineClipResponse:
    """Assign a clip to a timeline track with positioning.

    Args:
        project_id: The unique project identifier.
        request: Timeline clip creation request.
        project_repo: Project repository dependency.
        timeline_repo: Timeline repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        Updated clip with timeline fields.

    Raises:
        HTTPException: 404 if project, track, or clip not found.
            422 if timeline positions are invalid.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    # Verify track exists
    track = await timeline_repo.get_track(request.track_id)
    if track is None or track.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TRACK_NOT_FOUND",
                "message": f"Track {request.track_id} not found",
            },
        )

    # Verify clip exists and belongs to project
    clip = await clip_repo.get(request.clip_id)
    if clip is None or clip.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {request.clip_id} not found"},
        )

    # Validate positions
    if request.timeline_start >= request.timeline_end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_POSITION",
                "message": "timeline_start must be less than timeline_end",
            },
        )

    # Update clip with timeline fields
    clip.track_id = request.track_id
    clip.timeline_start = request.timeline_start
    clip.timeline_end = request.timeline_end
    clip.updated_at = datetime.now(timezone.utc)
    await clip_repo.update(clip)

    return TimelineClipResponse(
        id=clip.id,
        project_id=clip.project_id,
        source_video_id=clip.source_video_id,
        track_id=clip.track_id,
        timeline_start=clip.timeline_start,
        timeline_end=clip.timeline_end,
        in_point=clip.in_point,
        out_point=clip.out_point,
    )


@router.patch(
    "/{project_id}/timeline/clips/{clip_id}",
    response_model=TimelineClipResponse,
)
async def update_timeline_clip(
    project_id: str,
    clip_id: str,
    request: TimelineClipUpdate,
    project_repo: ProjectRepoDep,
    timeline_repo: TimelineRepoDep,
    clip_repo: ClipRepoDep,
) -> TimelineClipResponse:
    """Update clip timeline position or track assignment.

    Args:
        project_id: The unique project identifier.
        clip_id: The unique clip identifier.
        request: Timeline clip update request.
        project_repo: Project repository dependency.
        timeline_repo: Timeline repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        Updated clip with timeline fields.

    Raises:
        HTTPException: 404 if project, track, or clip not found.
            422 if timeline positions are invalid.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    clip = await clip_repo.get(clip_id)
    if clip is None or clip.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {clip_id} not found"},
        )

    # Validate new track_id if provided
    if request.track_id is not None:
        track = await timeline_repo.get_track(request.track_id)
        if track is None or track.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "code": "TRACK_NOT_FOUND",
                    "message": f"Track {request.track_id} not found",
                },
            )
        clip.track_id = request.track_id

    if request.timeline_start is not None:
        clip.timeline_start = request.timeline_start
    if request.timeline_end is not None:
        clip.timeline_end = request.timeline_end

    # Validate final positions
    if (
        clip.timeline_start is not None
        and clip.timeline_end is not None
        and clip.timeline_start >= clip.timeline_end
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "INVALID_POSITION",
                "message": "timeline_start must be less than timeline_end",
            },
        )

    clip.updated_at = datetime.now(timezone.utc)
    await clip_repo.update(clip)

    return TimelineClipResponse(
        id=clip.id,
        project_id=clip.project_id,
        source_video_id=clip.source_video_id,
        track_id=clip.track_id,
        timeline_start=clip.timeline_start,
        timeline_end=clip.timeline_end,
        in_point=clip.in_point,
        out_point=clip.out_point,
    )


@router.delete(
    "/{project_id}/timeline/clips/{clip_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_timeline_clip(
    project_id: str,
    clip_id: str,
    project_repo: ProjectRepoDep,
    clip_repo: ClipRepoDep,
) -> Response:
    """Remove a clip from the timeline.

    Clears the clip's timeline association (track_id, timeline_start, timeline_end)
    without deleting the clip itself.

    Args:
        project_id: The unique project identifier.
        clip_id: The unique clip identifier.
        project_repo: Project repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        Empty response with 204 status.

    Raises:
        HTTPException: 404 if project or clip not found.
    """
    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    clip = await clip_repo.get(clip_id)
    if clip is None or clip.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {clip_id} not found"},
        )

    # Clear timeline association
    clip.track_id = None
    clip.timeline_start = None
    clip.timeline_end = None
    clip.updated_at = datetime.now(timezone.utc)
    await clip_repo.update(clip)

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# POST /projects/{project_id}/timeline/transitions
# ---------------------------------------------------------------------------


@router.post(
    "/{project_id}/timeline/transitions",
    response_model=TransitionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def add_transition(
    project_id: str,
    request: TransitionCreate,
    project_repo: ProjectRepoDep,
    clip_repo: ClipRepoDep,
) -> TransitionResponse:
    """Apply a transition between two adjacent clips.

    Validates clip adjacency, delegates offset computation to Rust core's
    calculate_composition_positions(), and returns the computed filter_string
    and timeline_offset.

    Args:
        project_id: The unique project identifier.
        request: Transition creation request with clip IDs, type, and duration.
        project_repo: Project repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        Transition response with filter_string and computed timeline_offset.

    Raises:
        HTTPException: 404 if project or clips not found.
            422 if clips are not adjacent.
    """
    from stoat_ferret_core import (
        CompositionClip,
        TransitionSpec,
        TransitionType,
        build_composition_graph,
        calculate_composition_positions,
    )

    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    clip_a = await clip_repo.get(request.clip_a_id)
    if clip_a is None or clip_a.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {request.clip_a_id} not found"},
        )

    clip_b = await clip_repo.get(request.clip_b_id)
    if clip_b is None or clip_b.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Clip {request.clip_b_id} not found"},
        )

    # Validate adjacency: same track, clip_a ends where clip_b starts (or overlaps)
    if clip_a.track_id is None or clip_b.track_id is None or clip_a.track_id != clip_b.track_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "CLIPS_NOT_ADJACENT",
                "message": "Clips must be on the same track to apply a transition",
            },
        )

    if (
        clip_a.timeline_end is None
        or clip_b.timeline_start is None
        or clip_a.timeline_start is None
        or clip_b.timeline_end is None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "CLIPS_NOT_ADJACENT",
                "message": "Clips must have timeline positions to apply a transition",
            },
        )

    # Narrow types after None check above
    a_start: float = clip_a.timeline_start
    a_end: float = clip_a.timeline_end
    b_start: float = clip_b.timeline_start
    b_end: float = clip_b.timeline_end

    # Ensure clip_a comes before clip_b; swap if needed
    if a_start > b_start:
        clip_a, clip_b = clip_b, clip_a
        a_start, a_end, b_start, b_end = b_start, b_end, a_start, a_end

    if a_end != b_start:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "CLIPS_NOT_ADJACENT",
                "message": "Clips must be adjacent (clip_a must end where clip_b starts)",
            },
        )

    # Construct Rust types and call calculate_composition_positions
    comp_clip_a = CompositionClip(0, a_start, a_end, 0, 0)
    comp_clip_b = CompositionClip(1, b_start, b_end, 0, 0)
    transition_type = TransitionType.from_str(request.transition_type)
    transition_spec = TransitionSpec(transition_type, request.duration, 0.0)

    adjusted = calculate_composition_positions([comp_clip_a, comp_clip_b], [transition_spec])

    # Compute timeline_offset: the shift applied to clip_b
    timeline_offset = adjusted[1].timeline_start - comp_clip_b.timeline_start

    # Build filter graph to get filter_string
    graph = build_composition_graph(
        adjusted,
        [transition_spec],
        None,
        None,
        project.output_width,
        project.output_height,
    )
    filter_string = str(graph)

    # Store transition in project
    transition_id = str(uuid.uuid4())
    transition_data = {
        "id": transition_id,
        "clip_a_id": request.clip_a_id,
        "clip_b_id": request.clip_b_id,
        "transition_type": request.transition_type,
        "duration": request.duration,
    }
    if project.transitions is None:
        project.transitions = []
    project.transitions.append(transition_data)
    project.updated_at = datetime.now(timezone.utc)
    await project_repo.update(project)

    adjusted_positions = [
        AdjustedClipPosition(
            input_index=c.input_index,
            timeline_start=c.timeline_start,
            timeline_end=c.timeline_end,
        )
        for c in adjusted
    ]

    return TransitionResponse(
        id=transition_id,
        transition_type=request.transition_type,
        duration=request.duration,
        filter_string=filter_string,
        timeline_offset=timeline_offset,
        clips=adjusted_positions,
    )


# ---------------------------------------------------------------------------
# DELETE /projects/{project_id}/timeline/transitions/{transition_id}
# ---------------------------------------------------------------------------


@router.delete(
    "/{project_id}/timeline/transitions/{transition_id}",
    response_model=TimelineResponse,
)
async def delete_transition(
    project_id: str,
    transition_id: str,
    project_repo: ProjectRepoDep,
    timeline_repo: TimelineRepoDep,
    clip_repo: ClipRepoDep,
) -> TimelineResponse:
    """Remove a transition and recalculate timeline duration.

    Args:
        project_id: The unique project identifier.
        transition_id: The unique transition identifier.
        project_repo: Project repository dependency.
        timeline_repo: Timeline repository dependency.
        clip_repo: Clip repository dependency.

    Returns:
        Updated timeline state with recalculated duration.

    Raises:
        HTTPException: 404 if project or transition not found.
    """
    from stoat_ferret_core import (
        CompositionClip,
        TransitionSpec,
        TransitionType,
        calculate_timeline_duration,
    )

    project = await project_repo.get(project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "NOT_FOUND", "message": f"Project {project_id} not found"},
        )

    # Find and remove the transition
    if project.transitions is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Transition {transition_id} not found",
            },
        )

    original_len = len(project.transitions)
    project.transitions = [t for t in project.transitions if t.get("id") != transition_id]
    if len(project.transitions) == original_len:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Transition {transition_id} not found",
            },
        )

    project.updated_at = datetime.now(timezone.utc)
    await project_repo.update(project)

    # Recalculate timeline duration using remaining transitions
    tracks = await timeline_repo.get_tracks_by_project(project_id)
    clips_by_track = await _get_clips_by_track(clip_repo, project_id)

    # Build composition clips and remaining transition specs for duration calc
    all_comp_clips: list[CompositionClip] = []
    all_transitions: list[TransitionSpec] = []

    for track in tracks:
        track_clips = clips_by_track.get(track.id, [])
        for i, clip in enumerate(track_clips):
            if clip.timeline_start is not None and clip.timeline_end is not None:
                all_comp_clips.append(
                    CompositionClip(i, clip.timeline_start, clip.timeline_end, 0, 0)
                )

    # Build transition specs from remaining stored transitions
    for t in project.transitions:
        t_type = TransitionType.from_str(t["transition_type"])
        all_transitions.append(TransitionSpec(t_type, t["duration"], 0.0))

    # Calculate duration considering remaining transitions
    if all_comp_clips:
        duration = calculate_timeline_duration(all_comp_clips, all_transitions)
    else:
        duration = 0.0

    track_responses = []
    for track in tracks:
        track_clips = clips_by_track.get(track.id, [])
        track_responses.append(
            TrackResponse(
                id=track.id,
                project_id=track.project_id,
                track_type=track.track_type,
                label=track.label,
                z_index=track.z_index,
                muted=track.muted,
                locked=track.locked,
                clips=track_clips,
            )
        )

    return TimelineResponse(
        project_id=project_id,
        tracks=track_responses,
        duration=duration,
        version=1,
    )

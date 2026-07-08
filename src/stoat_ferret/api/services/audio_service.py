# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Audio service: DuckingPair CRUD and validation (BL-517)."""

from __future__ import annotations

from datetime import datetime, timezone

import stoat_ferret_core as sfc
from stoat_ferret.api.schemas.audio import DuckingPairCreate, DuckingPairUpdate
from stoat_ferret.db.ducking_pair_repository import AsyncDuckingPairRepository
from stoat_ferret.db.models import DuckingPair, Track


class DuckingPairService:
    """Service for DuckingPair CRUD operations.

    Validates input at the service layer in addition to the Pydantic layer.
    The Pydantic model_validator enforces ducked_track_id != sidechain_track_id
    before this service is called; this service delegates persistence to the
    repository.
    """

    def __init__(self, repository: AsyncDuckingPairRepository) -> None:
        """Initialize the service with a ducking pair repository."""
        self._repository = repository

    async def create(self, project_id: str, request: DuckingPairCreate) -> DuckingPair:
        """Create a new ducking pair for a project.

        Args:
            project_id: The owning project ID.
            request: Validated create request.

        Returns:
            The created DuckingPair.

        Raises:
            ValueError: If ducked_track_id == sidechain_track_id (redundant guard).
        """
        if request.ducked_track_id == request.sidechain_track_id:
            raise ValueError("ducked_track_id and sidechain_track_id must be different")
        now = datetime.now(timezone.utc)
        pair = DuckingPair(
            id=DuckingPair.new_id(),
            project_id=project_id,
            ducked_track_id=request.ducked_track_id,
            sidechain_track_id=request.sidechain_track_id,
            threshold=request.threshold,
            ratio=request.ratio,
            attack_ms=request.attack_ms,
            release_ms=request.release_ms,
            apply_pre_volume=request.apply_pre_volume,
            created_at=now,
            updated_at=now,
        )
        return await self._repository.create(pair)

    async def get(self, pair_id: str) -> DuckingPair | None:
        """Get a ducking pair by its ID."""
        return await self._repository.get(pair_id)

    async def list_by_project(self, project_id: str) -> list[DuckingPair]:
        """List all ducking pairs for a project."""
        return await self._repository.list_by_project(project_id)

    async def update(self, pair_id: str, request: DuckingPairUpdate) -> DuckingPair | None:
        """Update mutable fields of a ducking pair.

        Args:
            pair_id: The ducking pair ID.
            request: Validated update request.

        Returns:
            The updated DuckingPair, or None if not found.
        """
        pair = await self._repository.get(pair_id)
        if pair is None:
            return None
        now = datetime.now(timezone.utc)
        updated = DuckingPair(
            id=pair.id,
            project_id=pair.project_id,
            ducked_track_id=pair.ducked_track_id,
            sidechain_track_id=pair.sidechain_track_id,
            threshold=request.threshold if request.threshold is not None else pair.threshold,
            ratio=request.ratio if request.ratio is not None else pair.ratio,
            attack_ms=request.attack_ms if request.attack_ms is not None else pair.attack_ms,
            release_ms=request.release_ms if request.release_ms is not None else pair.release_ms,
            apply_pre_volume=(
                request.apply_pre_volume
                if request.apply_pre_volume is not None
                else pair.apply_pre_volume
            ),
            created_at=pair.created_at,
            updated_at=now,
        )
        return await self._repository.update(updated)

    async def delete(self, pair_id: str) -> bool:
        """Delete a ducking pair by its ID."""
        return await self._repository.delete(pair_id)


def assemble_multi_track_mixer(
    tracks: list[Track],
    ducking_pairs: list[DuckingPair],
) -> str:
    """Build an FFmpeg filter_complex string for multi-track audio mixing.

    Maps project tracks to stream indices in the order supplied. Only tracks
    with ``track_type == "audio"`` are admitted; non-audio tracks are skipped
    silently. Ducking pairs are resolved by track ID to stream indices inside
    the filtered list.

    Args:
        tracks: Ordered list of Track objects from the project.
        ducking_pairs: DuckingPair rows for the project; may be empty.

    Returns:
        FFmpeg filter_complex string produced by MultiTrackAudioMixer.build().

    Raises:
        ValueError: If a DuckingPair references a track ID not in the audio
            track list, or if MultiTrackAudioMixer.build() returns an error.
    """
    audio_tracks = [t for t in tracks if t.track_type == "audio"]
    if not audio_tracks:
        raise ValueError("at least 1 audio track is required")
    seen_ids: set[str] = set()
    dupe_ids: set[str] = set()
    for t in audio_tracks:
        if t.id in seen_ids:
            dupe_ids.add(t.id)
        seen_ids.add(t.id)
    if dupe_ids:
        raise ValueError(f"duplicate audio track id(s): {', '.join(sorted(dupe_ids))!r}")
    id_to_idx = {t.id: i for i, t in enumerate(audio_tracks)}

    mixer = sfc.MultiTrackAudioMixer()
    for idx, track in enumerate(audio_tracks):
        mixer.add_track(idx, track.volume_envelope, track.weight)

    for pair in ducking_pairs:
        ducked_idx = id_to_idx.get(pair.ducked_track_id)
        sidechain_idx = id_to_idx.get(pair.sidechain_track_id)
        if ducked_idx is None:
            raise ValueError(
                f"DuckingPair {pair.id}: ducked_track_id {pair.ducked_track_id!r} "
                "not found in audio tracks"
            )
        if sidechain_idx is None:
            raise ValueError(
                f"DuckingPair {pair.id}: sidechain_track_id {pair.sidechain_track_id!r} "
                "not found in audio tracks"
            )
        mixer.add_ducking_pair(
            ducked_idx,
            sidechain_idx,
            pair.threshold,
            pair.ratio,
            pair.attack_ms,
            pair.release_ms,
            pair.apply_pre_volume,
        )

    result: str = mixer.build()
    return result

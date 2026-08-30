# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
from __future__ import annotations

from collections.abc import Sequence

from stoat_ferret.db.models import Clip


def _check_clip_adjacency(clip_a: Clip, clip_b: Clip, all_clips: Sequence[Clip]) -> bool:
    """Return True iff clip_a and clip_b are adjacent on the same track.

    Geometric rule: same track_id, clip_a.timeline_end == clip_b.timeline_start.
    Assumes clip_a precedes clip_b on the timeline.
    """
    if clip_a.track_id is None or clip_b.track_id is None:
        return False
    if clip_a.track_id != clip_b.track_id:
        return False
    if clip_a.timeline_end is None or clip_b.timeline_start is None:
        return False
    return clip_a.timeline_end == clip_b.timeline_start

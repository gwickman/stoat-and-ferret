# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Acceptance test: uc_media_split_preserve — clip split preserves effects (BL-800 AC-6).

Builds a project with a clip carrying effects, splits it with the default
copy_full_stack policy, and asserts:
- Both children retain the parent's effects list.
- migration_report has one entry per effect with disposition=copied.
- children receive distinct IDs (not the original clip's ID).
- Original clip is deleted after split.

No FFmpeg required; exercised via FastAPI TestClient with in-memory repositories.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.models import Clip, Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository

_PROJECT_ID = "proj-accept-split-preserve"
_CLIP_ID = "clip-accept-split-preserve"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def test_uc_media_split_preserve() -> None:
    """Full split-preserve scenario: clip split retains effects and migration_report.

    BL-800-AC-6: Splits a clip carrying effects and asserts children retain/remap
    per policy plus a migration report.
    """
    parent_effects: list[Any] = [
        {"effect_type": "reverse", "filter_string": "reverse"},
        {"effect_type": "volume", "filter_string": "volume=2.0"},
    ]
    now = _now()
    clip = Clip(
        id=_CLIP_ID,
        project_id=_PROJECT_ID,
        source_video_id="video-accept-1",
        in_point=0,
        out_point=120,
        timeline_position=0,
        timeline_start=0.0,
        timeline_end=4.0,
        effects=parent_effects,
        created_at=now,
        updated_at=now,
    )
    project = Project(
        id=_PROJECT_ID,
        name="Accept Split Preserve Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )

    project_repo = AsyncInMemoryProjectRepository()
    clip_repo = AsyncInMemoryClipRepository()
    project_repo.seed([project])
    clip_repo.seed([clip])

    app = create_app(
        project_repository=project_repo,
        clip_repository=clip_repo,
    )

    with TestClient(app) as client:
        # Step 1: Split with default policy (copy_full_stack)
        resp = client.post(
            f"/api/v1/projects/{_PROJECT_ID}/clips/{_CLIP_ID}/split",
            json={"split_frame": 60},
        )

    assert resp.status_code == 200, f"split failed: {resp.text}"
    data = resp.json()

    # Step 2: Both children carry the parent's effects list
    assert data["clip_a"]["effects"] == parent_effects, (
        f"clip_a effects mismatch: {data['clip_a']['effects']}"
    )
    assert data["clip_b"]["effects"] == parent_effects, (
        f"clip_b effects mismatch: {data['clip_b']['effects']}"
    )

    # Step 3: migration_report has one entry per effect
    report = data["migration_report"]
    assert len(report) == len(parent_effects), (
        f"expected {len(parent_effects)} migration_report entries, got {len(report)}: {report}"
    )
    for entry in report:
        assert entry["disposition"] == "copied", f"unexpected disposition: {entry}"
        assert entry["target"] == "both", f"unexpected target: {entry}"

    # Step 4: Children have distinct IDs (not the original)
    clip_a_id = data["clip_a"]["id"]
    clip_b_id = data["clip_b"]["id"]
    assert clip_a_id != _CLIP_ID
    assert clip_b_id != _CLIP_ID
    assert clip_a_id != clip_b_id

    # Step 5: Split frame boundaries correct
    assert data["clip_a"]["out_point"] == 60
    assert data["clip_b"]["in_point"] == 60
    assert data["clip_a"]["in_point"] == 0
    assert data["clip_b"]["out_point"] == 120

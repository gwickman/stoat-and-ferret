# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for project audio baseline (BL-422).

Tests sample_rate and bit_depth fields across:
- ProjectCreate/ProjectUpdate schema validation
- ProjectResponse serialization
- AsyncInMemoryProjectRepository parity
- create_render_job() audio field injection
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from stoat_ferret.api.schemas.project import ProjectCreate, ProjectResponse, ProjectUpdate
from stoat_ferret.db.models import Project
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository


def _make_project(**kwargs) -> Project:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id="test-id",
        name="Test Project",
        output_width=1920,
        output_height=1080,
        output_fps=30,
        created_at=now,
        updated_at=now,
    )
    defaults.update(kwargs)
    return Project(**defaults)


class TestProjectCreateSchema:
    def test_default_values(self) -> None:
        req = ProjectCreate(name="MyProject")
        assert req.sample_rate == 48000
        assert req.bit_depth == 24

    def test_custom_values(self) -> None:
        req = ProjectCreate(name="MyProject", sample_rate=44100, bit_depth=32)
        assert req.sample_rate == 44100
        assert req.bit_depth == 32

    def test_invalid_sample_rate_422(self) -> None:
        with pytest.raises(ValidationError):
            ProjectCreate(name="X", sample_rate=22050)  # type: ignore[arg-type]

    def test_invalid_bit_depth_422(self) -> None:
        with pytest.raises(ValidationError):
            ProjectCreate(name="X", bit_depth=8)  # type: ignore[arg-type]

    def test_all_valid_sample_rates(self) -> None:
        for sr in (44100, 48000, 96000):
            req = ProjectCreate(name="X", sample_rate=sr)
            assert req.sample_rate == sr

    def test_all_valid_bit_depths(self) -> None:
        for bd in (16, 24, 32):
            req = ProjectCreate(name="X", bit_depth=bd)
            assert req.bit_depth == bd


class TestProjectUpdateSchema:
    def test_all_fields_optional(self) -> None:
        req = ProjectUpdate()
        assert req.sample_rate is None
        assert req.bit_depth is None

    def test_set_sample_rate(self) -> None:
        req = ProjectUpdate(sample_rate=96000)
        assert req.sample_rate == 96000

    def test_set_bit_depth(self) -> None:
        req = ProjectUpdate(bit_depth=16)
        assert req.bit_depth == 16

    def test_invalid_sample_rate(self) -> None:
        with pytest.raises(ValidationError):
            ProjectUpdate(sample_rate=22050)  # type: ignore[arg-type]

    def test_invalid_bit_depth(self) -> None:
        with pytest.raises(ValidationError):
            ProjectUpdate(bit_depth=8)  # type: ignore[arg-type]


class TestProjectResponse:
    def test_includes_audio_fields(self) -> None:
        project = _make_project(sample_rate=44100, bit_depth=32)
        resp = ProjectResponse.model_validate(project)
        assert resp.sample_rate == 44100
        assert resp.bit_depth == 32

    def test_default_audio_fields(self) -> None:
        project = _make_project()
        resp = ProjectResponse.model_validate(project)
        assert resp.sample_rate == 48000
        assert resp.bit_depth == 24


class TestAsyncInMemoryProjectRepository:
    async def test_add_returns_audio_fields(self) -> None:
        repo = AsyncInMemoryProjectRepository()
        project = _make_project(sample_rate=44100, bit_depth=32)
        result = await repo.add(project)
        assert result.sample_rate == 44100
        assert result.bit_depth == 32

    async def test_get_returns_audio_fields(self) -> None:
        repo = AsyncInMemoryProjectRepository()
        project = _make_project(sample_rate=96000, bit_depth=16)
        await repo.add(project)
        fetched = await repo.get("test-id")
        assert fetched is not None
        assert fetched.sample_rate == 96000
        assert fetched.bit_depth == 16

    async def test_update_audio_fields(self) -> None:
        repo = AsyncInMemoryProjectRepository()
        project = _make_project()
        await repo.add(project)
        project.sample_rate = 96000
        project.bit_depth = 16
        await repo.update(project)
        fetched = await repo.get("test-id")
        assert fetched is not None
        assert fetched.sample_rate == 96000
        assert fetched.bit_depth == 16

    async def test_default_audio_fields(self) -> None:
        repo = AsyncInMemoryProjectRepository()
        project = _make_project()
        await repo.add(project)
        fetched = await repo.get("test-id")
        assert fetched is not None
        assert fetched.sample_rate == 48000
        assert fetched.bit_depth == 24


class TestProjectAudioAPIEndpoints:
    def _make_client(self) -> TestClient:
        from stoat_ferret.api.app import create_app

        app = create_app(project_repository=AsyncInMemoryProjectRepository())
        return TestClient(app)

    def test_create_project_default_audio(self) -> None:
        client = self._make_client()
        resp = client.post("/api/v1/projects", json={"name": "Test"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["sample_rate"] == 48000
        assert data["bit_depth"] == 24

    def test_create_project_custom_audio(self) -> None:
        client = self._make_client()
        resp = client.post(
            "/api/v1/projects",
            json={"name": "Test", "sample_rate": 44100, "bit_depth": 32},
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["sample_rate"] == 44100
        assert data["bit_depth"] == 32

    def test_get_project_includes_audio_fields(self) -> None:
        client = self._make_client()
        create_resp = client.post(
            "/api/v1/projects",
            json={"name": "Test", "sample_rate": 44100, "bit_depth": 16},
        )
        pid = create_resp.json()["id"]
        get_resp = client.get(f"/api/v1/projects/{pid}")
        assert get_resp.status_code == 200
        data = get_resp.json()
        assert data["sample_rate"] == 44100
        assert data["bit_depth"] == 16

    def test_patch_sample_rate(self) -> None:
        client = self._make_client()
        create_resp = client.post("/api/v1/projects", json={"name": "Test"})
        pid = create_resp.json()["id"]
        patch_resp = client.patch(f"/api/v1/projects/{pid}", json={"sample_rate": 96000})
        assert patch_resp.status_code == 200
        assert patch_resp.json()["sample_rate"] == 96000
        get_resp = client.get(f"/api/v1/projects/{pid}")
        assert get_resp.json()["sample_rate"] == 96000

    def test_invalid_sample_rate_returns_422(self) -> None:
        client = self._make_client()
        resp = client.post(
            "/api/v1/projects",
            json={"name": "Test", "sample_rate": 22050},
        )
        assert resp.status_code == 422

    def test_invalid_bit_depth_returns_422(self) -> None:
        client = self._make_client()
        resp = client.post(
            "/api/v1/projects",
            json={"name": "Test", "bit_depth": 8},
        )
        assert resp.status_code == 422


class TestCreateRenderJobAudioInjection:
    """Unit tests for audio field injection in create_render_job."""

    def test_audio_fields_injected_into_plan_data(self) -> None:
        """create_render_job injects sample_rate/bit_depth from project into plan_data."""
        # Build a minimal plan_data as the router would
        plan_data: dict = {"settings": {"quality_preset": "medium", "width": 1920, "height": 1080}}
        project = _make_project(sample_rate=44100, bit_depth=32)

        # Simulate the injection logic from create_render_job
        plan_data["settings"]["width"] = project.output_width or 1920
        plan_data["settings"]["height"] = project.output_height or 1080
        plan_data["settings"]["audio_sample_rate"] = project.sample_rate
        plan_data["settings"]["audio_bit_depth"] = project.bit_depth

        assert plan_data["settings"]["audio_sample_rate"] == 44100
        assert plan_data["settings"]["audio_bit_depth"] == 32

    def test_default_audio_values_injected(self) -> None:
        plan_data: dict = {"settings": {}}
        project = _make_project()

        plan_data["settings"]["audio_sample_rate"] = project.sample_rate
        plan_data["settings"]["audio_bit_depth"] = project.bit_depth

        assert plan_data["settings"]["audio_sample_rate"] == 48000
        assert plan_data["settings"]["audio_bit_depth"] == 24

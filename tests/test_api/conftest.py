# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Shared fixtures for API tests."""

from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
from stoat_ferret.db.asset_repository import AssetRecord
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.batch_repository import InMemoryBatchRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.proxy_repository import InMemoryProxyRepository
from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
from stoat_ferret.db.version_repository import AsyncInMemoryVersionRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository
from tests.factories import ProjectFactory, make_test_video


class InMemoryAssetRepository:
    """Dict-backed implementation of AsyncAssetRepository for tests."""

    def __init__(self) -> None:
        self._store: dict[str, AssetRecord] = {}

    async def insert(self, asset: AssetRecord) -> AssetRecord:
        self._store[asset.id] = asset
        return asset

    async def get_by_id(self, asset_id: str) -> AssetRecord | None:
        return self._store.get(asset_id)

    async def get_by_content_hash(self, content_hash: str) -> AssetRecord | None:
        for r in self._store.values():
            if r.content_hash == content_hash:
                return r
        return None

    async def list_assets(
        self,
        kind: str | None,
        tags: list[str] | None,
        offset: int,
        limit: int,
    ) -> list[AssetRecord]:
        items = [r for r in self._store.values() if r.deleted_at is None]
        if kind is not None:
            items = [r for r in items if r.kind == kind]
        items.sort(key=lambda r: r.created_at, reverse=True)
        return items[offset : offset + limit]

    async def soft_delete(self, asset_id: str) -> bool:
        r = self._store.get(asset_id)
        if r is None or r.deleted_at is not None:
            return False
        r.deleted_at = datetime.now(timezone.utc).isoformat()
        return True

    async def restore(self, asset_id: str) -> AssetRecord | None:
        r = self._store.get(asset_id)
        if r is None:
            return None
        r.deleted_at = None
        r.updated_at = datetime.now(timezone.utc).isoformat()
        return r


@pytest.fixture
def asset_repository() -> InMemoryAssetRepository:
    """Create in-memory asset repository for testing.

    Returns:
        Empty in-memory asset repository.
    """
    return InMemoryAssetRepository()


@pytest.fixture
def video_repository() -> AsyncInMemoryVideoRepository:
    """Create in-memory video repository for testing.

    Returns:
        Empty in-memory video repository.
    """
    return AsyncInMemoryVideoRepository()


@pytest.fixture
def project_repository() -> AsyncInMemoryProjectRepository:
    """Create in-memory project repository for testing.

    Returns:
        Empty in-memory project repository.
    """
    return AsyncInMemoryProjectRepository()


@pytest.fixture
def clip_repository() -> AsyncInMemoryClipRepository:
    """Create in-memory clip repository for testing.

    Returns:
        Empty in-memory clip repository.
    """
    return AsyncInMemoryClipRepository()


@pytest.fixture
def timeline_repository() -> AsyncInMemoryTimelineRepository:
    """Create in-memory timeline repository for testing.

    Returns:
        Empty in-memory timeline repository.
    """
    return AsyncInMemoryTimelineRepository()


@pytest.fixture
def version_repository() -> AsyncInMemoryVersionRepository:
    """Create in-memory version repository for testing.

    Returns:
        Empty in-memory version repository.
    """
    return AsyncInMemoryVersionRepository()


@pytest.fixture
def batch_repository() -> InMemoryBatchRepository:
    """Create in-memory batch repository for testing.

    Returns:
        Empty in-memory batch repository.
    """
    return InMemoryBatchRepository()


@pytest.fixture
def proxy_repository() -> InMemoryProxyRepository:
    """Create in-memory proxy repository for testing.

    Returns:
        Empty in-memory proxy repository.
    """
    return InMemoryProxyRepository()


@pytest.fixture
def render_repository() -> InMemoryRenderRepository:
    """Create in-memory render repository for testing.

    Returns:
        Empty in-memory render repository.
    """
    return InMemoryRenderRepository()


@pytest.fixture
def job_queue(video_repository: AsyncInMemoryVideoRepository) -> InMemoryJobQueue:
    """Create in-memory job queue with scan handler registered.

    Args:
        video_repository: In-memory video repository for the scan handler.

    Returns:
        Job queue with scan handler for deterministic test execution.
    """
    queue = InMemoryJobQueue()
    queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(video_repository))
    return queue


@pytest.fixture
def app(
    video_repository: AsyncInMemoryVideoRepository,
    project_repository: AsyncInMemoryProjectRepository,
    clip_repository: AsyncInMemoryClipRepository,
    timeline_repository: AsyncInMemoryTimelineRepository,
    version_repository: AsyncInMemoryVersionRepository,
    batch_repository: InMemoryBatchRepository,
    proxy_repository: InMemoryProxyRepository,
    render_repository: InMemoryRenderRepository,
    job_queue: InMemoryJobQueue,
    asset_repository: InMemoryAssetRepository,
) -> FastAPI:
    """Create test application with injected in-memory repositories.

    Uses create_app() parameter injection instead of dependency_overrides.

    Args:
        video_repository: In-memory video repository for testing.
        project_repository: In-memory project repository for testing.
        clip_repository: In-memory clip repository for testing.
        timeline_repository: In-memory timeline repository for testing.
        version_repository: In-memory version repository for testing.
        batch_repository: In-memory batch repository for testing.
        proxy_repository: In-memory proxy repository for testing.
        render_repository: In-memory render repository for testing.
        job_queue: In-memory job queue for testing.
        asset_repository: In-memory asset repository for testing.

    Returns:
        Configured FastAPI application for testing.
    """
    return create_app(
        video_repository=video_repository,
        project_repository=project_repository,
        clip_repository=clip_repository,
        timeline_repository=timeline_repository,
        version_repository=version_repository,
        batch_repository=batch_repository,
        proxy_repository=proxy_repository,
        render_repository=render_repository,
        job_queue=job_queue,
        asset_repository=asset_repository,
    )


@pytest.fixture
def client(
    app: FastAPI,
) -> Generator[TestClient, None, None]:
    """Create test client for API requests.

    The TestClient handles lifespan events automatically.
    Repositories are injected via create_app() parameters.

    Args:
        app: FastAPI application fixture.

    Yields:
        Test client for making HTTP requests.
    """
    with TestClient(app) as c:
        yield c


class ApiFactory:
    """Factory wrapper that creates test data through the HTTP API.

    Combines a ProjectFactory with a TestClient and video repository
    so that ``create_via_api()`` can seed videos automatically.
    """

    def __init__(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        self._client = client
        self._video_repository = video_repository

    def project(self) -> _ApiProjectBuilder:
        """Start building a project for API creation.

        Returns:
            An API-aware project builder.
        """
        return _ApiProjectBuilder(self._client, self._video_repository)


class _ApiProjectBuilder:
    """Builder that creates projects and clips via the HTTP API."""

    def __init__(
        self,
        client: TestClient,
        video_repository: AsyncInMemoryVideoRepository,
    ) -> None:
        self._factory = ProjectFactory()
        self._client = client
        self._video_repository = video_repository
        self._video_ids: list[str] = []

    def with_name(self, name: str) -> _ApiProjectBuilder:
        """Set the project name.

        Args:
            name: Project name.

        Returns:
            Self for fluent chaining.
        """
        self._factory.with_name(name)
        return self

    def with_output(
        self,
        *,
        width: int | None = None,
        height: int | None = None,
        fps: int | None = None,
    ) -> _ApiProjectBuilder:
        """Set output dimensions and/or frame rate.

        Args:
            width: Output width in pixels.
            height: Output height in pixels.
            fps: Output frames per second.

        Returns:
            Self for fluent chaining.
        """
        self._factory.with_output(width=width, height=height, fps=fps)
        return self

    async def with_clip(
        self,
        *,
        in_point: int = 0,
        out_point: int = 100,
        timeline_position: int = 0,
    ) -> _ApiProjectBuilder:
        """Add a clip, auto-seeding a video in the repository.

        Args:
            in_point: Clip start frame.
            out_point: Clip end frame.
            timeline_position: Position on timeline in frames.

        Returns:
            Self for fluent chaining.
        """
        video = make_test_video()
        await self._video_repository.add(video)
        self._video_ids.append(video.id)
        self._factory.with_clip(
            source_video_id=video.id,
            in_point=in_point,
            out_point=out_point,
            timeline_position=timeline_position,
        )
        return self

    def create(self) -> dict[str, Any]:
        """Create the project (and clips) via the API.

        Returns:
            Dict with ``"project"`` and ``"clips"`` response data.
        """
        return self._factory.create_via_api(self._client)


@pytest.fixture
def api_factory(
    client: TestClient,
    video_repository: AsyncInMemoryVideoRepository,
) -> ApiFactory:
    """Provide an ApiFactory wired to the test client.

    Args:
        client: TestClient fixture.
        video_repository: In-memory video repository fixture.

    Returns:
        An ApiFactory for creating test data via HTTP.
    """
    return ApiFactory(client, video_repository)

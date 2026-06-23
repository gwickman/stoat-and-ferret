# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Shared fixtures for integration tests."""

from __future__ import annotations

from collections.abc import Generator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.app import create_app
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
from stoat_ferret.db.batch_repository import InMemoryBatchRepository
from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository
from stoat_ferret.db.proxy_repository import InMemoryProxyRepository
from stoat_ferret.db.timeline_repository import AsyncInMemoryTimelineRepository
from stoat_ferret.db.version_repository import AsyncInMemoryVersionRepository
from stoat_ferret.jobs.queue import InMemoryJobQueue
from stoat_ferret.render.render_repository import InMemoryRenderRepository


@pytest.fixture
def app() -> FastAPI:
    """Create test application with in-memory repositories."""
    return create_app(
        video_repository=AsyncInMemoryVideoRepository(),
        project_repository=AsyncInMemoryProjectRepository(),
        clip_repository=AsyncInMemoryClipRepository(),
        timeline_repository=AsyncInMemoryTimelineRepository(),
        version_repository=AsyncInMemoryVersionRepository(),
        batch_repository=InMemoryBatchRepository(),
        proxy_repository=InMemoryProxyRepository(),
        render_repository=InMemoryRenderRepository(),
        job_queue=InMemoryJobQueue(),
    )


@pytest.fixture
def client(app: FastAPI) -> Generator[TestClient, None, None]:
    """Create synchronous test client."""
    with TestClient(app) as c:
        yield c

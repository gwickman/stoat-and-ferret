"""Tests for ``/api/v1/testing/seed`` endpoints (BL-276).

These tests cover the testing-mode guard (INV-SEED-1), the enforced
``seeded_`` prefix (INV-SEED-2), and fixture persistence across
requests until an explicit DELETE (INV-SEED-3).
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stoat_ferret.api.settings import Settings
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository


@pytest.fixture
def testing_mode_client(app: FastAPI) -> Iterator[TestClient]:
    """Yield a TestClient with ``Settings.testing_mode=True`` installed.

    The ``_settings`` attribute on ``app.state`` is the hook the router
    consults (see ``testing._settings_from_request``); it must be set
    *after* the TestClient enters its context, because the lifespan
    stomps on the value with its own ``get_settings()`` result during
    startup. The override is strictly scoped to the test lifetime.
    """
    with TestClient(app) as c:
        app.state._settings = Settings(testing_mode=True)
        yield c


@pytest.fixture
def testing_mode_off_client(app: FastAPI) -> Iterator[TestClient]:
    """Yield a TestClient with ``Settings.testing_mode=False``."""
    with TestClient(app) as c:
        app.state._settings = Settings(testing_mode=False)
        yield c


# ---------------------------------------------------------------------------
# INV-SEED-1 / FR-002: testing-mode guard
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_seed_post_rejected_when_testing_mode_disabled(
    testing_mode_off_client: TestClient,
) -> None:
    """POST returns 403 when testing mode is off (INV-SEED-1)."""
    response = testing_mode_off_client.post(
        "/api/v1/testing/seed",
        json={"fixture_type": "project", "name": "my_fixture"},
    )
    assert response.status_code == 403
    body = response.json()
    assert body["detail"]["code"] == "TESTING_MODE_DISABLED"


@pytest.mark.api
def test_seed_delete_rejected_when_testing_mode_disabled(
    testing_mode_off_client: TestClient,
) -> None:
    """DELETE returns 403 when testing mode is off (INV-SEED-1)."""
    response = testing_mode_off_client.delete("/api/v1/testing/seed/does-not-matter")
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "TESTING_MODE_DISABLED"


# ---------------------------------------------------------------------------
# FR-001 / FR-003 / INV-SEED-2: create + enforced prefix
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_seed_post_creates_fixture_with_prefix(
    testing_mode_client: TestClient,
) -> None:
    """POST returns 201 with the ``seeded_`` prefix applied (INV-SEED-2)."""
    response = testing_mode_client.post(
        "/api/v1/testing/seed",
        json={"fixture_type": "project", "name": "my_fixture"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["fixture_type"] == "project"
    assert body["name"] == "seeded_my_fixture"
    assert body["fixture_id"]


@pytest.mark.api
def test_seed_post_ignores_caller_supplied_prefix(
    testing_mode_client: TestClient,
) -> None:
    """Server does not strip a pre-supplied ``seeded_`` — it stacks (spec)."""
    # The contract says the server *prepends* the prefix; callers are
    # documented never to pre-prefix. Asserting on the concatenation
    # behaviour guards against a silent "strip existing prefix" refactor.
    response = testing_mode_client.post(
        "/api/v1/testing/seed",
        json={"fixture_type": "project", "name": "seeded_already"},
    )
    assert response.status_code == 201
    assert response.json()["name"] == "seeded_seeded_already"


@pytest.mark.api
def test_seed_post_honors_project_data_overrides(
    testing_mode_client: TestClient,
) -> None:
    """Project-type fixtures accept output_width/height/fps overrides."""
    response = testing_mode_client.post(
        "/api/v1/testing/seed",
        json={
            "fixture_type": "project",
            "name": "hd",
            "data": {"output_width": 3840, "output_height": 2160, "output_fps": 60},
        },
    )
    assert response.status_code == 201
    fixture_id = response.json()["fixture_id"]

    fetched = testing_mode_client.get(f"/api/v1/projects/{fixture_id}")
    assert fetched.status_code == 200
    body = fetched.json()
    assert body["output_width"] == 3840
    assert body["output_height"] == 2160
    assert body["output_fps"] == 60


@pytest.mark.api
def test_seed_post_rejects_unknown_fixture_type(
    testing_mode_client: TestClient,
) -> None:
    """POST returns 422 when fixture_type is outside the supported set."""
    response = testing_mode_client.post(
        "/api/v1/testing/seed",
        json={"fixture_type": "unicorn", "name": "whatever"},
    )
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNSUPPORTED_FIXTURE_TYPE"


@pytest.mark.api
def test_seed_post_rejects_blank_name(
    testing_mode_client: TestClient,
) -> None:
    """Pydantic validation rejects empty names (FR-003 guards against 'seeded_')."""
    response = testing_mode_client.post(
        "/api/v1/testing/seed",
        json={"fixture_type": "project", "name": ""},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# FR-005 / INV-SEED-3: fixture persists and is visible via pass-through GET
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_seed_fixture_is_visible_via_project_endpoint(
    testing_mode_client: TestClient,
) -> None:
    """A seeded project is listed by the standard /api/v1/projects endpoint."""
    create = testing_mode_client.post(
        "/api/v1/testing/seed",
        json={"fixture_type": "project", "name": "visible"},
    )
    assert create.status_code == 201
    fixture_id = create.json()["fixture_id"]

    listed = testing_mode_client.get("/api/v1/projects")
    assert listed.status_code == 200
    names = {p["name"] for p in listed.json()["projects"]}
    assert "seeded_visible" in names

    detail = testing_mode_client.get(f"/api/v1/projects/{fixture_id}")
    assert detail.status_code == 200
    assert detail.json()["name"] == "seeded_visible"


# ---------------------------------------------------------------------------
# FR-004: DELETE lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.api
def test_seed_delete_removes_fixture(testing_mode_client: TestClient) -> None:
    """POST → DELETE → GET returns 404 (complete lifecycle)."""
    create = testing_mode_client.post(
        "/api/v1/testing/seed",
        json={"fixture_type": "project", "name": "ephemeral"},
    )
    assert create.status_code == 201
    fixture_id = create.json()["fixture_id"]

    delete = testing_mode_client.delete(f"/api/v1/testing/seed/{fixture_id}")
    assert delete.status_code == 204
    assert delete.content == b""

    missing = testing_mode_client.get(f"/api/v1/projects/{fixture_id}")
    assert missing.status_code == 404


@pytest.mark.api
def test_seed_delete_unknown_id_returns_404(
    testing_mode_client: TestClient,
) -> None:
    """DELETE of a non-existent id returns 404, not 204."""
    response = testing_mode_client.delete("/api/v1/testing/seed/nonexistent-id")
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "NOT_FOUND"


@pytest.mark.api
def test_seed_delete_rejects_unknown_fixture_type(
    testing_mode_client: TestClient,
) -> None:
    """DELETE with unsupported fixture_type returns 422."""
    response = testing_mode_client.delete("/api/v1/testing/seed/any-id?fixture_type=unicorn")
    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "UNSUPPORTED_FIXTURE_TYPE"


# ---------------------------------------------------------------------------
# Repository interaction — verifies INV-SEED-3 persistence semantics
# ---------------------------------------------------------------------------


@pytest.mark.api
async def test_seeded_project_persists_in_repository(
    testing_mode_client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """The fixture lives in the project repository with the prefixed name."""
    create = testing_mode_client.post(
        "/api/v1/testing/seed",
        json={"fixture_type": "project", "name": "persisted"},
    )
    assert create.status_code == 201
    fixture_id = create.json()["fixture_id"]

    stored = await project_repository.get(fixture_id)
    assert stored is not None
    assert stored.name == "seeded_persisted"

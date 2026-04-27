"""Test fixture seed endpoints (BL-276).

Exposes ``POST /api/v1/testing/seed`` and
``DELETE /api/v1/testing/seed/{fixture_id}``.

Both endpoints are gated by ``Settings.testing_mode`` (INV-SEED-1):
when the flag is disabled the handler returns HTTP 403 before any
repository interaction. The server enforces the ``seeded_`` name prefix
(INV-SEED-2) so callers cannot leak unprefixed fixtures into production
data paths. Fixtures persist across requests until explicitly deleted
(INV-SEED-3); the underlying repositories own all persistence.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request, Response, status

from stoat_ferret.api.middleware.metrics import stoat_seed_duration_seconds
from stoat_ferret.api.routers.projects import (
    ProjectRepoDep,
    get_project_repository,
)
from stoat_ferret.api.schemas.seed_fixture import SeedRequest, SeedResponse
from stoat_ferret.api.settings import Settings, get_settings
from stoat_ferret.db.models import Project
from stoat_ferret.db.project_repository import AsyncProjectRepository

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1/testing", tags=["testing"])

SEEDED_PREFIX = "seeded_"
SUPPORTED_FIXTURE_TYPES = frozenset({"project"})


def _settings_from_request(request: Request) -> Settings:
    """Resolve effective ``Settings`` for this request.

    Prefers the instance stored on ``app.state`` by the lifespan (the
    same pattern used by the flags router) so the runtime flag state is
    single-sourced. Falls back to ``get_settings()`` when lifespan is
    bypassed (e.g. tests that skip startup).
    """
    state_settings: Settings | None = getattr(request.app.state, "_settings", None)
    if state_settings is not None:
        return state_settings
    return get_settings()


def require_testing_mode(request: Request) -> Settings:
    """Reject the request with HTTP 403 unless ``testing_mode`` is on.

    Used as a FastAPI ``Depends`` so the check runs before the handler
    body — no repository work happens when the guard fails. The returned
    :class:`Settings` instance is made available to callers that want to
    log or branch on further flags without re-resolving it.
    """
    settings = _settings_from_request(request)
    if not settings.testing_mode:
        logger.info("testing.seed.forbidden", reason="testing_mode_disabled")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "TESTING_MODE_DISABLED",
                "message": (
                    "Seed endpoints require STOAT_TESTING_MODE=true. "
                    "This deployment has testing mode disabled."
                ),
            },
        )
    return settings


TestingModeDep = Annotated[Settings, Depends(require_testing_mode)]


@router.post(
    "/seed",
    response_model=SeedResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        403: {
            "description": (
                "Testing mode is disabled. Set ``STOAT_TESTING_MODE=true`` to "
                "enable seed endpoints; the response body carries "
                '``{"detail": {"code": "TESTING_MODE_DISABLED", "message": ...}}``.'
            ),
        },
        422: {
            "description": (
                "Request failed validation. Sent when ``fixture_type`` is not "
                "one of the supported values or the body is malformed; the "
                "``detail`` field includes a structured error code."
            ),
        },
    },
)
async def create_seed_fixture(
    seed_request: SeedRequest,
    _settings: TestingModeDep,
    project_repo: ProjectRepoDep,
) -> SeedResponse:
    """Create a named test fixture (FR-001).

    The ``fixture_type`` field dispatches to the owning repository. All
    stored names carry the ``seeded_`` prefix (INV-SEED-2) so callers
    can enumerate seeded records without special indexes. Only
    ``testing_mode=True`` deployments reach this handler — the guard is
    enforced by :func:`require_testing_mode`.

    Args:
        seed_request: Parsed request body (fixture_type, name, data).
        _settings: Settings instance returned by the testing-mode guard.
            The argument is accepted only to enforce the dependency —
            handler logic reads from the repository, not the settings.
        project_repo: Injected project repository (in-memory in tests,
            SQLite in production).

    Returns:
        :class:`SeedResponse` echoing the fixture id, type, and final
        stored name.

    Raises:
        HTTPException: 422 when ``fixture_type`` is not supported. 403
            is raised earlier by :func:`require_testing_mode` when the
            guard fails.
    """
    if seed_request.fixture_type not in SUPPORTED_FIXTURE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "UNSUPPORTED_FIXTURE_TYPE",
                "message": (
                    f"fixture_type={seed_request.fixture_type!r} is not supported. "
                    f"Supported types: {sorted(SUPPORTED_FIXTURE_TYPES)}"
                ),
            },
        )

    prefixed_name = f"{SEEDED_PREFIX}{seed_request.name}"

    with stoat_seed_duration_seconds.time():
        if seed_request.fixture_type == "project":
            fixture_id = await _create_project_fixture(
                project_repo, prefixed_name, seed_request.data
            )
        else:  # pragma: no cover — guarded above
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

    logger.info(
        "testing.seed.created",
        fixture_type=seed_request.fixture_type,
        fixture_id=fixture_id,
        name=prefixed_name,
    )
    return SeedResponse(
        fixture_id=fixture_id,
        fixture_type=seed_request.fixture_type,
        name=prefixed_name,
    )


@router.delete(
    "/seed/{fixture_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        403: {
            "description": (
                "Testing mode is disabled. Set ``STOAT_TESTING_MODE=true`` to "
                "enable seed endpoints."
            ),
        },
        404: {
            "description": (
                "No seeded fixture with the supplied ``fixture_id`` exists for "
                "the selected ``fixture_type``. The response carries "
                '``{"detail": {"code": "NOT_FOUND", "message": ...}}``.'
            ),
        },
        422: {
            "description": (
                "Unsupported ``fixture_type`` query parameter (only ``project`` "
                "is currently supported)."
            ),
        },
    },
)
async def delete_seed_fixture(
    _settings: TestingModeDep,
    project_repo: ProjectRepoDep,
    fixture_id: str = Path(
        description="Identifier returned by ``POST /api/v1/testing/seed``.",
        examples=["proj_01HXZ2T9CK3Q4R5S6T7U8V9W0X"],
    ),
    fixture_type: str = Query(
        default="project",
        description=("Repository that owns the fixture. Currently only ``project`` is supported."),
        examples=["project"],
    ),
) -> Response:
    """Remove a previously seeded fixture (FR-004).

    The ``fixture_type`` query parameter routes the delete to the
    correct repository; it defaults to ``project`` because that is the
    only supported type in this release (NFR-002 allows adding more).
    Only ``testing_mode=True`` deployments reach this handler.

    Args:
        fixture_id: Identifier returned by the prior POST.
        _settings: Settings instance returned by the testing-mode guard.
        project_repo: Injected project repository.
        fixture_type: Which repository owns the fixture (query string).

    Returns:
        Empty ``204 No Content`` response on success.

    Raises:
        HTTPException: 404 when no fixture with that id exists, 422 when
            ``fixture_type`` is not recognised.
    """
    if fixture_type not in SUPPORTED_FIXTURE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail={
                "code": "UNSUPPORTED_FIXTURE_TYPE",
                "message": (
                    f"fixture_type={fixture_type!r} is not supported. "
                    f"Supported types: {sorted(SUPPORTED_FIXTURE_TYPES)}"
                ),
            },
        )

    if fixture_type == "project":
        deleted = await project_repo.delete(fixture_id)
    else:  # pragma: no cover — guarded above
        deleted = False

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "NOT_FOUND",
                "message": f"Seeded fixture {fixture_id} not found",
            },
        )

    logger.info(
        "testing.seed.deleted",
        fixture_type=fixture_type,
        fixture_id=fixture_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


async def _create_project_fixture(
    repo: AsyncProjectRepository,
    prefixed_name: str,
    data: dict[str, object],
) -> str:
    """Persist a :class:`Project` fixture and return its id.

    Accepts the same optional fields as ``POST /api/v1/projects`` —
    ``output_width``, ``output_height``, ``output_fps`` — falling back to
    project defaults when absent so small seed payloads stay ergonomic
    for test authors.
    """
    now = datetime.now(timezone.utc)
    project = Project(
        id=Project.new_id(),
        name=prefixed_name,
        output_width=_int_or_default(data.get("output_width"), 1920),
        output_height=_int_or_default(data.get("output_height"), 1080),
        output_fps=_int_or_default(data.get("output_fps"), 30),
        created_at=now,
        updated_at=now,
    )
    await repo.add(project)
    return project.id


def _int_or_default(value: object, default: int) -> int:
    """Coerce ``value`` to ``int`` or return ``default`` when invalid."""
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    return default


# Re-export dependency accessor so test modules can override it without
# importing the projects router directly.
__all__ = [
    "router",
    "require_testing_mode",
    "get_project_repository",
]

"""Feature flags endpoint exposing STOAT_* boolean flag state (BL-268)."""

from __future__ import annotations

import structlog
from fastapi import APIRouter, Request

from stoat_ferret.api.middleware.metrics import stoat_feature_flag_state
from stoat_ferret.api.settings import Settings, get_settings
from stoat_ferret.models.flags import FlagsResponse

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/api/v1", tags=["flags"])


def _settings_from_request(request: Request) -> Settings:
    """Return Settings from app.state when present, falling back to get_settings().

    The lifespan stores Settings on app.state for consistency with other DI
    patterns. The fallback keeps the endpoint callable in tests that skip
    lifespan setup.
    """
    state_settings: Settings | None = getattr(request.app.state, "_settings", None)
    if state_settings is not None:
        return state_settings
    return get_settings()


@router.get("/flags", response_model=FlagsResponse)
async def get_flags(request: Request) -> FlagsResponse:
    """Return the current STOAT_* feature flag state.

    Values reflect the application's :class:`Settings` at startup; flags
    are immutable for the life of the process. No database query is
    performed — the response is derived from in-memory settings.

    Args:
        request: The FastAPI request object; used to reach the app state
            so the handler prefers the Settings instance resolved during
            lifespan over re-reading the environment.

    Returns:
        A :class:`FlagsResponse` with the four STOAT_* boolean flags.
    """
    settings = _settings_from_request(request)
    response = FlagsResponse(
        testing_mode=settings.testing_mode,
        seed_endpoint=settings.seed_endpoint,
        synthetic_monitoring=settings.synthetic_monitoring,
        batch_rendering=settings.batch_rendering,
    )
    # BL-288: refresh the feature-flag gauge whenever the endpoint is
    # called so /metrics reflects the latest configured state. Settings
    # are immutable for the life of the process, so this is idempotent.
    for flag_name, flag_value in (
        ("testing_mode", response.testing_mode),
        ("seed_endpoint", response.seed_endpoint),
        ("synthetic_monitoring", response.synthetic_monitoring),
        ("batch_rendering", response.batch_rendering),
    ):
        stoat_feature_flag_state.labels(flag=flag_name).set(int(flag_value))
    return response

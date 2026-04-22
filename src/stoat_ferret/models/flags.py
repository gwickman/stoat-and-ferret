"""Pydantic models for feature flag endpoint responses (BL-268)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class FlagsResponse(BaseModel):
    """Current state of the STOAT_* feature flags.

    Returned by GET /api/v1/flags. Values reflect the application's
    Settings (Pydantic BaseSettings) as resolved from environment
    variables at startup. Flags are immutable for the life of the
    application process.
    """

    model_config = ConfigDict(from_attributes=True)

    testing_mode: bool
    seed_endpoint: bool
    synthetic_monitoring: bool
    batch_rendering: bool

"""Pydantic models for feature flag endpoint responses (BL-268)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FlagsResponse(BaseModel):
    """Current state of the STOAT_* feature flags.

    Returned by GET /api/v1/flags. Values reflect the application's
    Settings (Pydantic BaseSettings) as resolved from environment
    variables at startup. Flags are immutable for the life of the
    application process.
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "testing_mode": False,
                    "seed_endpoint": False,
                    "synthetic_monitoring": True,
                    "batch_rendering": True,
                }
            ]
        },
    )

    testing_mode: bool = Field(
        description="``STOAT_TESTING_MODE`` — unlocks test-only endpoints (e.g. seed fixtures).",
    )
    seed_endpoint: bool = Field(
        description="``STOAT_SEED_ENDPOINT`` — legacy alias retained for ops dashboards.",
    )
    synthetic_monitoring: bool = Field(
        description="``STOAT_SYNTHETIC_MONITORING`` — enables background probe traffic.",
    )
    batch_rendering: bool = Field(
        description="``STOAT_BATCH_RENDERING`` — permits multi-clip batch render jobs.",
    )

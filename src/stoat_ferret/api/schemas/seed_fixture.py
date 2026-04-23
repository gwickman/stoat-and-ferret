"""Seed fixture API schemas (BL-276).

Pydantic models for the ``POST /api/v1/testing/seed`` request/response
contract. Fixtures are created only when ``Settings.testing_mode`` is
``True``; the handler enforces the ``seeded_`` name prefix server-side
(INV-SEED-2).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SeedRequest(BaseModel):
    """Request body for creating a seeded test fixture.

    The ``fixture_type`` field selects which in-memory domain object is
    created. Type-specific parameters are carried in ``data`` to keep the
    wire format stable as new fixture types are added; the router
    validates type-specific constraints before dispatching to the
    matching repository (NFR-002).
    """

    fixture_type: str = Field(
        description=(
            "Discriminator for the fixture category (e.g. ``project``). "
            "The server rejects unknown values with HTTP 422."
        ),
        min_length=1,
    )
    name: str = Field(
        description=(
            "Caller-supplied fixture name. The server prepends ``seeded_`` "
            "before persistence (INV-SEED-2); callers must not pre-prefix "
            "the value."
        ),
        min_length=1,
    )
    data: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Fixture-type-specific creation payload. For ``project`` "
            "fixtures, keys ``output_width``, ``output_height`` and "
            "``output_fps`` are honored; missing keys take project "
            "defaults."
        ),
    )


class SeedResponse(BaseModel):
    """Response body for a successful seed fixture creation (HTTP 201)."""

    model_config = ConfigDict(from_attributes=True)

    fixture_id: str = Field(
        description="Unique identifier returned by the underlying repository.",
    )
    fixture_type: str = Field(
        description="Echoes the request's ``fixture_type`` so the caller can fan-out cleanup.",
    )
    name: str = Field(
        description=(
            "Final stored name, always beginning with ``seeded_`` "
            "(INV-SEED-2). Useful for querying pass-through GET endpoints."
        ),
    )

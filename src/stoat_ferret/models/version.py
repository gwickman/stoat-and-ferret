"""Pydantic model for the /api/v1/version endpoint response (BL-267)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class AppVersionResponse(BaseModel):
    """Deployment version metadata returned by GET /api/v1/version.

    Named ``AppVersionResponse`` rather than ``VersionResponse`` to avoid
    an OpenAPI schema-name collision with the pre-existing project
    snapshot model at ``stoat_ferret.api.schemas.version.VersionResponse``.

    The response is assembled from three sources:

    - ``app_version`` comes from the FastAPI application version string.
    - ``core_version``, ``build_timestamp``, and ``git_sha`` come from the
      Rust :class:`stoat_ferret_core.VersionInfo` class populated at compile
      time by ``build.rs``. ``git_sha`` is the literal string ``"unknown"``
      when the build system did not capture a SHA.
    - ``python_version`` is the running interpreter version (``sys.version_info``).
    - ``database_version`` is the current ``alembic_version.version_num``
      revision hash (e.g., ``"1e895699ad50"``) or the literal ``"none"`` when
      the table is empty or missing.
    """

    model_config = ConfigDict(from_attributes=True)

    app_version: str
    core_version: str
    build_timestamp: str
    git_sha: str
    python_version: str
    database_version: str

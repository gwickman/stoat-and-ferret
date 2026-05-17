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
      time by ``build.rs``. ``git_sha`` is the Rust core compile-time SHA and
      may lag the running Python code after Python-only releases. The literal
      string ``"unknown"`` is used when the build system did not capture a SHA.
    - ``app_sha`` is the runtime-resolved git SHA captured once at startup
      by ``_get_git_sha()`` in ``app.py``. It reflects the actual running code
      at the time the process started, making it reliable for Python-only
      releases that do not recompile Rust. Returns ``"unknown"`` when git is
      unavailable (e.g. Docker deployments without git installed and no
      ``GIT_SHA`` env var set). Both ``git_sha`` and ``app_sha`` are present
      simultaneously so agents can compare them to detect divergence.
    - ``python_version`` is the running interpreter version (``sys.version_info``).
    - ``database_version`` is the current ``alembic_version.version_num``
      revision hash (e.g., ``"1e895699ad50"``) or the literal ``"none"`` when
      the table is empty or missing.

    **SHA semantics summary:**

    - ``git_sha``: Rust core compile-time SHA (may be weeks behind Python HEAD
      after Python-only releases — does not reflect Python changes).
    - ``app_sha``: Runtime-resolved SHA (reflects the deployed Python code at
      startup — authoritative for Python-only release identification).
    - ``build_timestamp``: Rust core compile timestamp (same staleness risk as
      ``git_sha`` after Python-only releases).

    An agent that needs to verify it is testing the current Python HEAD should
    compare ``app_sha`` against the known target commit, not ``git_sha``.
    """

    model_config = ConfigDict(from_attributes=True)

    app_version: str
    core_version: str
    build_timestamp: str
    git_sha: str
    app_sha: str
    python_version: str
    database_version: str

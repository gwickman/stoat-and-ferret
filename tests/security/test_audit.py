"""Phase 6 Python security audit probe suite (BL-286).

Automated probes covering the four audit families called out in the v043
``python-security-audit`` requirements:

* **SQL injection** — AST-walk every Python file under ``src/`` looking for
  ``.execute()`` / ``.executemany()`` invocations whose SQL argument is
  built via f-string or ``%`` interpolation. Calls in the allowlist are
  internal DDL with non-user-controllable identifiers; any call outside
  the allowlist fails the probe.
* **Seed endpoint access control** — POST ``/api/v1/testing/seed`` with
  ``STOAT_TESTING_MODE`` disabled and verify a 403 with no project
  repository writes.
* **Path traversal** — null-byte injection, symlink escape against a
  configured ``ALLOWED_SCAN_ROOTS``, and double-encoded ``..`` payloads
  against ``POST /api/v1/videos/scan``.
* **Configuration drift** — derive ``STOAT_*`` env vars from the
  ``Settings`` model and assert every var either appears in
  ``docs/manual/`` or in the explicit drift baseline (P2 finding).

The tests assert observable behaviour (HTTP status, repository state,
discoverable settings) rather than call shapes. Findings detected by
these probes are documented in ``docs/security/review-phase6.md``.
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest
import structlog
from fastapi.testclient import TestClient

from stoat_ferret.api.settings import Settings
from stoat_ferret.db.project_repository import AsyncInMemoryProjectRepository

logger = structlog.get_logger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = REPO_ROOT / "src" / "stoat_ferret"
MANUAL_DIR = REPO_ROOT / "docs" / "manual"

pytestmark = pytest.mark.timeout(30)


# ---------------------------------------------------------------------------
# Stage 1 — SQL injection AST probe (FR-001)
# ---------------------------------------------------------------------------

# Calls in this allowlist are internal DDL whose interpolated values come from
# Python-side constants (column-name lists) or trusted runtime metadata
# (``sqlite_master`` queries). SQLite's PRAGMA and ALTER TABLE statements do
# not accept parameter binding for identifiers, so f-string interpolation is
# the only mechanism available — these calls are safe by construction. Each
# entry is ``(relative_path, line_number)``.
SQL_INTERPOLATION_ALLOWLIST: frozenset[tuple[str, int]] = frozenset(
    {
        ("src/stoat_ferret/db/schema.py", 343),
        ("src/stoat_ferret/db/schema.py", 359),
        ("src/stoat_ferret/db/schema.py", 425),
        ("src/stoat_ferret/db/schema.py", 441),
        ("src/stoat_ferret/api/services/migrations.py", 434),
        # IN-clause placeholder expansion: "?,?,?" derived from a list length.
        # The interpolated value contains only "?" and "," — values are bound
        # through the second argument to ``.execute()``.
        ("src/stoat_ferret/render/checkpoints.py", 140),
    }
)

EXECUTE_METHODS = frozenset({"execute", "executemany", "executescript"})

SQL_KEYWORD_PATTERN = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|PRAGMA|REPLACE|MERGE)\b",
    re.IGNORECASE,
)


def _looks_like_sql(node: ast.AST) -> bool:
    """Return ``True`` when ``node`` plausibly produces an SQL string."""
    if isinstance(node, ast.JoinedStr):
        for value in node.values:
            if (
                isinstance(value, ast.Constant)
                and isinstance(value.value, str)
                and SQL_KEYWORD_PATTERN.search(value.value)
            ):
                return True
        return False
    # ``"SELECT ..." % (...)`` style formatting.
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Mod)
        and isinstance(node.left, ast.Constant)
        and isinstance(node.left.value, str)
    ):
        return bool(SQL_KEYWORD_PATTERN.search(node.left.value))
    return False


def _scan_module_for_unsafe_sql(
    module_path: Path,
) -> list[tuple[str, int, str]]:
    """Return ``(rel_path, lineno, snippet)`` for unsafe execute calls."""
    source = module_path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(module_path))
    except SyntaxError:
        return []

    rel_path = module_path.relative_to(REPO_ROOT).as_posix()
    findings: list[tuple[str, int, str]] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        method_name = (
            func.attr
            if isinstance(func, ast.Attribute)
            else func.id
            if isinstance(func, ast.Name)
            else None
        )
        if method_name not in EXECUTE_METHODS:
            continue
        if not node.args:
            continue
        first_arg = node.args[0]
        if not _looks_like_sql(first_arg):
            continue
        snippet = ast.unparse(first_arg)
        findings.append((rel_path, node.lineno, snippet))

    return findings


def test_no_sql_fstring_interpolation() -> None:
    """No ``.execute()`` call uses f-string or ``%`` SQL interpolation outside the allowlist.

    Walks every ``.py`` file under ``src/stoat_ferret/`` looking for
    interpolated SQL. The allowlist captures the four ``ALTER TABLE``
    migrations (column names from a Python-side constant list) and the
    ``PRAGMA table_info`` snapshot helper (table name from a
    ``sqlite_master`` query). SQLite cannot bind identifiers, so these
    are the only places interpolation is used.
    """
    py_files = sorted(SRC_ROOT.rglob("*.py"))
    assert py_files, "expected to find Python sources under src/stoat_ferret"

    all_findings: list[tuple[str, int, str]] = []
    for module_path in py_files:
        all_findings.extend(_scan_module_for_unsafe_sql(module_path))

    unexpected = [
        (rel_path, lineno, snippet)
        for rel_path, lineno, snippet in all_findings
        if (rel_path, lineno) not in SQL_INTERPOLATION_ALLOWLIST
    ]

    for rel_path, lineno, snippet in all_findings:
        logger.info(
            "audit_finding",
            severity="P3" if (rel_path, lineno) in SQL_INTERPOLATION_ALLOWLIST else "P0",
            category="sql_injection",
            location=f"{rel_path}:{lineno}",
            snippet=snippet,
            allowlisted=(rel_path, lineno) in SQL_INTERPOLATION_ALLOWLIST,
        )

    assert not unexpected, (
        "Unexpected SQL string interpolation detected — review for injection risk:\n"
        + "\n".join(f"  {rel}:{lineno}  {snippet}" for rel, lineno, snippet in unexpected)
    )


def test_sql_interpolation_allowlist_is_live() -> None:
    """Every entry in the allowlist still resolves to a real ``execute`` call.

    Catches stale entries: when a refactor moves the interpolated DDL the
    allowlist needs to move with it, otherwise drift accumulates and the
    main probe silently weakens.
    """
    discovered: set[tuple[str, int]] = set()
    for module_path in sorted(SRC_ROOT.rglob("*.py")):
        for rel_path, lineno, _ in _scan_module_for_unsafe_sql(module_path):
            discovered.add((rel_path, lineno))

    stale = SQL_INTERPOLATION_ALLOWLIST - discovered
    assert not stale, (
        "SQL interpolation allowlist contains entries that no longer exist:\n"
        + "\n".join(f"  {rel}:{lineno}" for rel, lineno in sorted(stale))
    )


# ---------------------------------------------------------------------------
# Stage 2 — Seed endpoint access control (FR-002)
# ---------------------------------------------------------------------------


def test_seed_endpoint_blocked_without_testing_mode(
    client: TestClient,
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """``POST /api/v1/testing/seed`` returns 403 with no DB writes when testing_mode is off."""
    response = client.post(
        "/api/v1/testing/seed",
        json={"fixture_type": "project", "name": "audit_probe", "data": {}},
    )

    assert response.status_code == 403, response.text
    detail = response.json().get("detail", {})
    assert detail.get("code") == "TESTING_MODE_DISABLED"

    # No project should have been written even though the route was hit.
    projects = list(project_repository._projects.values())  # type: ignore[attr-defined]
    assert projects == [], f"expected zero projects after blocked seed, got {projects}"


def test_seed_delete_blocked_without_testing_mode(client: TestClient) -> None:
    """``DELETE /api/v1/testing/seed/{id}`` returns 403 when testing_mode is off."""
    response = client.delete("/api/v1/testing/seed/proj_audit_probe")
    assert response.status_code == 403, response.text


def test_seeded_prefix_enforcement_when_testing_mode_enabled(
    project_repository: AsyncInMemoryProjectRepository,
) -> None:
    """When testing_mode is enabled the response always carries the ``seeded_`` prefix."""
    from stoat_ferret.api.app import create_app
    from stoat_ferret.api.services.scan import SCAN_JOB_TYPE, make_scan_handler
    from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository
    from stoat_ferret.db.clip_repository import AsyncInMemoryClipRepository
    from stoat_ferret.jobs.queue import InMemoryJobQueue

    video_repo = AsyncInMemoryVideoRepository()
    clip_repo = AsyncInMemoryClipRepository()
    queue = InMemoryJobQueue()
    queue.register_handler(SCAN_JOB_TYPE, make_scan_handler(video_repo))

    app = create_app(
        video_repository=video_repo,
        project_repository=project_repository,
        clip_repository=clip_repo,
        job_queue=queue,
    )

    with TestClient(app) as testing_client:
        app.state._settings = Settings(testing_mode=True)
        response = testing_client.post(
            "/api/v1/testing/seed",
            json={"fixture_type": "project", "name": "audit_probe", "data": {}},
        )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"].startswith("seeded_"), body
    assert body["fixture_type"] == "project"


# ---------------------------------------------------------------------------
# Stage 3 — Path traversal probes (FR-003)
# ---------------------------------------------------------------------------


def test_path_traversal_null_byte_rejected(client: TestClient) -> None:
    """A scan path containing a null byte must not produce a 2xx response."""
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": "/var/media\x00/../../etc/passwd"},
    )
    assert 400 <= response.status_code < 500, (
        f"null-byte payload reached the scan handler (status={response.status_code})"
    )


def test_path_traversal_double_encoded_rejected(client: TestClient) -> None:
    """A scan path with double-encoded ``..`` segments must not be accepted."""
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": "%252e%252e/%252e%252e/etc/passwd"},
    )
    assert 400 <= response.status_code < 500, (
        f"double-encoded traversal reached the scan handler (status={response.status_code})"
    )


def test_path_traversal_relative_dotdot_rejected(client: TestClient) -> None:
    """Relative ``../`` traversal must not produce a 2xx response."""
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": "../../../etc"},
    )
    assert 400 <= response.status_code < 500, (
        f"relative traversal reached the scan handler (status={response.status_code})"
    )


def test_path_outside_allowed_root_returns_403(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``allowed_scan_roots`` is configured, paths outside it are forbidden."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    from stoat_ferret.api.routers import videos as videos_router

    real_get_settings = videos_router.get_settings

    class _RootedSettings:
        allowed_scan_roots = [str(allowed)]

    monkeypatch.setattr(videos_router, "get_settings", lambda: _RootedSettings(), raising=True)
    try:
        response = client.post(
            "/api/v1/videos/scan",
            json={"path": str(outside)},
        )
    finally:
        monkeypatch.setattr(videos_router, "get_settings", real_get_settings, raising=True)

    assert response.status_code == 403, response.text
    assert response.json()["detail"]["code"] == "PATH_NOT_ALLOWED"


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks require admin on Windows")
def test_path_traversal_symlink_escape_blocked(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A symlink pointing outside the allowed root resolves and is blocked."""
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()

    sneaky = allowed / "sneaky"
    sneaky.symlink_to(outside)

    from stoat_ferret.api.routers import videos as videos_router

    class _RootedSettings:
        allowed_scan_roots = [str(allowed)]

    monkeypatch.setattr(videos_router, "get_settings", lambda: _RootedSettings(), raising=True)
    response = client.post(
        "/api/v1/videos/scan",
        json={"path": str(sneaky)},
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# Stage 4 — Configuration drift audit (FR-005)
# ---------------------------------------------------------------------------

# ``STOAT_*`` env vars that are present in the Settings model but not yet
# referenced anywhere under ``docs/manual/``. Each entry is a P2 documentation
# finding tracked in ``docs/security/review-phase6.md``. New undocumented
# vars added to ``Settings`` must either be referenced in the manual or
# explicitly added here as a recognised gap.
KNOWN_UNDOCUMENTED_SETTINGS_VARS: frozenset[str] = frozenset(
    {
        "STOAT_BATCH_MAX_JOBS",
        "STOAT_BATCH_RENDERING",
        "STOAT_PREVIEW_CACHE_MAX_BYTES",
        "STOAT_PREVIEW_CACHE_MAX_SESSIONS",
        "STOAT_PREVIEW_SEGMENT_DURATION",
        "STOAT_PREVIEW_SESSION_TTL_SECONDS",
        "STOAT_PROXY_AUTO_GENERATE",
        "STOAT_PROXY_CLEANUP_THRESHOLD",
        "STOAT_SEED_ENDPOINT",
        "STOAT_SYNTHETIC_MONITORING",
        "STOAT_SYNTHETIC_MONITORING_INTERVAL_SECONDS",
        "STOAT_THUMBNAIL_STRIP_INTERVAL",
        "STOAT_VERSION_RETENTION_COUNT",
    }
)


_STOAT_VAR_PATTERN = re.compile(r"STOAT_[A-Z][A-Z0-9_]*")


def _settings_env_vars() -> set[str]:
    """Derive ``STOAT_*`` env-var names from the Settings model."""
    prefix = Settings.model_config.get("env_prefix", "STOAT_")
    return {f"{prefix}{name.upper()}" for name in Settings.model_fields}


def _documented_env_vars() -> set[str]:
    """Collect ``STOAT_*`` references discovered under ``docs/manual/``."""
    documented: set[str] = set()
    if not MANUAL_DIR.is_dir():
        return documented
    for md_file in MANUAL_DIR.rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        documented.update(_STOAT_VAR_PATTERN.findall(text))
    return documented


def test_settings_env_vars_documented_or_known_drift() -> None:
    """Every Settings ``STOAT_*`` var must be documented or in the known-drift list."""
    settings_vars = _settings_env_vars()
    documented = _documented_env_vars()

    undocumented = settings_vars - documented
    new_drift = undocumented - KNOWN_UNDOCUMENTED_SETTINGS_VARS

    for var in sorted(undocumented):
        logger.info(
            "audit_finding",
            severity="P2",
            category="config_drift",
            var=var,
            kind="settings_var_missing_from_manual",
            new_drift=var in new_drift,
        )

    assert not new_drift, (
        "New STOAT_* env vars are not documented in docs/manual/ and are "
        "not listed in KNOWN_UNDOCUMENTED_SETTINGS_VARS:\n"
        + "\n".join(f"  {var}" for var in sorted(new_drift))
    )


def test_known_drift_baseline_still_undocumented() -> None:
    """Drift baseline entries that have since been documented should be removed."""
    settings_vars = _settings_env_vars()
    documented = _documented_env_vars()

    resolved = {
        var
        for var in KNOWN_UNDOCUMENTED_SETTINGS_VARS
        if var in documented or var not in settings_vars
    }
    assert not resolved, (
        "KNOWN_UNDOCUMENTED_SETTINGS_VARS contains entries that have been "
        "documented or removed from Settings — prune the baseline:\n"
        + "\n".join(f"  {var}" for var in sorted(resolved))
    )

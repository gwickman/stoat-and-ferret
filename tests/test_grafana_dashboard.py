"""Validation tests for the Grafana SLI dashboard JSON (BL-290).

These tests guarantee:

- ``grafana/dashboard.json`` is valid JSON and well-formed for Grafana 9.x+.
- The required SLI panels are present (count, titles).
- Every Prometheus metric referenced in panel queries is actually
  registered by the application metrics middleware (no hallucinated
  metric names — NFR-002).
- SLO alert rules for P99 latency and error budget are present.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
DASHBOARD_PATH = REPO_ROOT / "grafana" / "dashboard.json"
METRICS_MODULE = REPO_ROOT / "src" / "stoat_ferret" / "api" / "middleware" / "metrics.py"


# Metric names are valid PromQL identifiers: [a-zA-Z_:][a-zA-Z0-9_:]*
# Histograms expose <name>_bucket, <name>_count, <name>_sum suffixes — strip them
# when reducing back to the registered base name.
_METRIC_TOKEN_RE = re.compile(r"\b([a-zA-Z_:][a-zA-Z0-9_:]*)\b")
_HISTOGRAM_SUFFIXES = ("_bucket", "_count", "_sum")
# PromQL keywords / aggregation operators / function names that look like
# identifiers but are not metrics. Anything matching one of these is filtered
# out before metric-name validation.
_PROMQL_RESERVED = frozenset(
    {
        # functions
        "histogram_quantile",
        "rate",
        "irate",
        "increase",
        "sum",
        "avg",
        "min",
        "max",
        "count",
        "abs",
        "ceil",
        "floor",
        "ln",
        "log2",
        "log10",
        "round",
        "sqrt",
        "clamp_min",
        "clamp_max",
        "delta",
        "deriv",
        "predict_linear",
        # aggregation modifiers / keywords
        "by",
        "without",
        "on",
        "ignoring",
        "group_left",
        "group_right",
        "offset",
        "le",
        "and",
        "or",
        "unless",
        # label names that may appear bare (left side of `=`)
        "status",
        "path",
        "method",
        "job_type",
        "flag",
        "result",
        "service",
        "severity",
    }
)


@pytest.fixture(scope="module")
def dashboard() -> dict:
    """Parsed dashboard JSON document."""
    with DASHBOARD_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def registered_metrics() -> set[str]:
    """Metric names registered in the metrics middleware module.

    Parses the source for ``Counter("name", ...)``, ``Gauge("name", ...)``,
    and ``Histogram("name", ...)`` constructor calls so the truth set
    cannot drift from the dashboard without one or the other being
    edited.
    """
    text = METRICS_MODULE.read_text(encoding="utf-8")
    pattern = re.compile(r"\b(?:Counter|Gauge|Histogram)\(\s*\"([a-zA-Z_:][a-zA-Z0-9_:]*)\"")
    return set(pattern.findall(text))


def _iter_panel_targets(panels: list[dict]):
    """Yield every (panel_title, target_expr) tuple in the dashboard."""
    for panel in panels:
        for target in panel.get("targets", []):
            expr = target.get("expr")
            if expr:
                yield panel.get("title", ""), expr


def _extract_metric_names(expr: str) -> set[str]:
    """Extract candidate metric tokens from a PromQL expression.

    Strips string literals first so values inside label matchers
    (``path="/health"``) do not leak as identifiers.
    """
    cleaned = re.sub(r'"[^"]*"', "", expr)
    cleaned = re.sub(r"'[^']*'", "", cleaned)
    found: set[str] = set()
    for token in _METRIC_TOKEN_RE.findall(cleaned):
        if token in _PROMQL_RESERVED:
            continue
        found.add(token)
    return found


def _resolve_to_registered(token: str, registered: set[str]) -> str | None:
    """Map a PromQL identifier back to its registered metric name.

    Returns the registered name if ``token`` matches directly, or if
    stripping a histogram suffix (``_bucket`` / ``_count`` / ``_sum``)
    yields a registered histogram name. Returns ``None`` if no
    registered metric corresponds to the token.
    """
    if token in registered:
        return token
    for suffix in _HISTOGRAM_SUFFIXES:
        if token.endswith(suffix):
            base = token[: -len(suffix)]
            if base in registered:
                return base
    return None


def test_dashboard_json_valid(dashboard: dict) -> None:
    """Dashboard parses as JSON and exposes the top-level Grafana fields."""
    assert isinstance(dashboard, dict)
    for required_field in ("title", "uid", "schemaVersion", "panels", "alerts"):
        assert required_field in dashboard, f"missing top-level field: {required_field}"
    assert isinstance(dashboard["panels"], list)
    assert isinstance(dashboard["alerts"], list)


def test_dashboard_title(dashboard: dict) -> None:
    """Dashboard title matches the value documented in BL-290 / FR-005."""
    assert dashboard["title"] == "stoat-and-ferret SLI Dashboard"


def test_dashboard_uid_and_schema_version(dashboard: dict) -> None:
    """UID is set (so re-imports update in place) and schema is Grafana 9.x+."""
    assert dashboard["uid"] == "stoat-sli-v043"
    # Grafana 9.x emits schemaVersion 37; 10.x emits 38; 11.x emits 39.
    # Accept >= 37 to keep the dashboard portable across recent majors.
    assert isinstance(dashboard["schemaVersion"], int)
    assert dashboard["schemaVersion"] >= 37


def test_dashboard_panel_count(dashboard: dict) -> None:
    """Dashboard has exactly the 7 SLI panels mandated by FR-002."""
    assert len(dashboard["panels"]) == 7


def test_dashboard_panel_titles(dashboard: dict) -> None:
    """Panels cover all 7 SLI categories from FR-002."""
    titles = [p.get("title", "").lower() for p in dashboard["panels"]]
    required_keywords = (
        "latency",
        "error rate",
        "render throughput",
        "websocket connections",
        "buffer",
        "synthetic checks",
        "active jobs",
    )
    for kw in required_keywords:
        assert any(kw in t for t in titles), f"no panel title contains '{kw}'; titles are {titles}"


def test_panels_have_grid_position(dashboard: dict) -> None:
    """Every panel has a grid position so the imported dashboard renders."""
    for panel in dashboard["panels"]:
        assert "gridPos" in panel, f"panel {panel.get('id')} missing gridPos"
        for axis in ("h", "w", "x", "y"):
            assert axis in panel["gridPos"]


def test_panels_have_targets(dashboard: dict) -> None:
    """Every panel has at least one PromQL target."""
    for panel in dashboard["panels"]:
        targets = panel.get("targets", [])
        assert targets, f"panel {panel.get('id')} '{panel.get('title')}' has no targets"
        for target in targets:
            assert target.get("expr"), (
                f"panel {panel.get('id')} target {target.get('refId')} missing expr"
            )


def test_metric_names_match_emitted(dashboard: dict, registered_metrics: set[str]) -> None:
    """Every Prometheus metric referenced in panels is actually registered.

    Cross-references PromQL identifiers against
    ``src/stoat_ferret/api/middleware/metrics.py``. Standard Prometheus
    HTTP-level metrics (``http_requests_total``,
    ``http_request_duration_seconds``) are also accepted because they are
    emitted by ``MetricsMiddleware`` in the same module.
    """
    truth = set(registered_metrics)
    referenced: set[str] = set()
    unknown: set[str] = set()
    for _title, expr in _iter_panel_targets(dashboard["panels"]):
        for token in _extract_metric_names(expr):
            resolved = _resolve_to_registered(token, truth)
            if resolved is None:
                unknown.add(token)
            else:
                referenced.add(resolved)

    assert not unknown, (
        f"dashboard references metrics not registered in metrics.py: "
        f"{sorted(unknown)}; registered set: {sorted(truth)}"
    )

    # Phase 6 metrics from BL-288 — the dashboard must reference each one
    # somewhere so we have visibility coverage of the full SLI surface.
    phase_6 = {
        "stoat_seed_duration_seconds",
        "stoat_system_state_duration_seconds",
        "stoat_ws_buffer_size",
        "stoat_ws_connected_clients",
        "stoat_active_jobs_count",
        "stoat_feature_flag_state",
        "stoat_migration_duration_seconds",
    }
    missing_phase_6 = phase_6 - referenced
    assert not missing_phase_6, (
        f"dashboard does not reference Phase 6 metrics: {sorted(missing_phase_6)}"
    )


def test_alert_rules_present(dashboard: dict) -> None:
    """Two SLO alert rules: P99 latency > 200ms and error rate > 1%."""
    alerts = dashboard["alerts"]
    assert len(alerts) >= 2

    names = [a.get("name", "") for a in alerts]
    assert any("p99" in n.lower() or "latency" in n.lower() for n in names), (
        f"missing P99 latency alert; names: {names}"
    )
    assert any("error" in n.lower() for n in names), f"missing error budget alert; names: {names}"

    # Each alert exposes its threshold via the model.expr PromQL string —
    # verify both SLO numbers (0.2 seconds, 0.01 ratio) are present.
    exprs = [d.get("model", {}).get("expr", "") for a in alerts for d in a.get("data", [])]
    joined = " ".join(exprs)
    assert "0.2" in joined, f"no alert references the 200ms threshold: {exprs}"
    assert "0.01" in joined, f"no alert references the 1% threshold: {exprs}"


def test_alerts_have_for_clause_and_annotations(dashboard: dict) -> None:
    """Alerts have a ``for`` window (debounce) and human-readable annotations."""
    for alert in dashboard["alerts"]:
        assert alert.get("for"), f"alert {alert.get('name')} missing 'for' clause"
        annotations = alert.get("annotations", {})
        assert annotations.get("summary"), f"alert {alert.get('name')} missing annotations.summary"
        assert annotations.get("description"), (
            f"alert {alert.get('name')} missing annotations.description"
        )

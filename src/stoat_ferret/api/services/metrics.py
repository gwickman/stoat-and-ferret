"""Prometheus metrics for deployment-visibility services (BL-269).

Defines the counter and histogram used by the synthetic monitoring
background task to record probe outcomes. Metrics are registered
against the default Prometheus registry so the existing ``/metrics``
endpoint (mounted in ``stoat_ferret.api.app``) exposes them.

Label cardinality is bounded by design: three probe names
(``health_ready``, ``version``, ``system_state``) × six status values
(``success``, ``degraded``, ``not_implemented``, ``failure``, ``error``,
``timeout``) = 18 label combinations maximum.
"""

from __future__ import annotations

from prometheus_client import Counter, Histogram

SYNTHETIC_CHECK_TOTAL = Counter(
    "stoat_synthetic_check_total",
    "Total synthetic monitoring checks executed.",
    ["check_name", "status"],
)

SYNTHETIC_CHECK_DURATION_SECONDS = Histogram(
    "stoat_synthetic_check_duration_seconds",
    "Duration of synthetic monitoring checks in seconds.",
    ["check_name"],
)


__all__ = [
    "SYNTHETIC_CHECK_DURATION_SECONDS",
    "SYNTHETIC_CHECK_TOTAL",
]

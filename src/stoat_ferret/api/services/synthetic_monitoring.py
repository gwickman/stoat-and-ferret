"""Synthetic monitoring background task (BL-269).

Implements a FastAPI-lifespan-scoped asyncio task that periodically
probes three critical endpoints and emits Prometheus metrics for each
probe. The task is a non-critical self-health check: failures are
logged but never crash the task or affect request serving.

Endpoint response mappings are intentional and documented in
:meth:`SyntheticMonitoringTask._probe`:

- ``HTTP 200`` → ``status="success"``
- ``HTTP 503`` from ``/health/ready`` → ``status="degraded"`` (INFO log,
  not failure) so transient downstream degradation does not page.
- ``HTTP 404`` from ``/api/v1/system/state`` → ``status="not_implemented"``
  (INFO log) as forward-compat for the v039 feature (BL-314).
- Other ``4xx/5xx`` → ``status="failure"``
- Connection errors → ``status="error"``
- ``asyncio.TimeoutError`` → ``status="timeout"``

Task cancellation propagates ``CancelledError`` cleanly; the loop
exits on shutdown without further side effects.
"""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Final

import httpx
import structlog

from stoat_ferret.api.services.metrics import (
    SYNTHETIC_CHECK_DURATION_SECONDS,
    SYNTHETIC_CHECK_TOTAL,
)

logger = structlog.get_logger(__name__)

# Probe endpoints and their canonical check names.
HEALTH_READY_PATH: Final = "/health/ready"
VERSION_PATH: Final = "/api/v1/version"
# /api/v1/system/state lands in v039 via BL-314; 404 in v038 is forward
# compatible and explicitly mapped to status="not_implemented".
SYSTEM_STATE_PATH: Final = "/api/v1/system/state"

DEFAULT_TIMEOUT_SECONDS: Final = 10.0


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single synthetic probe.

    Attributes:
        check_name: One of ``health_ready``, ``version``, or
            ``system_state``.
        status: One of ``success``, ``degraded``, ``not_implemented``,
            ``failure``, ``error``, ``timeout``.
        duration_seconds: Wall-clock duration of the probe, measured
            with :func:`time.perf_counter`.
    """

    check_name: str
    status: str
    duration_seconds: float


class SyntheticMonitoringTask:
    """Periodic probe loop for deployment self-health checks (BL-269).

    The task is constructed from the FastAPI lifespan when the
    :class:`~stoat_ferret.api.settings.Settings` feature flag
    ``synthetic_monitoring`` is enabled. It issues sequential
    ``GET`` requests against three endpoints each interval and records
    the outcome as a Prometheus counter + histogram sample.

    The task does not own the ``httpx.AsyncClient`` — the lifespan
    constructs and closes it — so the same client can be reused across
    many probe iterations without per-iteration connection churn.
    """

    def __init__(
        self,
        *,
        client: httpx.AsyncClient,
        interval_seconds: float = 60.0,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
    ) -> None:
        """Initialise the monitoring task.

        Args:
            client: Pre-configured :class:`httpx.AsyncClient` with
                ``base_url`` pointing at the running application.
                The task issues ``GET`` requests against paths on this
                client; the caller is responsible for closing it.
            interval_seconds: Seconds between probe cycles. Default 60.
                Integration tests override with a shorter interval to
                observe multiple cycles within the test timeout.
            timeout_seconds: Per-request timeout wrapping each probe.
                Default 10 seconds; enforced via
                :func:`asyncio.wait_for`.
        """
        self._client = client
        self._interval = float(interval_seconds)
        self._timeout = float(timeout_seconds)

    async def run(self) -> None:
        """Run the probe loop until cancelled.

        Each iteration executes the three checks sequentially and then
        sleeps ``interval_seconds``. Exceptions raised by individual
        probe methods are contained inside ``_probe`` so the loop keeps
        running. ``CancelledError`` propagates out of the sleep and is
        re-raised after a single INFO log so callers can ``await`` the
        task handle cleanly during shutdown.
        """
        try:
            while True:
                await self.check_health_ready()
                await self.check_version()
                await self.check_system_state()
                await asyncio.sleep(self._interval)
        except asyncio.CancelledError:
            logger.info("synthetic.task_cancelled")
            raise

    async def check_health_ready(self) -> CheckResult:
        """Probe ``/health/ready`` and map 503 to ``degraded``.

        The readiness probe returns 503 during known-degraded states
        (e.g., a pod without FFmpeg). Mapping 503 to ``degraded``
        reserves ``failure`` for unexpected 5xx and connection errors,
        preventing false alerts during routine degraded operation.
        """
        return await self._probe(
            check_name="health_ready",
            path=HEALTH_READY_PATH,
            degraded_http_status=503,
        )

    async def check_version(self) -> CheckResult:
        """Probe ``/api/v1/version`` for build identity verification."""
        return await self._probe(
            check_name="version",
            path=VERSION_PATH,
        )

    async def check_system_state(self) -> CheckResult:
        """Probe ``/api/v1/system/state``; 404 maps to ``not_implemented``.

        The ``/api/v1/system/state`` endpoint lands in v039 (BL-314).
        In v038 the endpoint is absent and returns 404; that response
        is explicitly mapped to ``status="not_implemented"`` so the
        metric neither over-reports success nor triggers ``failure``
        alerts before the endpoint exists.
        """
        return await self._probe(
            check_name="system_state",
            path=SYSTEM_STATE_PATH,
            not_implemented_http_status=404,
        )

    async def _probe(
        self,
        *,
        check_name: str,
        path: str,
        degraded_http_status: int | None = None,
        not_implemented_http_status: int | None = None,
    ) -> CheckResult:
        """Execute one probe against ``path`` and record its outcome.

        Wraps the HTTP request in :func:`asyncio.wait_for` so a hung
        downstream is cut off at ``timeout_seconds``. All non-cancel
        exceptions are trapped so one failing check cannot crash the
        enclosing loop. The counter and histogram are always updated,
        regardless of outcome.

        Args:
            check_name: Probe label recorded in metrics.
            path: Path (appended to client ``base_url``) to GET.
            degraded_http_status: When set and the response matches
                this status code, map to ``status="degraded"`` with an
                INFO log instead of ``failure``.
            not_implemented_http_status: When set and the response
                matches this status code, map to
                ``status="not_implemented"`` with an INFO log instead
                of ``failure``.

        Returns:
            A :class:`CheckResult` describing the outcome.
        """
        start = time.perf_counter()
        status = "failure"
        try:
            response = await asyncio.wait_for(
                self._client.get(path),
                timeout=self._timeout,
            )
            code = response.status_code
            if code == 200:
                status = "success"
            elif degraded_http_status is not None and code == degraded_http_status:
                status = "degraded"
                logger.info(
                    "synthetic.health_degraded",
                    check_name=check_name,
                    reason="downstream_503",
                    http_status=code,
                )
            elif not_implemented_http_status is not None and code == not_implemented_http_status:
                status = "not_implemented"
                logger.info(
                    "synthetic.not_implemented",
                    check_name=check_name,
                    reason=f"endpoint_{code}",
                    http_status=code,
                )
            else:
                status = "failure"
                logger.warning(
                    "synthetic.check_failure",
                    check_name=check_name,
                    http_status=code,
                )
        except asyncio.CancelledError:
            raise
        except asyncio.TimeoutError:
            status = "timeout"
            logger.warning(
                "synthetic.check_timeout",
                check_name=check_name,
                timeout_seconds=self._timeout,
            )
        except httpx.RequestError as exc:
            status = "error"
            logger.warning(
                "synthetic.check_error",
                check_name=check_name,
                error=str(exc),
                error_type=type(exc).__name__,
            )
        except Exception as exc:
            status = "error"
            logger.warning(
                "synthetic.check_error",
                check_name=check_name,
                error=str(exc),
                error_type=type(exc).__name__,
            )
        finally:
            duration = time.perf_counter() - start
            SYNTHETIC_CHECK_TOTAL.labels(check_name=check_name, status=status).inc()
            SYNTHETIC_CHECK_DURATION_SECONDS.labels(check_name=check_name).observe(duration)
        return CheckResult(
            check_name=check_name,
            status=status,
            duration_seconds=duration,
        )


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "HEALTH_READY_PATH",
    "SYSTEM_STATE_PATH",
    "VERSION_PATH",
    "CheckResult",
    "SyntheticMonitoringTask",
]

"""Locust load test harness for stoat-ferret (BL-289).

Three concurrent scenarios:

* :class:`APIUser` exercises read-heavy and write-light HTTP endpoints
  (``GET /api/v1/system/state``, ``GET /api/v1/version``,
  ``POST /api/v1/testing/seed``) at 50 concurrent users with a P99 < 200 ms
  target.
* :class:`WebSocketUser` opens a long-lived ``/ws`` connection and holds it
  for the duration of the run (target: 100 concurrent connections, no
  unexpected disconnects, ``stoat_ws_connected_clients`` gauge tracks ±5%).
* :class:`BatchRenderUser` submits ``POST /api/v1/render/batch`` payloads of
  five jobs each, then polls ``GET /api/v1/render/batch/{batch_id}`` until
  every job reaches a terminal state. Requires the server to run with
  ``STOAT_RENDER_MODE=noop`` so renders short-circuit without spawning
  FFmpeg processes.

Manual execution (one terminal per concurrency role):

.. code-block:: bash

    # Server side
    STOAT_RENDER_MODE=noop STOAT_TESTING_MODE=true \\
        STOAT_SEED_ENDPOINT=true \\
        uv run python -m stoat_ferret.api

    # Driver side, scenario 1 — API users
    locust -f tests/loadtests/locustfile.py -u 50 -r 10 -t 5m \\
        --headless --host http://localhost:8765 APIUser

    # Driver side, scenario 2 — WebSocket storm
    locust -f tests/loadtests/locustfile.py -u 100 -r 20 -t 5m \\
        --headless --host http://localhost:8765 WebSocketUser

    # Driver side, scenario 3 — batch render
    locust -f tests/loadtests/locustfile.py -u 10 -r 1 -t 10m \\
        --headless --host http://localhost:8765 BatchRenderUser

Locust uses gevent for cooperative concurrency, so the WebSocket scenario
relies on the synchronous ``websocket-client`` package rather than
``asyncio``. Both ``locust`` and ``websocket-client`` are installed as dev
dependencies (see ``pyproject.toml``).
"""

from __future__ import annotations

import contextlib
import json
import time
import uuid
from typing import Any

import structlog
from locust import HttpUser, User, between, events, task
from locust.exception import StopUser

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Tunables
# ---------------------------------------------------------------------------

#: Polling interval (seconds) when waiting for batch render completion.
BATCH_POLL_INTERVAL_SECONDS = 0.5

#: Hard timeout (seconds) per batch before giving up — protects the run
#: against pathological queue stalls. Synthetic noop renders complete in
#: well under a second; the generous bound surfaces stalls instead of
#: silently inflating latency stats.
BATCH_TIMEOUT_SECONDS = 60

#: Jobs per batch submission (FR-003 specifies 10 batches × 5).
JOBS_PER_BATCH = 5


# ---------------------------------------------------------------------------
# Scenario 1 — API users
# ---------------------------------------------------------------------------


class APIUser(HttpUser):
    """50 concurrent API users exercising read and seed endpoints (FR-001).

    Each virtual user sleeps 1–3 seconds between tasks to simulate
    interactive client behaviour.
    """

    wait_time = between(1, 3)

    @task(3)
    def get_system_state(self) -> None:
        """Read the in-memory system state aggregate."""
        self.client.get("/api/v1/system/state", name="GET /api/v1/system/state")

    @task(2)
    def get_version(self) -> None:
        """Read the application version metadata."""
        self.client.get("/api/v1/version", name="GET /api/v1/version")

    @task(1)
    def post_seed(self) -> None:
        """Create a seeded project fixture (gated by ``STOAT_TESTING_MODE``)."""
        suffix = uuid.uuid4().hex[:12]
        payload = {
            "fixture_type": "project",
            "name": f"loadtest_{suffix}",
            "data": {"name": f"loadtest_project_{suffix}"},
        }
        self.client.post(
            "/api/v1/testing/seed",
            json=payload,
            name="POST /api/v1/testing/seed",
        )


# ---------------------------------------------------------------------------
# Scenario 2 — WebSocket storm
# ---------------------------------------------------------------------------


class WebSocketUser(User):
    """100 concurrent WebSocket connections held for the run duration (FR-002, FR-004).

    Locust does not ship with first-party WebSocket support, so this user
    drives a synchronous ``websocket-client`` connection over gevent. The
    connection is established in :meth:`on_start` and held until the user
    is stopped; a single ``ws.connect`` event is reported to locust's
    statistics so the dashboard reflects connection success/failure rates.
    """

    # Hold connections open — minimal sleep so on_stop is reachable promptly
    # when the run ends. Reported elsewhere via locust event hooks.
    wait_time = between(5.0, 5.0)

    host: str = "http://localhost:8765"

    def on_start(self) -> None:  # noqa: D401 — locust lifecycle hook
        """Establish a long-lived WebSocket connection to ``/ws``."""
        try:
            from websocket import WebSocket  # type: ignore[import-untyped]
        except ImportError as exc:  # pragma: no cover — exercised at run time
            self._log_request_failure("ws.connect", exc, response_time_ms=0.0)
            raise StopUser() from exc

        ws_url = self._build_ws_url(self.host)
        self._ws: WebSocket | None = WebSocket()
        start = time.perf_counter()
        try:
            self._ws.connect(ws_url, timeout=10)
        except Exception as exc:  # pragma: no cover — surfaced via stats
            elapsed_ms = (time.perf_counter() - start) * 1000.0
            self._log_request_failure("ws.connect", exc, response_time_ms=elapsed_ms)
            self._ws = None
            raise StopUser() from exc

        elapsed_ms = (time.perf_counter() - start) * 1000.0
        self._log_request_success("ws.connect", response_time_ms=elapsed_ms)

    @task
    def hold_connection(self) -> None:
        """No-op task; the user contributes by holding the connection open.

        Reads any inbound messages so the underlying socket buffer drains
        and the connection stays healthy. Heartbeats from the server are
        consumed silently.
        """
        ws = getattr(self, "_ws", None)
        if ws is None:
            return
        try:
            ws.settimeout(1.0)
            ws.recv()
        except Exception:
            # Timeout / read errors are expected — the connection is held
            # for liveness, not message exchange.
            pass

    def on_stop(self) -> None:  # noqa: D401 — locust lifecycle hook
        """Close the long-lived WebSocket connection."""
        ws = getattr(self, "_ws", None)
        if ws is None:
            return
        with contextlib.suppress(Exception):
            ws.close()

    @staticmethod
    def _build_ws_url(host: str) -> str:
        if host.startswith("https://"):
            return "wss://" + host[len("https://") :].rstrip("/") + "/ws"
        if host.startswith("http://"):
            return "ws://" + host[len("http://") :].rstrip("/") + "/ws"
        return "ws://" + host.rstrip("/") + "/ws"

    def _log_request_success(self, name: str, *, response_time_ms: float) -> None:
        events.request.fire(
            request_type="WS",
            name=name,
            response_time=response_time_ms,
            response_length=0,
            exception=None,
            context=self.context(),
        )

    def _log_request_failure(
        self,
        name: str,
        exc: BaseException,
        *,
        response_time_ms: float,
    ) -> None:
        events.request.fire(
            request_type="WS",
            name=name,
            response_time=response_time_ms,
            response_length=0,
            exception=exc,
            context=self.context(),
        )


# ---------------------------------------------------------------------------
# Scenario 3 — batch render
# ---------------------------------------------------------------------------


def _make_render_plan(project_id: str) -> dict[str, Any]:
    """Build a minimal render plan accepted by the noop short-circuit."""
    return {
        "total_duration": 1.0,
        "segments": [],
        "settings": {
            "output_format": "mp4",
            "width": 1920,
            "height": 1080,
            "codec": "libx264",
            "quality_preset": "standard",
            "fps": 30.0,
        },
        "project_id": project_id,
    }


class BatchRenderUser(HttpUser):
    """10 concurrent users submitting batches of 5 jobs each (FR-003).

    Each task submits a batch via ``POST /api/v1/render/batch`` and polls
    the batch status endpoint until every job reaches a terminal state.
    Server must run with ``STOAT_RENDER_MODE=noop`` so jobs short-circuit
    without invoking FFmpeg.
    """

    wait_time = between(1, 2)

    @task
    def submit_and_poll_batch(self) -> None:
        """Submit a batch of five render jobs and wait for terminal status."""
        suffix = uuid.uuid4().hex[:8]
        project_id = f"loadtest_project_{suffix}"
        jobs = [
            {
                "project_id": project_id,
                "output_path": f"/tmp/loadtest_{suffix}_{i}.mp4",
                "quality": "standard",
            }
            for i in range(JOBS_PER_BATCH)
        ]
        payload = {"jobs": jobs}

        with self.client.post(
            "/api/v1/render/batch",
            json=payload,
            name="POST /api/v1/render/batch",
            catch_response=True,
        ) as response:
            if response.status_code != 202:
                response.failure(f"unexpected status {response.status_code}: {response.text[:200]}")
                return
            batch_id = response.json().get("batch_id")
            if not batch_id:
                response.failure("missing batch_id in response")
                return

        self._wait_for_terminal_state(batch_id)

    def _wait_for_terminal_state(self, batch_id: str) -> None:
        """Poll a batch until every job reaches a terminal status.

        Records each poll as its own request so per-poll latency is captured
        in the locust statistics. Bails out with a recorded failure when
        the batch fails to settle within :data:`BATCH_TIMEOUT_SECONDS`.
        """
        deadline = time.monotonic() + BATCH_TIMEOUT_SECONDS
        url = f"/api/v1/render/batch/{batch_id}"
        while time.monotonic() < deadline:
            with self.client.get(
                url,
                name="GET /api/v1/render/batch/{batch_id}",
                catch_response=True,
            ) as response:
                if response.status_code != 200:
                    response.failure(
                        f"unexpected status {response.status_code}: {response.text[:200]}"
                    )
                    return
                payload = response.json()
                statuses = {job.get("status") for job in payload.get("jobs", [])}
                if statuses and statuses.issubset({"completed", "failed"}):
                    return
            time.sleep(BATCH_POLL_INTERVAL_SECONDS)

        events.request.fire(
            request_type="batch",
            name="batch.terminal_timeout",
            response_time=BATCH_TIMEOUT_SECONDS * 1000.0,
            response_length=0,
            exception=TimeoutError(f"batch {batch_id} did not terminate"),
            context={},
        )


# ---------------------------------------------------------------------------
# Run lifecycle hooks
# ---------------------------------------------------------------------------


@events.test_start.add_listener
def _on_test_start(environment: Any, **_kwargs: Any) -> None:
    """Log structured event when the load run begins."""
    logger.info(
        "load_test_start",
        host=getattr(environment, "host", None),
        run_id=str(uuid.uuid4()),
    )


@events.test_stop.add_listener
def _on_test_stop(environment: Any, **_kwargs: Any) -> None:
    """Log a structured run summary when the load run ends."""
    stats = environment.stats.total
    logger.info(
        "load_test_stop",
        total_requests=stats.num_requests,
        total_failures=stats.num_failures,
        median_ms=stats.median_response_time,
        p95_ms=stats.get_response_time_percentile(0.95),
        p99_ms=stats.get_response_time_percentile(0.99),
    )
    # Echo a JSON summary on stdout so headless runs surface a machine-
    # readable result line that's easy to grep into the results table.
    print(  # noqa: T201
        "LOADTEST_SUMMARY "
        + json.dumps(
            {
                "total_requests": stats.num_requests,
                "total_failures": stats.num_failures,
                "median_ms": stats.median_response_time,
                "p95_ms": stats.get_response_time_percentile(0.95),
                "p99_ms": stats.get_response_time_percentile(0.99),
            }
        )
    )

#!/usr/bin/env python3
"""Poll a generic queue job (scan/proxy/waveform/thumbnail) until completion.

Long-poll wrapper around ``GET /api/v1/jobs/{job_id}/wait``.

**Scope:** This script covers only the GENERIC job queue — jobs created by
scan, proxy, waveform, and thumbnail operations.  Render jobs are NOT in the
generic queue (they live in ``RenderQueue``/``AsyncRenderRepository``).  Passing
a render job ID returns HTTP 404 from this endpoint.

To poll render status, use the render endpoint directly::

    GET /api/v1/render/{job_id}

Dependencies: stdlib only (``urllib.request``, ``argparse``, ``json``, ``sys``).
No third-party HTTP libraries are imported — this is enforced by the v042
quality gate ``grep -E "^import (requests|httpx)" scripts/examples/wait-for-render.py``.

Usage:
    python scripts/examples/wait-for-render.py --job-id <job_id>
    python scripts/examples/wait-for-render.py \\
        --host localhost --port 8765 --job-id job_abc --timeout 30

Exit codes:
    0 — terminal status received (``complete``, ``failed``, ``timeout``,
        ``cancelled``) OR HTTP 408 (``JOB_WAIT_TIMEOUT``) returned by the
        server (the job itself is still running; the timeout is client-side).
    1 — render job ID supplied (HTTP 404 from generic queue); user is directed
        to ``GET /api/v1/render/{job_id}``.
    2 — other HTTP/network error.

The terminal/timeout JSON payload is printed to stdout. Pipe to ``jq`` to
extract specific fields (e.g. ``jq -r '.status'`` or ``jq -r '.result.output_path'``).
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Long-poll a stoat-and-ferret async job to terminal state.",
    )
    parser.add_argument("--host", default="localhost", help="API host (default: localhost)")
    parser.add_argument("--port", type=int, default=8765, help="API port (default: 8765)")
    parser.add_argument("--job-id", required=True, help="Job ID returned by an async submit")
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Server-side wait window in seconds, clamped to [1, 3600] (default: 30)",
    )
    return parser.parse_args(argv)


def wait_for_job(host: str, port: int, job_id: str, timeout: float) -> int:
    """Issue a single long-poll wait request and print the response.

    Returns the process exit code: 0 on terminal status or HTTP 408 timeout,
    1 on HTTP 404 (render job detected), 2 on other transport errors.
    """
    url = f"http://{host}:{port}/api/v1/jobs/{job_id}/wait?timeout={timeout}"
    # Buffer slightly beyond the server-side timeout so the socket does not
    # close before the server can reply with 200 or 408.
    socket_timeout = timeout + 5.0

    request = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=socket_timeout) as response:
            body = response.read().decode("utf-8")
            print(body)
            return 0
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        if err.code == 408:
            # JOB_WAIT_TIMEOUT — job is still running; client decides next move.
            print(body)
            return 0
        if err.code == 404:
            print(
                f"Job '{job_id}' not found in the generic queue. "
                f"If this is a render job, poll render status via: "
                f"GET /api/v1/render/{job_id}",
                file=sys.stderr,
            )
            return 1
        print(
            json.dumps({"error": "http_error", "status": err.code, "body": body}),
            file=sys.stderr,
        )
        return 2
    except urllib.error.URLError as err:
        print(
            json.dumps({"error": "url_error", "reason": str(err.reason)}),
            file=sys.stderr,
        )
        return 2


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    args = parse_args(argv)
    return wait_for_job(args.host, args.port, args.job_id, args.timeout)


if __name__ == "__main__":
    sys.exit(main())

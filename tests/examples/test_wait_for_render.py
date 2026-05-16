"""Unit tests for scripts/examples/wait-for-render.py.

Verifies the 404 error guard added in v064-005 (BL-359-AC-2):
when a render job ID causes HTTP 404 from the generic queue, the script
prints a redirect message to stderr and exits with code 1.
"""

from __future__ import annotations

import importlib.util
import io
import pathlib
import urllib.error
from typing import Any
from unittest.mock import MagicMock, patch

# Load wait-for-render.py as a module via importlib (avoids import name collision
# with the hyphenated filename).
_SCRIPT = (
    pathlib.Path(__file__).parent.parent.parent / "scripts" / "examples" / "wait-for-render.py"
)
_spec = importlib.util.spec_from_file_location("wait_for_render", _SCRIPT)
assert _spec is not None and _spec.loader is not None
wait_for_render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wait_for_render)  # type: ignore[arg-type]


def _make_http_error(code: int, body: bytes = b"Not Found") -> urllib.error.HTTPError:
    """Construct a minimal HTTPError suitable for urlopen mock."""
    err = urllib.error.HTTPError(
        url="http://localhost:8765/api/v1/jobs/abc/wait",
        code=code,
        msg="",
        hdrs=MagicMock(),  # type: ignore[arg-type]
        fp=io.BytesIO(body),
    )
    return err


def test_wait_for_job_404_prints_redirect_and_exits_1(capsys: Any) -> None:
    """HTTP 404 from generic queue triggers redirect message (to stderr) and exit code 1."""
    job_id = "render-job-abc-123"
    with patch("urllib.request.urlopen", side_effect=_make_http_error(404)):
        exit_code = wait_for_render.wait_for_job("localhost", 8765, job_id, 30.0)

    captured = capsys.readouterr()
    assert exit_code == 1
    assert "GET /api/v1/render/" + job_id in captured.err
    assert captured.out == ""


def test_wait_for_job_other_http_error_exits_2(capsys: Any) -> None:
    """HTTP 500 exits with code 2 and writes JSON error to stderr."""
    with patch("urllib.request.urlopen", side_effect=_make_http_error(500, b"Server Error")):
        exit_code = wait_for_render.wait_for_job("localhost", 8765, "some-job", 30.0)

    captured = capsys.readouterr()
    assert exit_code == 2
    assert "http_error" in captured.err
    assert captured.out == ""


def test_wait_for_job_408_prints_body_and_exits_0(capsys: Any) -> None:
    """HTTP 408 (JOB_WAIT_TIMEOUT) prints body to stdout and exits 0."""
    body = b'{"detail": {"code": "JOB_WAIT_TIMEOUT", "message": "timed out"}}'
    with patch("urllib.request.urlopen", side_effect=_make_http_error(408, body)):
        exit_code = wait_for_render.wait_for_job("localhost", 8765, "some-job", 30.0)

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "JOB_WAIT_TIMEOUT" in captured.out
    assert captured.err == ""

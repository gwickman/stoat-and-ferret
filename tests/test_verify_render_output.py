# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Regression tests for scripts/verify_render_output.py (BL-620).

Confirms that default mode checks fields actually present in RenderJobResponse
(status, output_path, progress) and NOT fields that only exist on the /evidence
endpoint (exit_code, output_size_bytes).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Import via path so the test doesn't require the scripts/ dir to be a package.
scripts_dir = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(scripts_dir))
from verify_render_output import _validate_host, main  # noqa: E402

# Shared test-vector table (requirements.md "Parity Requirements") — applied
# identically across test_verify_render_output.py, test_wait_for_render.py,
# and test_dump_ws_events.py so a bypass found against one script is
# mechanically checked against the other two.
HOST_ALLOWLIST_VECTORS = [
    ("http://localhost:8765", True),
    ("http://127.0.0.1:8765", True),
    ("http://evil.com:8765", False),
    ("http://localhost.evil.example:8765", False),
    ("http://127.0.0.1.evil.example:8765", False),
    ("http://localhost@evil.example", False),
    ("http://[::1]:8765/", True),
    ("file:///etc/passwd", False),
]


def _mock_response(data: dict) -> MagicMock:
    body = json.dumps(data).encode()
    resp = MagicMock()
    resp.read = MagicMock(return_value=body)
    resp.__enter__ = MagicMock(return_value=resp)
    resp.__exit__ = MagicMock(return_value=False)
    return resp


class TestDefaultMode:
    """Default mode (no --full) uses GET /render/{job_id} and checks status/output_path/progress."""

    def _run(self, data: dict, extra_args: list[str] | None = None) -> int:
        with (
            patch(
                "urllib.request.urlopen",
                return_value=_mock_response(data),
            ),
            patch(
                "sys.argv",
                ["verify_render_output.py", "--job-id", "job-123", *(extra_args or [])],
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        return exc_info.value.code

    def test_pass_when_completed_and_populated(self) -> None:
        code = self._run(
            {"status": "completed", "output_path": "/renders/out.mp4", "progress": 1.0}
        )
        assert code == 0

    def test_fail_when_status_not_completed(self) -> None:
        code = self._run({"status": "running", "output_path": "/renders/out.mp4", "progress": 0.5})
        assert code == 1

    def test_fail_when_output_path_empty(self) -> None:
        code = self._run({"status": "completed", "output_path": "", "progress": 1.0})
        assert code == 1

    def test_fail_when_progress_not_1(self) -> None:
        code = self._run(
            {"status": "completed", "output_path": "/renders/out.mp4", "progress": 0.9}
        )
        assert code == 1

    def test_pass_even_when_exit_code_absent(self) -> None:
        """exit_code is NOT in RenderJobResponse — default mode must not assert it."""
        code = self._run(
            {"status": "completed", "output_path": "/renders/out.mp4", "progress": 1.0}
        )
        # No exit_code in response — should still PASS (the pre-fix bug caused FAIL here)
        assert code == 0

    def test_pass_even_when_output_size_bytes_absent(self) -> None:
        """output_size_bytes is NOT in RenderJobResponse — default mode must not assert it."""
        code = self._run(
            {"status": "completed", "output_path": "/renders/out.mp4", "progress": 1.0}
        )
        assert code == 0


class TestFullMode:
    """--full mode uses the evidence endpoint; checks command_args, exit_code, output_size_bytes."""

    def _run(self, data: dict) -> int:
        with (
            patch(
                "urllib.request.urlopen",
                return_value=_mock_response(data),
            ),
            patch(
                "sys.argv",
                ["verify_render_output.py", "--job-id", "job-123", "--full"],
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        return exc_info.value.code

    def test_pass_when_all_evidence_fields_present(self) -> None:
        code = self._run(
            {
                "command_args": ["ffmpeg", "-i", "input.mp4", "out.mp4"],
                "exit_code": 0,
                "output_size_bytes": 123456,
            }
        )
        assert code == 0

    def test_fail_when_exit_code_absent(self) -> None:
        code = self._run(
            {
                "command_args": ["ffmpeg"],
                "exit_code": None,
                "output_size_bytes": 123456,
            }
        )
        assert code == 1

    def test_fail_when_command_args_empty(self) -> None:
        code = self._run(
            {
                "command_args": [],
                "exit_code": 0,
                "output_size_bytes": 123456,
            }
        )
        assert code == 1

    def test_fail_when_output_size_bytes_absent(self) -> None:
        code = self._run(
            {
                "command_args": ["ffmpeg"],
                "exit_code": 0,
                "output_size_bytes": None,
            }
        )
        assert code == 1


class TestHostAllowlist:
    """SSRF host-allowlist validation (BL-641) — must reject before any network call."""

    @pytest.mark.parametrize("url,expect_accept", HOST_ALLOWLIST_VECTORS)
    def test_validate_host_vector_table(self, url: str, expect_accept: bool) -> None:
        if expect_accept:
            _validate_host(url, {"http", "https"})  # must not raise
        else:
            with pytest.raises(SystemExit):
                _validate_host(url, {"http", "https"})

    def test_non_allowlisted_host_exits_before_network_call(self) -> None:
        with (
            patch("urllib.request.urlopen") as mock_urlopen,
            patch(
                "sys.argv",
                ["verify_render_output.py", "--job-id", "job-123", "--base-url", "http://evil.com"],
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code != 0
        mock_urlopen.assert_not_called()

    def test_non_http_scheme_rejected_before_network_call(self) -> None:
        with (
            patch("urllib.request.urlopen") as mock_urlopen,
            patch(
                "sys.argv",
                [
                    "verify_render_output.py",
                    "--job-id",
                    "job-123",
                    "--base-url",
                    "file:///etc/passwd",
                ],
            ),
            pytest.raises(SystemExit) as exc_info,
        ):
            main()
        assert exc_info.value.code != 0
        mock_urlopen.assert_not_called()

    def test_env_override_allows_listed_non_loopback_host(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STOAT_RENDER_VERIFY_ALLOWED_HOSTS", "staging.internal")
        _validate_host("http://staging.internal:8765", {"http", "https"})  # must not raise

    def test_env_override_is_not_a_bare_boolean(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setting the env var to a truthy-looking string must not disable the allowlist."""
        monkeypatch.setenv("STOAT_RENDER_VERIFY_ALLOWED_HOSTS", "true")
        with pytest.raises(SystemExit):
            _validate_host("http://evil.com", {"http", "https"})

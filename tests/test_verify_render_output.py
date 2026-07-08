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
from verify_render_output import main  # noqa: E402


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

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""TOCTOU regression tests for the /api/v1/videos/scan endpoint (BL-699).

Verifies that a symlink retargeted outside the allowed scan root between
endpoint validation and worker execution is caught by the worker-side
re-validation in make_scan_handler.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from stoat_ferret.api.services.scan import make_scan_handler
from stoat_ferret.db.async_repository import AsyncInMemoryVideoRepository


@pytest.mark.skipif(sys.platform == "win32", reason="symlinks require elevated privileges")
async def test_scan_toctou_worker_rejects_retargeted_symlink(tmp_path: Path) -> None:
    """Worker re-validates after a symlink is retargeted outside the allowed root.

    Simulates a TOCTOU attack where:
    1. The endpoint validates /allowed/legit (a real dir) — passes.
    2. The caller replaces /allowed/legit with a symlink to /outside.
    3. The worker re-resolves and re-validates — must fail closed.
    """
    allowed = tmp_path / "allowed"
    outside = tmp_path / "outside"
    allowed.mkdir()
    outside.mkdir()

    legit = allowed / "legit"
    legit.mkdir()

    repo = AsyncInMemoryVideoRepository()
    mock_settings = MagicMock()
    mock_settings.allowed_scan_roots = [str(allowed)]
    mock_settings.proxy_auto_generate = False

    # Simulate TOCTOU: endpoint validated legit/ as a real dir; now retarget to outside.
    legit.rmdir()
    legit.symlink_to(outside)

    handler = make_scan_handler(repo)

    with (
        patch("stoat_ferret.api.services.scan.get_settings", return_value=mock_settings),
        pytest.raises(ValueError, match="not under any allowed scan root"),
    ):
        await handler("scan", {"path": str(legit)})

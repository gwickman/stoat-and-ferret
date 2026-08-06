# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

from __future__ import annotations

from pathlib import Path

import pytest

_ACCEPTANCE_DIR = Path(__file__).parent


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    # Each acceptance test does a full E2E render; the internal _poll_render_job
    # timeout is 300s, so 600s gives adequate headroom over the global --timeout=120.
    for item in items:
        if Path(str(item.fspath)).is_relative_to(_ACCEPTANCE_DIR):
            item.add_marker(pytest.mark.timeout(600))

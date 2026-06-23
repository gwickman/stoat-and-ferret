# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Chatbot scenario runner hook for Release 2 scaffold.

Delegates to uc_cap_master for the full delivery profile mastering scenario and
uc_media_mps_001 for the UC-MEDIA-MPS-001 session build and master workflow.
"""

from __future__ import annotations

from tests.chatbot.scenarios.uc_media_mps_001 import run_uc_media_mps_001


async def run_r2_scenario(base_url: str) -> dict:
    """Chatbot scenario runner hook for Release 2 scaffold.

    Delegates to uc_media_mps_001.run_uc_media_mps_001() for the full
    UC-MEDIA-MPS-001 session build and master scenario.
    """
    return await run_uc_media_mps_001(base_url)

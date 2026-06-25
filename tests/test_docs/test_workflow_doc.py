# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""CI grep gate: assert required verification tokens exist in the chatbot workflow doc (BL-506)."""

from __future__ import annotations

from pathlib import Path


def test_chatbot_workflow_contains_required_tokens() -> None:
    path = Path("docs/design/chatbot-driven-testing/example-workflow.md")
    content = path.read_text(encoding="utf-8")
    required_tokens = ["SSIM", "sobel", "edge magnitude", "mean luminance", "tempfile.mkdtemp"]
    for token in required_tokens:
        assert token in content, f"Missing required token: {token}"

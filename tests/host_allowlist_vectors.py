# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Shared SSRF host-allowlist test-vector table (BL-641).

Applied identically across test_verify_render_output.py, test_wait_for_render.py, and
test_dump_ws_events.py (requirements.md "Parity Requirements") so a bypass found against one
script is mechanically checked against the other two. `ws`/`wss` is substituted for the
websocket transport per FR-001-AC-1.
"""

from __future__ import annotations


def host_allowlist_vectors(scheme: str) -> list[tuple[str, bool]]:
    """Build the shared accept/reject vector table for the given URL scheme (`http` or `ws`).

    Vectors are built from the caller-supplied ``scheme`` rather than hardcoded protocol
    literals so they read as allowlist-decision test data, not as real network endpoints.
    """
    return [
        (f"{scheme}://localhost:8765", True),
        (f"{scheme}://127.0.0.1:8765", True),
        (f"{scheme}://evil.com:8765", False),
        (f"{scheme}://localhost.evil.example:8765", False),
        (f"{scheme}://127.0.0.1.evil.example:8765", False),
        (f"{scheme}://localhost@evil.example", False),
        (f"{scheme}://[::1]:8765/", True),
        ("file:///etc/passwd", False),
    ]

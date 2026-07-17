# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""SSRF host-allowlist regression tests for scripts/examples/dump-ws-events.py (BL-641).

Confirms scheme+hostname validation (ws/wss) runs before any WebSocket
connection attempt.
"""

from __future__ import annotations

import asyncio
import importlib.util
import pathlib
from unittest.mock import patch

import pytest

# Load dump-ws-events.py as a module via importlib (avoids import name collision
# with the hyphenated filename).
_SCRIPT = pathlib.Path(__file__).parent.parent / "scripts" / "examples" / "dump-ws-events.py"
_spec = importlib.util.spec_from_file_location("dump_ws_events_ssrf", _SCRIPT)
assert _spec is not None and _spec.loader is not None
dump_ws_events = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dump_ws_events)  # type: ignore[arg-type]

# Shared test-vector table (requirements.md "Parity Requirements") — applied
# identically across test_verify_render_output.py, test_wait_for_render.py,
# and test_dump_ws_events.py so a bypass found against one script is
# mechanically checked against the other two. `ws`/`wss` substituted for the
# websocket transport per FR-001-AC-1.
HOST_ALLOWLIST_VECTORS = [
    ("ws://localhost:8765", True),
    ("ws://127.0.0.1:8765", True),
    ("ws://evil.com:8765", False),
    ("ws://localhost.evil.example:8765", False),
    ("ws://127.0.0.1.evil.example:8765", False),
    ("ws://localhost@evil.example", False),
    ("ws://[::1]:8765/", True),
    ("file:///etc/passwd", False),
]


class _FakeWSConnection:
    """Minimal async context manager standing in for a websockets connection."""

    async def __aenter__(self) -> _FakeWSConnection:
        return self

    async def __aexit__(self, *exc_info: object) -> bool:
        return False

    def __aiter__(self) -> _FakeWSConnection:
        return self

    async def __anext__(self) -> str:
        raise StopAsyncIteration


class TestHostAllowlist:
    """SSRF host-allowlist validation (BL-641) — must reject before any connection."""

    @pytest.mark.parametrize("url,expect_accept", HOST_ALLOWLIST_VECTORS)
    def test_validate_host_vector_table(self, url: str, expect_accept: bool) -> None:
        if expect_accept:
            dump_ws_events._validate_host(url, {"ws", "wss"})  # must not raise
        else:
            with pytest.raises(SystemExit):
                dump_ws_events._validate_host(url, {"ws", "wss"})

    def test_non_allowlisted_host_exits_before_connect(self) -> None:
        with (
            patch.object(dump_ws_events.websockets, "connect") as mock_connect,
            pytest.raises(SystemExit),
        ):
            asyncio.run(dump_ws_events.stream_events("evil.com", 8765, None))
        mock_connect.assert_not_called()

    def test_hostname_trick_embedded_auth_rejected_before_connect(self) -> None:
        with (
            patch.object(dump_ws_events.websockets, "connect") as mock_connect,
            pytest.raises(SystemExit),
        ):
            asyncio.run(dump_ws_events.stream_events("localhost@evil.example", 8765, None))
        mock_connect.assert_not_called()

    def test_hostname_trick_subdomain_rejected_before_connect(self) -> None:
        with (
            patch.object(dump_ws_events.websockets, "connect") as mock_connect,
            pytest.raises(SystemExit),
        ):
            asyncio.run(dump_ws_events.stream_events("localhost.evil.example", 8765, None))
        mock_connect.assert_not_called()

    def test_bracketed_ipv6_loopback_accepted(self) -> None:
        with patch.object(
            dump_ws_events.websockets, "connect", return_value=_FakeWSConnection()
        ) as mock_connect:
            result = asyncio.run(dump_ws_events.stream_events("[::1]", 8765, None))
        mock_connect.assert_called_once()
        assert result == 0

    def test_env_override_allows_listed_non_loopback_host(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STOAT_RENDER_VERIFY_ALLOWED_HOSTS", "staging.internal")
        dump_ws_events._validate_host("ws://staging.internal:8765", {"ws", "wss"})  # must not raise

    def test_env_override_is_not_a_bare_boolean(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setting the env var to a truthy-looking string must not disable the allowlist."""
        monkeypatch.setenv("STOAT_RENDER_VERIFY_ALLOWED_HOSTS", "true")
        with pytest.raises(SystemExit):
            dump_ws_events._validate_host("ws://evil.com", {"ws", "wss"})

    def test_default_host_still_reaches_connect(self) -> None:
        """Existing default (--host localhost) must remain unaffected (FR-006-AC-1)."""
        with patch.object(
            dump_ws_events.websockets, "connect", return_value=_FakeWSConnection()
        ) as mock_connect:
            result = asyncio.run(dump_ws_events.stream_events("localhost", 8765, None))
        mock_connect.assert_called_once()
        assert result == 0

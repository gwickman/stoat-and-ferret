# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""SSRF host-allowlist regression tests for scripts/examples/wait-for-render.py (BL-641).

Confirms scheme+hostname validation runs before any network call. See
tests/examples/test_wait_for_render.py for the pre-existing 404-guard tests
(BL-359-AC-2) — this file covers only the allowlist behavior added in v106.
"""

from __future__ import annotations

import importlib.util
import pathlib
from unittest.mock import patch

import pytest

from tests.host_allowlist_vectors import host_allowlist_vectors

# Load wait-for-render.py as a module via importlib (avoids import name collision
# with the hyphenated filename).
_SCRIPT = pathlib.Path(__file__).parent.parent / "scripts" / "examples" / "wait-for-render.py"
_spec = importlib.util.spec_from_file_location("wait_for_render_ssrf", _SCRIPT)
assert _spec is not None and _spec.loader is not None
wait_for_render = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(wait_for_render)  # type: ignore[arg-type]

# Shared test-vector table (requirements.md "Parity Requirements", tests/host_allowlist_vectors.py)
# — applied identically across test_verify_render_output.py, test_wait_for_render.py, and
# test_dump_ws_events.py so a bypass found against one script is mechanically checked against
# the other two.
HOST_ALLOWLIST_VECTORS = host_allowlist_vectors("http")


class TestHostAllowlist:
    """SSRF host-allowlist validation (BL-641) — must reject before any network call."""

    @pytest.mark.parametrize("url,expect_accept", HOST_ALLOWLIST_VECTORS)
    def test_validate_host_vector_table(self, url: str, expect_accept: bool) -> None:
        if expect_accept:
            wait_for_render._validate_host(url, {"http", "https"})  # must not raise
        else:
            with pytest.raises(SystemExit):
                wait_for_render._validate_host(url, {"http", "https"})

    def test_non_allowlisted_host_exits_before_network_call(self) -> None:
        with (
            patch("urllib.request.urlopen") as mock_urlopen,
            pytest.raises(SystemExit),
        ):
            wait_for_render.wait_for_job("evil.com", 8765, "job-123", 30.0)
        mock_urlopen.assert_not_called()

    def test_hostname_trick_embedded_auth_rejected_before_network_call(self) -> None:
        """`--host localhost@evil.example` builds a URL with embedded auth; parsed
        hostname is `evil.example`, not `localhost` — must be rejected."""
        with (
            patch("urllib.request.urlopen") as mock_urlopen,
            pytest.raises(SystemExit),
        ):
            wait_for_render.wait_for_job("localhost@evil.example", 8765, "job-123", 30.0)
        mock_urlopen.assert_not_called()

    def test_hostname_trick_subdomain_rejected_before_network_call(self) -> None:
        with (
            patch("urllib.request.urlopen") as mock_urlopen,
            pytest.raises(SystemExit),
        ):
            wait_for_render.wait_for_job("localhost.evil.example", 8765, "job-123", 30.0)
        mock_urlopen.assert_not_called()

    def test_bracketed_ipv6_loopback_accepted(self) -> None:
        with patch("urllib.request.urlopen") as mock_urlopen:
            wait_for_render.wait_for_job("[::1]", 8765, "job-123", 30.0)
        mock_urlopen.assert_called_once()

    def test_env_override_allows_listed_non_loopback_host(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setenv("STOAT_RENDER_VERIFY_ALLOWED_HOSTS", "staging.internal")
        # must not raise
        wait_for_render._validate_host(
            "http://staging.internal:8765",  # NOSONAR (S5332): test vector
            {"http", "https"},
        )

    def test_env_override_is_not_a_bare_boolean(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Setting the env var to a truthy-looking string must not disable the allowlist."""
        monkeypatch.setenv("STOAT_RENDER_VERIFY_ALLOWED_HOSTS", "true")
        with pytest.raises(SystemExit):
            wait_for_render._validate_host(
                "http://evil.com",  # NOSONAR (S5332): test vector
                {"http", "https"},
            )

    def test_default_host_still_reaches_network_call(self) -> None:
        """Existing default (--host localhost) must remain unaffected (FR-006-AC-1)."""
        with patch("urllib.request.urlopen") as mock_urlopen:
            wait_for_render.wait_for_job("localhost", 8765, "job-123", 30.0)
        mock_urlopen.assert_called_once()

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Smoke test to verify pytest is properly configured."""

from __future__ import annotations


def test_smoke() -> None:
    """Verify pytest runs."""


def test_import_stoat_ferret() -> None:
    """Verify the stoat_ferret package can be imported."""
    from importlib.metadata import version as _metadata_version

    import stoat_ferret

    expected = _metadata_version("stoat-ferret")
    assert stoat_ferret.__version__ == expected, (
        f"__version__ {stoat_ferret.__version__!r} != package metadata {expected!r}"
    )


def test_import_stoat_ferret_core() -> None:
    """Verify the stoat_ferret_core package can be imported."""
    import stoat_ferret_core

    # health_check should be exported
    assert hasattr(stoat_ferret_core, "health_check")


def test_stoat_ferret_core_health_check() -> None:
    """Verify health_check returns expected status."""
    from stoat_ferret_core import health_check

    result = health_check()
    assert result == "stoat_ferret_core OK"

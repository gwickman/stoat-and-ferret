"""Smoke test to verify pytest is properly configured."""

from __future__ import annotations

import pytest


def test_smoke() -> None:
    """Verify pytest runs."""
    assert True


def test_import_stoat_ferret() -> None:
    """Verify the stoat_ferret package can be imported."""
    import stoat_ferret

    assert stoat_ferret.__version__ == "0.1.0"


def test_import_stoat_ferret_core() -> None:
    """Verify the stoat_ferret_core package can be imported."""
    import stoat_ferret_core

    # health_check should be exported
    assert hasattr(stoat_ferret_core, "health_check")


def test_stoat_ferret_core_health_check_stub() -> None:
    """Verify health_check raises when native module not built."""
    from stoat_ferret_core import health_check

    # When native module isn't built, health_check should raise RuntimeError
    with pytest.raises(RuntimeError, match="native extension not built"):
        health_check()

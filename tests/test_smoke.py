"""Smoke test to verify pytest is properly configured."""

from __future__ import annotations


def test_smoke() -> None:
    """Verify pytest runs."""
    assert True


def test_import_stoat_ferret() -> None:
    """Verify the stoat_ferret package can be imported."""
    import stoat_ferret

    assert stoat_ferret.__version__ == "0.1.0"

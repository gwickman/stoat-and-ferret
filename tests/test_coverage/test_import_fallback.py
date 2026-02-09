"""Tests for the ImportError fallback path in stoat_ferret_core.__init__.

When the Rust extension (_core) is not built, the package should fall back
to stub functions that raise RuntimeError with an informative message.
"""

from __future__ import annotations

import importlib
import sys
from unittest.mock import patch

import pytest


def _reload_with_import_error():
    """Reload stoat_ferret_core with _core import blocked.

    Temporarily removes stoat_ferret_core modules from sys.modules and
    patches the import of stoat_ferret_core._core to raise ImportError,
    forcing the fallback path.

    Returns the reloaded module.
    """
    # Save and remove cached modules so importlib.reload re-executes the module
    saved = {}
    for key in list(sys.modules):
        if key.startswith("stoat_ferret_core"):
            saved[key] = sys.modules.pop(key)

    original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

    def _blocking_import(name, *args, **kwargs):
        if name == "stoat_ferret_core._core":
            raise ImportError("Simulated: native extension not built")
        return original_import(name, *args, **kwargs)

    try:
        with patch("builtins.__import__", side_effect=_blocking_import):
            import stoat_ferret_core

            importlib.reload(stoat_ferret_core)
            return stoat_ferret_core
    finally:
        # Restore original modules so other tests are not affected
        for key in list(sys.modules):
            if key.startswith("stoat_ferret_core"):
                del sys.modules[key]
        sys.modules.update(saved)


class TestImportFallback:
    """Tests that the ImportError fallback stubs behave correctly."""

    def test_fallback_health_check_raises_runtime_error(self) -> None:
        """Calling health_check when native extension is missing raises RuntimeError."""
        mod = _reload_with_import_error()
        with pytest.raises(RuntimeError, match="native extension not built"):
            mod.health_check()

    def test_fallback_stub_classes_raise_runtime_error(self) -> None:
        """All stub class assignments raise RuntimeError when called."""
        mod = _reload_with_import_error()

        stub_names = [
            "Clip",
            "ClipValidationError",
            "FrameRate",
            "Position",
            "Duration",
            "TimeRange",
            "FFmpegCommand",
            "Filter",
            "FilterChain",
            "FilterGraph",
        ]
        for name in stub_names:
            attr = getattr(mod, name)
            with pytest.raises(RuntimeError, match="native extension not built"):
                attr()

    def test_fallback_exception_types_are_runtime_error(self) -> None:
        """Fallback exception types are aliased to RuntimeError."""
        mod = _reload_with_import_error()

        assert mod.ValidationError is RuntimeError
        assert mod.CommandError is RuntimeError
        assert mod.SanitizationError is RuntimeError

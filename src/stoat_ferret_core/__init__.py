"""stoat_ferret_core - Rust-powered video editing primitives.

This module provides the Python interface to the stoat_ferret_core Rust library,
which handles computationally intensive operations like filter generation,
timeline math, and FFmpeg command building.
"""

from __future__ import annotations

try:
    from stoat_ferret_core._core import health_check
except ImportError:
    # Rust extension not built - provide stub for development/testing
    def health_check() -> str:  # pragma: no cover
        """Stub health_check when native module unavailable."""
        raise RuntimeError(
            "stoat_ferret_core native extension not built. "
            "Run 'maturin develop' to build the Rust component."
        )


__all__ = ["health_check"]

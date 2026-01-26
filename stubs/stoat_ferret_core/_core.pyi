"""Type stubs for stoat_ferret_core._core (internal Rust module).

This module contains the actual PyO3 bindings from Rust.
"""

def health_check() -> str:
    """Performs a health check to verify the Rust module is loaded correctly.

    Returns:
        A status string indicating the module is operational.
    """
    ...

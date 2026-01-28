"""API server entry point.

Run with: python -m stoat_ferret.api
"""

from __future__ import annotations

import uvicorn

from stoat_ferret.api.app import create_app
from stoat_ferret.api.settings import get_settings


def main() -> None:
    """Run the API server with uvicorn.

    Uses settings from get_settings() for host and port configuration.
    Supports graceful shutdown via Ctrl+C.
    """
    settings = get_settings()
    app = create_app()

    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        log_level="info",
    )


if __name__ == "__main__":
    main()

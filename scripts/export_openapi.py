"""Export OpenAPI spec to a static JSON file for offline type generation."""

from __future__ import annotations

import json
from pathlib import Path

from stoat_ferret.api.app import create_app


def export_openapi(output_path: Path | None = None) -> dict:
    """Export the OpenAPI spec from the FastAPI app.

    Args:
        output_path: Where to write the JSON file. Defaults to gui/openapi.json.

    Returns:
        The OpenAPI spec as a dict.
    """
    # Use a non-existent gui_static_path to exclude environment-dependent
    # /gui routes, ensuring the spec is identical across all environments.
    app = create_app(gui_static_path="/nonexistent")
    spec = app.openapi()

    if output_path is None:
        output_path = Path(__file__).resolve().parent.parent / "gui" / "openapi.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(spec, indent=2) + "\n")
    return spec


if __name__ == "__main__":
    spec = export_openapi()
    paths = spec.get("paths", {})
    schemas = spec.get("components", {}).get("schemas", {})
    print(f"Exported OpenAPI spec: {len(paths)} paths, {len(schemas)} schemas")

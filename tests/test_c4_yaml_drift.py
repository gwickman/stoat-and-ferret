# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""CI drift-check: asserts C4 YAML and live OpenAPI agree on 4 /api/v1/source surfaces."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from stoat_ferret.api.app import create_app

OPENAPI_JSON = Path(__file__).parent.parent / "gui" / "openapi.json"
C4_YAML = (
    Path(__file__).parent.parent / "docs" / "C4-Documentation" / "apis" / "api-server-api.yaml"
)


def _get_live_spec() -> dict:
    app = create_app(gui_static_path=Path("/nonexistent"))
    return app.openapi()


def test_c4_yaml_source_route_drift() -> None:
    """C4 YAML and live OpenAPI agree on all 4 /api/v1/source surfaces."""
    spec = _get_live_spec()

    static = json.loads(OPENAPI_JSON.read_text(encoding="utf-8"))
    assert static == spec, "gui/openapi.json is stale — run scripts/export_openapi.py"
    c4 = yaml.safe_load(C4_YAML.read_text(encoding="utf-8"))

    live_route = spec["paths"]["/api/v1/source"]["get"]
    c4_route = c4["paths"]["/api/v1/source"]["get"]

    # Surface 1: route summary
    assert c4_route["summary"] == live_route["summary"], (
        f"route summary mismatch: YAML={c4_route['summary']!r} live={live_route['summary']!r}"
    )

    # Surface 2: route description
    assert c4_route.get("description") == live_route.get("description"), (
        f"route description mismatch: YAML={c4_route.get('description')!r} "
        f"live={live_route.get('description')!r}"
    )

    # Surface 3: SourceResponse.description
    live_schema_desc = spec["components"]["schemas"]["SourceResponse"].get("description")
    c4_schema_desc = c4["components"]["schemas"]["SourceResponse"].get("description")
    assert c4_schema_desc == live_schema_desc, (
        f"SourceResponse.description mismatch: YAML={c4_schema_desc!r} live={live_schema_desc!r}"
    )

    # Surface 4: info.license (name and url)
    live_license = spec["info"].get("license")
    c4_license = c4["info"].get("license")
    assert c4_license is not None, "C4 YAML info.license is missing"
    assert live_license is not None, "live OpenAPI info.license is missing"
    assert c4_license.get("name") == live_license.get("name"), (
        f"license name mismatch: YAML={c4_license.get('name')!r} live={live_license.get('name')!r}"
    )
    assert c4_license.get("url") == live_license.get("url"), (
        f"license url mismatch: YAML={c4_license.get('url')!r} live={live_license.get('url')!r}"
    )

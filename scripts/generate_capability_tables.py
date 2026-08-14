# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Generate capability tables from live effect registry and OpenAPI spec."""

import json
from pathlib import Path

from stoat_ferret.effects.definitions import create_default_registry


def generate_effect_table() -> str:
    """Return a markdown table of effects from the live registry."""
    registry = create_default_registry()
    effects = list(registry.list_all())
    lines = [f"## Effects ({len(effects)} total)\n"]
    lines.append("| # | Effect Type |")
    lines.append("|---|------------|")
    for i, effect in enumerate(effects, 1):
        lines.append(f"| {i} | `{effect.effect_type}` |")
    return "\n".join(lines)


def generate_route_table(openapi_path: Path = Path("gui/openapi.json")) -> str:
    """Return a markdown table of routes from the committed OpenAPI spec."""
    spec = json.loads(openapi_path.read_text(encoding="utf-8"))
    paths = list(spec.get("paths", {}).keys())
    lines = [f"## Routes ({len(paths)} total)\n"]
    lines.append("| # | Path |")
    lines.append("|---|------|")
    for i, path in enumerate(sorted(paths), 1):
        lines.append(f"| {i} | `{path}` |")
    return "\n".join(lines)


def main() -> None:
    """Print capability tables for effects and routes."""
    print(generate_effect_table())
    print()
    print(generate_route_table())


if __name__ == "__main__":
    main()

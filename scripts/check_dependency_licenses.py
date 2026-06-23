# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Validate that the dependency license inventory is current."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

INVENTORY_PATH = Path("docs/legal/dependency-license-inventory.md")

# Direct production dependencies tracked in the inventory.
# Maintained in sync with pyproject.toml [project.dependencies].
TRACKED_DIRECT_DEPS: dict[str, str] = {
    "alembic": "MIT",
    "aiosqlite": "MIT License",
    "fastapi": "MIT",
    "jsonschema": "MIT",
    "pillow": "MIT-CMU",
    "prometheus_client": "Apache-2.0 AND BSD-2-Clause",
    "pydantic-settings": "MIT",
    "python-dotenv": "BSD-3-Clause",
    "structlog": "MIT OR Apache-2.0",
    "uvicorn": "BSD-3-Clause",
}


def get_installed_packages() -> dict[str, str]:
    """Return {name_lower: license} for installed Python packages via pip-licenses."""
    result = subprocess.run(
        ["uv", "run", "pip-licenses", "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data: list[dict[str, str]] = json.loads(result.stdout)
    return {_normalize(pkg["Name"]): pkg["License"] for pkg in data}


def _normalize(name: str) -> str:
    """Normalize package name: lowercase, hyphens to underscores."""
    return name.lower().replace("-", "_")


def get_inventory_package_names() -> set[str]:
    """Return set of normalized package names listed in the inventory markdown tables."""
    if not INVENTORY_PATH.exists():
        return set()
    content = INVENTORY_PATH.read_text(encoding="utf-8")
    names: set[str] = set()
    for line in content.splitlines():
        # Match table rows: | `name` | ... (skip headers and dividers)
        if not line.startswith("| ") or line.startswith("| name") or line.startswith("| ---"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) > 1 and parts[1]:
            raw = parts[1].strip().strip("`")
            if raw and not re.match(r"^-+$", raw):
                names.add(_normalize(raw))
    return names


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate dependency license inventory.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit non-zero if inventory is incomplete or licenses have changed.",
    )
    args = parser.parse_args()

    if not args.check:
        print("Use --check to validate the inventory.")
        return 0

    if not INVENTORY_PATH.exists():
        print(f"ERROR: {INVENTORY_PATH} does not exist.", file=sys.stderr)
        return 1

    try:
        installed = get_installed_packages()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: pip-licenses failed: {exc}", file=sys.stderr)
        return 1

    inventory_names = get_inventory_package_names()
    errors: list[str] = []

    # Check 1: all tracked direct deps are present in inventory
    for dep_name in TRACKED_DIRECT_DEPS:
        if _normalize(dep_name) not in inventory_names:
            errors.append(f"Direct dep '{dep_name}' is missing from inventory.")

    # Check 2: no tracked dep's license changed from what pip-licenses reports
    for dep_name, recorded_license in TRACKED_DIRECT_DEPS.items():
        current = installed.get(_normalize(dep_name))
        if current is not None and current != recorded_license:
            errors.append(
                f"License changed for '{dep_name}': "
                f"inventory='{recorded_license}' installed='{current}'"
            )

    if errors:
        print(f"ERROR: {len(errors)} inventory issue(s) found:", file=sys.stderr)
        for err in errors:
            print(f"  {err}", file=sys.stderr)
        return 1

    tracked_count = len(TRACKED_DIRECT_DEPS)
    print(f"OK: all {tracked_count} tracked direct dependencies verified in inventory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

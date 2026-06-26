# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Validate that the dependency license inventory is current."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redef]

INVENTORY_PATH = Path("docs/legal/dependency-license-inventory.md")

# Direct production dependencies tracked in the inventory.
# Reference only — the primary source is pyproject.toml [project.dependencies].
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

_COPYLEFT_PATTERN = re.compile(r"GPL|AGPL|LGPL|Unknown", re.IGNORECASE)


def parse_project_deps(pyproject_path: str = "pyproject.toml") -> list[str]:
    """Parse direct runtime dependency names from pyproject.toml [project.dependencies]."""
    with open(pyproject_path, "rb") as f:
        data = tomllib.load(f)
    raw_deps: list[str] = data.get("project", {}).get("dependencies", [])
    names: list[str] = []
    for dep in raw_deps:
        name = re.split(r"[><=!;,\[]", dep)[0].strip()
        if name:
            names.append(name)
    return names


def get_installed_packages() -> dict[str, str]:
    """Return {name_lower: license} for installed Python packages via pip-licenses."""
    pip_licenses_path = shutil.which("pip-licenses")
    if pip_licenses_path is None:
        print(
            "Error: pip-licenses not found. Install with: pip install pip-licenses",
            file=sys.stderr,
        )
        sys.exit(1)
    result = subprocess.run(
        [pip_licenses_path, "--format=json"],
        capture_output=True,
        text=True,
        check=True,
    )
    data: list[dict[str, str]] = json.loads(result.stdout)
    return {_normalize(pkg["Name"]): pkg["License"] for pkg in data}


def _normalize(name: str) -> str:
    """Normalize package name: lowercase, hyphens to underscores."""
    return name.lower().replace("-", "_")


def get_inventory_package_names(inventory_path: Path = INVENTORY_PATH) -> set[str]:
    """Return set of normalized package names listed in the inventory markdown tables."""
    if not inventory_path.exists():
        return set()
    content = inventory_path.read_text(encoding="utf-8")
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
        help="Exit non-zero if inventory is incomplete or copyleft deps are unacknowledged.",
    )
    parser.add_argument(
        "--pyproject-path",
        default=None,
        help="Path to pyproject.toml (default: pyproject.toml).",
    )
    parser.add_argument(
        "--inventory-path",
        default=None,
        help=(
            "Path to dependency-license-inventory.md "
            "(default: docs/legal/dependency-license-inventory.md)."
        ),
    )
    args = parser.parse_args()

    should_check = args.check or args.pyproject_path is not None or args.inventory_path is not None
    if not should_check:
        print("Use --check to validate the inventory.")
        return 0

    pyproject_path = args.pyproject_path or "pyproject.toml"
    inventory_path = Path(args.inventory_path) if args.inventory_path else INVENTORY_PATH

    if not Path(pyproject_path).exists():
        print(f"ERROR: {pyproject_path} does not exist.", file=sys.stderr)
        return 1

    if not inventory_path.exists():
        print(f"ERROR: {inventory_path} does not exist.", file=sys.stderr)
        return 1

    # Parse direct runtime deps from pyproject.toml [project.dependencies]
    try:
        dep_names = parse_project_deps(pyproject_path)
    except Exception as exc:
        print(f"ERROR: Failed to parse {pyproject_path}: {exc}", file=sys.stderr)
        return 1

    # Check 1: all direct deps from pyproject.toml are present in inventory
    inventory_names = get_inventory_package_names(inventory_path)
    coverage_errors: list[str] = []
    for dep_name in dep_names:
        if _normalize(dep_name) not in inventory_names:
            coverage_errors.append(f"Direct dep '{dep_name}' is missing from inventory.")

    if coverage_errors:
        print(f"ERROR: {len(coverage_errors)} inventory issue(s) found:", file=sys.stderr)
        for err in coverage_errors:
            print(f"  {err}", file=sys.stderr)
        return 1

    # Check 2: copyleft/unknown detection via pip-licenses
    # Requires pip-licenses to be installed; fails non-zero if unavailable.
    try:
        installed = get_installed_packages()
    except subprocess.CalledProcessError as exc:
        print(f"ERROR: pip-licenses failed: {exc}", file=sys.stderr)
        return 1

    inventory_content = inventory_path.read_text(encoding="utf-8")
    copyleft_errors: list[str] = []
    for dep_name in dep_names:
        installed_license = installed.get(_normalize(dep_name))
        if (
            installed_license
            and _COPYLEFT_PATTERN.search(installed_license)
            and dep_name.lower() not in inventory_content.lower()
        ):
            copyleft_errors.append(
                f"Dep '{dep_name}' has copyleft/unknown license '{installed_license}'"
                f" not acknowledged in {inventory_path}."
            )

    if copyleft_errors:
        print(f"ERROR: {len(copyleft_errors)} copyleft/unknown issue(s) found:", file=sys.stderr)
        for err in copyleft_errors:
            print(f"  {err}", file=sys.stderr)
        return 1

    print(f"OK: all {len(dep_names)} direct runtime dependencies verified in inventory.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

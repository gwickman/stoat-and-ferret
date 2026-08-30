# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Bidirectional UAT journey registration guard with doc-truth dimension (BL-812 AC-14).

Three dimensions:
  (a) JOURNEY_MODULE_MAP.keys() ⊆ JOURNEY_DEPS.keys() ∩ JOURNEY_NAMES.keys()
  (b) Every tests/uat/journeys/j_*.py file has a JOURNEY_MODULE_MAP entry
  (c) Every docs/manual/uat-testing.md journey-ID→file row matches JOURNEY_MODULE_MAP
"""

from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _import_runner_maps() -> tuple[dict[int, list[int]], dict[int, str], dict[int, str]]:
    """Import the three registration dicts from scripts/uat_runner.py."""
    import importlib.util
    import sys

    runner_path = PROJECT_ROOT / "scripts" / "uat_runner.py"
    spec = importlib.util.spec_from_file_location("_uat_runner_guard", str(runner_path))
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules["_uat_runner_guard"] = mod
    spec.loader.exec_module(mod)  # type: ignore[attr-defined]
    return mod.JOURNEY_DEPS, mod.JOURNEY_NAMES, mod.JOURNEY_MODULE_MAP


def test_dimension_a_module_map_subset_of_deps_and_names() -> None:
    """(a) MODULE_MAP.keys() ⊆ DEPS.keys() AND MODULE_MAP.keys() ⊆ NAMES.keys()."""
    deps, names, module_map = _import_runner_maps()

    missing_in_deps = sorted(set(module_map.keys()) - set(deps.keys()))
    assert not missing_in_deps, (
        f"Journey IDs in JOURNEY_MODULE_MAP but missing from JOURNEY_DEPS: {missing_in_deps}\n"
        "Add each missing ID to JOURNEY_DEPS in scripts/uat_runner.py."
    )

    missing_in_names = sorted(set(module_map.keys()) - set(names.keys()))
    assert not missing_in_names, (
        f"Journey IDs in JOURNEY_MODULE_MAP but missing from JOURNEY_NAMES: {missing_in_names}\n"
        "Add each missing ID to JOURNEY_NAMES in scripts/uat_runner.py."
    )


def test_dimension_b_all_journey_files_registered() -> None:
    """(b) Every tests/uat/journeys/j_*.py file has a JOURNEY_MODULE_MAP entry."""
    _deps, _names, module_map = _import_runner_maps()

    journey_dir = PROJECT_ROOT / "tests" / "uat" / "journeys"
    journey_files = sorted(journey_dir.glob("j_*.py"))

    # Build reverse map: module_path → journey_id
    # Module path format: "tests.uat.journeys.j_foo"
    registered_modules = set(module_map.values())

    unregistered: list[str] = []
    for jf in journey_files:
        # Convert file path to module path
        rel = jf.relative_to(PROJECT_ROOT)
        module_path = ".".join(rel.with_suffix("").parts)
        if module_path not in registered_modules:
            unregistered.append(str(rel))

    assert not unregistered, (
        "Journey files not registered in JOURNEY_MODULE_MAP:\n"
        + "\n".join(f"  {f}" for f in unregistered)
        + "\nAdd each file's module path to JOURNEY_MODULE_MAP in scripts/uat_runner.py."
    )


def test_dimension_c_doc_truth_matches_module_map() -> None:
    """(c) Every uat-testing.md journey-ID→file row matches JOURNEY_MODULE_MAP."""
    _deps, _names, module_map = _import_runner_maps()

    doc_path = PROJECT_ROOT / "docs" / "manual" / "uat-testing.md"
    doc_text = doc_path.read_text(encoding="utf-8")

    # Parse table rows: "| <id> | `<path>` | ..."
    # Matches rows like: | 711 | `tests/uat/journeys/j_in_point_trim.py` | ...
    row_pattern = re.compile(
        r"^\|\s*(\d+)\s*\|[^|]*`([^`]+)`",
        re.MULTILINE,
    )

    mismatches: list[str] = []
    for m in row_pattern.finditer(doc_text):
        jid = int(m.group(1))
        raw_path = m.group(2).strip()

        # Only validate entries that point to tests/uat/journeys/j_*.py files
        if "tests/uat/journeys/j_" not in raw_path and "tests\\uat\\journeys\\j_" not in raw_path:
            continue

        # Convert file path → module path
        clean = raw_path.replace("\\", "/")
        module_path = clean.replace("/", ".").removesuffix(".py")

        if jid not in module_map:
            mismatches.append(
                f"  J-{jid}: doc references {raw_path!r} but ID not in JOURNEY_MODULE_MAP"
            )
        elif module_map[jid] != module_path:
            mismatches.append(
                f"  J-{jid}: doc says {module_path!r}, MODULE_MAP says {module_map[jid]!r}"
            )

    assert not mismatches, (
        "uat-testing.md journey-ID→file entries do not match JOURNEY_MODULE_MAP:\n"
        + "\n".join(mismatches)
        + "\nUpdate uat-testing.md or JOURNEY_MODULE_MAP to agree."
    )

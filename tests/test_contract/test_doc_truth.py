# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""CI gate: committed docs must not drift from live effect registry count."""

import importlib.util
import re
from pathlib import Path

from stoat_ferret.effects.definitions import create_default_registry

EFFECT_DOCS = [
    Path("docs/ARCHITECTURE.md"),
    Path("docs/manual/01_getting-started.md"),
    Path("docs/manual/03_api-reference.md"),
    Path("docs/manual/04_effects-guide.md"),
    Path("docs/manual/06_gui-guide.md"),
    Path("docs/manual/operator-guide.md"),
]

# Docs intentionally excluded from effect-count gating with rationale.
# C4 docs are auto-generated architecture artifacts; effect counts there are
# derived summaries, not authoritative references, and are updated at C4 doc
# regeneration time.
_EFFECT_DOC_GAPS = {
    "docs/C4-Documentation/": (
        "Auto-generated architecture artifacts; effect counts are derived summaries,"
        " not authoritative references. Updated at C4 doc regeneration time."
    ),
}

# Docs gated for route-inventory drift. Add entries here when a manual doc
# gains a route inventory section.
ROUTE_DOCS = [
    Path("docs/ARCHITECTURE.md"),
]

# Docs intentionally excluded from route-inventory gating with rationale.
# C4 docs are auto-generated artifacts; their route inventories are derived,
# not hand-maintained, so drift there is caught upstream (generation step).
_ROUTE_DOC_GAPS = {
    "docs/C4-Documentation/": (
        "Auto-generated; route inventories are derived artifacts, not hand-maintained."
    ),
}

# Load generate_route_table from scripts/ (not an installed package).
_scripts_dir = Path(__file__).resolve().parents[2] / "scripts"
_cap_spec = importlib.util.spec_from_file_location(
    "generate_capability_tables",
    _scripts_dir / "generate_capability_tables.py",
)
assert _cap_spec is not None
assert _cap_spec.loader is not None
_cap_mod = importlib.util.module_from_spec(_cap_spec)
_cap_spec.loader.exec_module(_cap_mod)  # type: ignore[union-attr]
generate_route_table = _cap_mod.generate_route_table


def test_effect_count_matches_registry() -> None:
    live_count = len(list(create_default_registry().list_all()))
    for doc in EFFECT_DOCS:
        text = doc.read_text(encoding="utf-8")
        m = re.search(r"effects-count:\s*(\d+)", text)
        assert m, f"{doc}: missing <!-- effects-count: N --> marker"
        assert int(m.group(1)) == live_count, (
            f"{doc}: effects-count {m.group(1)} != live {live_count}"
        )


def test_route_inventory_matches_architecture() -> None:
    table = generate_route_table()
    m = re.search(r"## Routes \((\d+) total\)", table)
    assert m, "generate_route_table() output missing expected '## Routes (N total)' header"
    live_count = int(m.group(1))

    for doc in ROUTE_DOCS:
        text = doc.read_text(encoding="utf-8")
        marker = re.search(r"<!--\s*route-count:\s*(\d+)\s*-->", text)
        assert marker, f"{doc}: missing <!-- route-count: N --> marker"
        doc_count = int(marker.group(1))
        assert doc_count == live_count, (
            f"{doc}: route-count {doc_count} != live {live_count}"
            f" (delta {live_count - doc_count:+d}); update the marker or the OpenAPI spec"
        )

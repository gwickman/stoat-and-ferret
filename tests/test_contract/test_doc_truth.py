# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""CI gate: committed docs must not drift from live effect registry count."""

import re
from pathlib import Path

from stoat_ferret.effects.definitions import create_default_registry

EFFECT_DOCS = [
    Path("docs/manual/01_getting-started.md"),
    Path("docs/manual/03_api-reference.md"),
    Path("docs/manual/04_effects-guide.md"),
    Path("docs/manual/06_gui-guide.md"),
    Path("docs/manual/operator-guide.md"),
]


def test_effect_count_matches_registry() -> None:
    live_count = len(list(create_default_registry().list_all()))
    for doc in EFFECT_DOCS:
        text = doc.read_text(encoding="utf-8")
        m = re.search(r"effects-count:\s*(\d+)", text)
        assert m, f"{doc}: missing <!-- effects-count: N --> marker"
        assert int(m.group(1)) == live_count, (
            f"{doc}: effects-count {m.group(1)} != live {live_count}"
        )

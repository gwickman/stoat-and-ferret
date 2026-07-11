#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Check that _core.pyi has not lost any def __new__ constructors.

Used in CI to prevent wholesale stub_gen copy-paste from stripping hand-written __new__ bodies.
See AGENTS.md §'Workflow After Modifying Rust API' for the append-only workflow.
"""

import subprocess
import sys

PYI_PATH = "src/stoat_ferret_core/_core.pyi"


def count_new_defs(content: str) -> int:
    return content.count("def __new__")


def main() -> int:
    try:
        with open(PYI_PATH, encoding="utf-8") as f:
            current_content = f.read()
    except FileNotFoundError:
        print(f"ERROR: {PYI_PATH} not found", file=sys.stderr)
        return 1
    current_count = count_new_defs(current_content)

    result = subprocess.run(
        ["git", "show", f"HEAD:{PYI_PATH}"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"INFO: {PYI_PATH} is new (not in HEAD); append-only guard skipped.")
        return 0

    head_count = count_new_defs(result.stdout)

    if current_count < head_count:
        delta = head_count - current_count
        print(
            f"ERROR: {PYI_PATH} lost {delta} `def __new__` constructor(s) "
            f"(was {head_count}, now {current_count}).\n"
            f"Do NOT copy stub_gen output wholesale. Use append-only edits.\n"
            f"See AGENTS.md §'Workflow After Modifying Rust API' for the correct approach.",
            file=sys.stderr,
        )
        return 1

    print(
        f"OK: {PYI_PATH} __new__ count: {head_count} -> {current_count} "
        f"({'unchanged' if current_count == head_count else f'+{current_count - head_count}'})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

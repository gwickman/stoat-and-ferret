#!/usr/bin/env python3
"""Repair malformed render_plan rows in the runtime database (data/stoat.db).

Operates on the runtime DB at data/stoat.db, not the seed fixture
(tests/fixtures/stoat.seed.db). The seed fixture is immutable and tracked
in git; this script repairs live runtime data only.

Idempotent: safe to re-run. Only updates rows where status='queued'
AND render_plan='{}'. Already-repaired rows are untouched.
"""

from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path("data/stoat.db")

VALID_RENDER_PLAN = json.dumps(
    {"settings": {"preset": "default", "codec": "h264"}, "total_duration": 120.0}
)


def main() -> int:
    """Run the fixture repair and return exit code."""
    if not DB_PATH.exists():
        print(f"ERROR: database not found at {DB_PATH}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM render_jobs WHERE render_plan='{}' AND status='queued';")
    count_before = cursor.fetchone()[0]
    print(f"Malformed rows before repair: {count_before}")

    cursor.execute(
        "UPDATE render_jobs SET render_plan=? WHERE status='queued' AND render_plan='{}';",
        (VALID_RENDER_PLAN,),
    )
    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM render_jobs WHERE render_plan='{}' AND status='queued';")
    count_after = cursor.fetchone()[0]
    print(f"Malformed rows after repair: {count_after}")

    conn.close()

    updated = count_before - count_after
    print(f"Repair complete. Updated {updated} rows.")

    if count_after != 0:
        print("ERROR: Repair incomplete — malformed rows remain.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

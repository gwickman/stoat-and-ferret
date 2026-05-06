#!/usr/bin/env python3
"""UAT Journey 604: Keyboard Navigation (J604).

Validates keyboard-only navigation through the application by wrapping the
TypeScript E2E spec `gui/e2e/keyboard-navigation.spec.ts` via Playwright CLI.

Checks that all interactive elements are Tab-reachable, focus order is correct,
and no focus traps exist in any workspace preset.

Independent — no prerequisite journeys required.

Environment variables:
    UAT_OUTPUT_DIR: Directory for journey output artifacts.
    UAT_HEADED: "1" for headed mode, "0" for headless (default).
    UAT_SERVER_URL: Base URL of the running server (default: http://localhost:8765).
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOURNEY_NAME = "keyboard-navigation"
JOURNEY_ID = 604

SPEC_PATH = PROJECT_ROOT / "gui" / "e2e" / "keyboard-navigation.spec.ts"


def run() -> int:
    """Execute the J604 keyboard navigation journey.

    Invokes the TypeScript E2E spec via Playwright CLI and reports pass/fail
    based on the exit code.

    Returns:
        Exit code: 0 if all tests pass, 1 otherwise.
    """
    output_dir = Path(os.environ.get("UAT_OUTPUT_DIR", "uat-evidence"))
    headed = os.environ.get("UAT_HEADED", "0") == "1"

    journey_dir = output_dir / JOURNEY_NAME
    journey_dir.mkdir(parents=True, exist_ok=True)

    npx_path = shutil.which("npx")
    if not npx_path:
        result_data = {
            "name": JOURNEY_NAME,
            "journey_id": JOURNEY_ID,
            "status": "error",
            "error": "npx not found in PATH",
        }
        result_path = journey_dir / "journey_result.json"
        result_path.write_text(json.dumps(result_data, indent=2) + "\n", encoding="utf-8")
        print(f"\n  Journey {JOURNEY_ID} ({JOURNEY_NAME}): ERROR — npx not found in PATH")
        sys.exit(1)

    start_time = time.monotonic()

    playwright_args = [
        npx_path,
        "playwright",
        "test",
        str(SPEC_PATH.relative_to(PROJECT_ROOT / "gui")),
    ]
    if headed:
        playwright_args.append("--headed")

    result = subprocess.run(
        playwright_args,
        cwd=str(PROJECT_ROOT / "gui"),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    duration = time.monotonic() - start_time
    passed = result.returncode == 0

    # Parse test count from Playwright output (e.g. "9 passed (12s)")
    stdout = result.stdout or ""
    stderr = result.stderr or ""

    steps_total = 0
    steps_passed = 0
    steps_failed = 0

    for line in stdout.splitlines():
        if "passed" in line and "failed" not in line:
            parts = line.strip().split()
            for i, part in enumerate(parts):
                if part == "passed" and i > 0:
                    try:
                        steps_passed = int(parts[i - 1])
                        steps_total += steps_passed
                    except ValueError:
                        pass
        if "failed" in line:
            parts = line.strip().split()
            for i, part in enumerate(parts):
                if part == "failed" and i > 0:
                    try:
                        steps_failed = int(parts[i - 1])
                        steps_total += steps_failed
                    except ValueError:
                        pass

    if steps_total == 0:
        steps_total = 1
        if passed:
            steps_passed = 1
        else:
            steps_failed = 1

    issues: list[str] = []
    if not passed:
        issues.append(f"Playwright exit code {result.returncode}")
        if stderr:
            issues.append(stderr[-500:])

    # Write structured result JSON
    result_data = {
        "name": JOURNEY_NAME,
        "journey_id": JOURNEY_ID,
        "steps_total": steps_total,
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "console_errors": [],
        "issues": issues,
        "duration_seconds": round(duration, 2),
    }
    result_path = journey_dir / "journey_result.json"
    result_path.write_text(json.dumps(result_data, indent=2) + "\n", encoding="utf-8")

    # Write Playwright output to log file
    log_path = journey_dir / "playwright_output.txt"
    log_path.write_text(stdout + "\n" + stderr, encoding="utf-8", errors="replace")

    status = "PASSED" if passed else "FAILED"
    print(f"\n  Journey {JOURNEY_ID} ({JOURNEY_NAME}): {status}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())

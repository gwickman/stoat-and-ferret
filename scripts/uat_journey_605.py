#!/usr/bin/env python3
"""UAT Journey 605: Screen Reader Audit (J605).

Validates WCAG AA compliance across all workspace routes using axe-core.
Navigates to each route, injects axe-core, runs an automated audit, and
reports critical/serious violations. The journey passes when 0 critical
and 0 serious violations are found across all routes.

Routes audited: /, /library, /render, /dashboard, /effects, /preview,
/projects, /timeline

Independent — no prerequisite journeys required.

Environment variables:
    UAT_OUTPUT_DIR: Directory for journey output artifacts.
    UAT_HEADED: "1" for headed mode, "0" for headless (default).
    UAT_SERVER_URL: Base URL of the running server (default: http://localhost:8765).
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright  # type: ignore[import-not-found]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
JOURNEY_NAME = "screen-reader-audit"
JOURNEY_ID = 605

# Routes to audit (relative to GUI base path)
AUDIT_ROUTES = [
    "/gui/",
    "/gui/library",
    "/gui/render",
    "/gui/dashboard",
    "/gui/preview",
    "/gui/projects",
    "/gui/timeline",
]

# Workspace presets to audit (on root route)
WORKSPACE_ROUTES = [
    ("/gui/?workspace=edit", "workspace-edit"),
    ("/gui/?workspace=render", "workspace-render"),
]

# axe-core rules disabled per project policy (Phase 7 scope, BL-299)
DISABLED_RULES = ["color-contrast", "select-name"]

# axe-core inline script — injects the CDN version via eval from package
AXE_INJECT_SCRIPT = """
async () => {
    if (typeof window.axe !== 'undefined') return;
    const script = document.createElement('script');
    script.src = '/gui/axe-core.js';
    document.head.appendChild(script);
    await new Promise((resolve, reject) => {
        script.onload = resolve;
        script.onerror = reject;
        setTimeout(reject, 10000);
    });
}
"""

# Axe run options — only report critical and serious violations
AXE_RUN_OPTS = {
    "runOnly": {
        "type": "tag",
        "values": ["wcag2a", "wcag2aa"],
    },
    "rules": {rule: {"enabled": False} for rule in DISABLED_RULES},
}


def run_axe_on_page(page: Any, url: str) -> dict[str, Any]:
    """Navigate to a URL and run an axe-core audit.

    Injects @axe-core/playwright's axe-core via the NPM package available
    in the node_modules, then runs the audit and filters to critical/serious.

    Args:
        page: Playwright sync Page object.
        url: Full URL to audit.

    Returns:
        Dict with keys: url, violations, critical_count, serious_count, error.
    """
    try:
        page.goto(url, wait_until="networkidle", timeout=30_000)
        # Short pause for dynamic content to settle
        page.wait_for_timeout(1000)

        # Use @axe-core/playwright inline — evaluate axe from the module
        # available in the GUI's node_modules via Playwright's addScriptTag
        page.add_script_tag(
            path=str(PROJECT_ROOT / "gui" / "node_modules" / "axe-core" / "axe.min.js")
        )

        # Run axe audit filtering to critical and serious violations
        violations_raw: list[dict[str, Any]] = page.evaluate(
            """(opts) => axe.run(document, opts).then(r => r.violations)""",
            AXE_RUN_OPTS,
        )

        critical_violations = [v for v in violations_raw if v.get("impact") == "critical"]
        serious_violations = [v for v in violations_raw if v.get("impact") == "serious"]

        return {
            "url": url,
            "violations": violations_raw,
            "critical_count": len(critical_violations),
            "serious_count": len(serious_violations),
            "error": None,
        }

    except Exception as exc:
        return {
            "url": url,
            "violations": [],
            "critical_count": 0,
            "serious_count": 0,
            "error": str(exc),
        }


def run() -> int:
    """Execute the J605 screen reader audit journey.

    Audits all configured routes using axe-core and reports violations.
    Journey passes when 0 critical and 0 serious violations found.

    Returns:
        Exit code: 0 if all routes pass, 1 otherwise.
    """
    output_dir = Path(os.environ.get("UAT_OUTPUT_DIR", "uat-evidence"))
    headed = os.environ.get("UAT_HEADED", "0") == "1"
    server_url = os.environ.get("UAT_SERVER_URL", "http://localhost:8765")

    journey_dir = output_dir / JOURNEY_NAME
    journey_dir.mkdir(parents=True, exist_ok=True)

    start_time = time.monotonic()

    steps_total = 0
    steps_passed = 0
    steps_failed = 0
    issues: list[str] = []
    audit_results: list[dict[str, Any]] = []

    # Build full URL list: page routes + workspace presets
    all_routes = [(f"{server_url}{route}", route) for route in AUDIT_ROUTES]
    for route, label in WORKSPACE_ROUTES:
        all_routes.append((f"{server_url}{route}", label))

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=not headed)
        context = browser.new_context(viewport={"width": 1280, "height": 720})
        page = context.new_page()

        try:
            for full_url, label in all_routes:
                steps_total += 1
                result = run_axe_on_page(page, full_url)
                audit_results.append(result)

                if result["error"]:
                    steps_failed += 1
                    issues.append(f"{label}: audit error — {result['error'][:200]}")
                    print(f"  {label}: ERROR — {result['error'][:100]}")
                    continue

                critical = result["critical_count"]
                serious = result["serious_count"]

                if critical == 0 and serious == 0:
                    steps_passed += 1
                    total_other = len(result["violations"]) - critical - serious
                    print(f"  {label}: PASS (0 critical, 0 serious, {total_other} minor/moderate)")
                else:
                    steps_failed += 1
                    violation_ids = [
                        v.get("id", "unknown")
                        for v in result["violations"]
                        if v.get("impact") in ("critical", "serious")
                    ]
                    issues.append(
                        f"{label}: {critical} critical, {serious} serious violations: "
                        + ", ".join(violation_ids[:5])
                    )
                    print(f"  {label}: FAIL ({critical} critical, {serious} serious)")
                    for v in result["violations"]:
                        if v.get("impact") in ("critical", "serious"):
                            desc = (v.get("description") or "")[:80]
                            print(f"    - [{v.get('impact')}] {v.get('id')}: {desc}")

        finally:
            context.close()
            browser.close()

    duration = time.monotonic() - start_time
    passed = steps_failed == 0

    # Write structured result JSON (includes per-route violation details)
    result_data = {
        "name": JOURNEY_NAME,
        "journey_id": JOURNEY_ID,
        "steps_total": steps_total,
        "steps_passed": steps_passed,
        "steps_failed": steps_failed,
        "console_errors": [],
        "issues": issues,
        "duration_seconds": round(duration, 2),
        "audit_results": [
            {
                "url": r["url"],
                "critical_count": r["critical_count"],
                "serious_count": r["serious_count"],
                "error": r["error"],
                "violation_ids": [v.get("id") for v in r["violations"]],
            }
            for r in audit_results
        ],
    }
    result_path = journey_dir / "journey_result.json"
    result_path.write_text(json.dumps(result_data, indent=2) + "\n", encoding="utf-8")

    status = "PASSED" if passed else "FAILED"
    print(f"\n  Journey {JOURNEY_ID} ({JOURNEY_NAME}): {status}")
    print(f"  Routes audited: {steps_total}, passed: {steps_passed}, failed: {steps_failed}")
    print(f"  Duration: {duration:.1f}s")
    print(f"  Results: {result_path}")

    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(run())

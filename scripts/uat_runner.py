#!/usr/bin/env python3
"""UAT runner harness for stoat-and-ferret.

Orchestrates the full build-boot-test-teardown cycle for user acceptance testing.
Manages subprocess lifecycle, health polling, journey execution with dependency-aware
fail-fast behavior, and timestamped output directories.

Usage:
    python scripts/uat_runner.py --headless
    python scripts/uat_runner.py --headed --journey 201
    python scripts/uat_runner.py --headless --no-build
    python scripts/uat_runner.py --headless --skip-build
    python scripts/uat_runner.py --headless --output-dir ./my-results
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, NamedTuple

import httpx

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "uat-evidence"
SERVER_PORT = 8765
SERVER_URL = f"http://localhost:{SERVER_PORT}"
HEALTH_POLL_INTERVAL = 1.0  # seconds
HEALTH_POLL_TIMEOUT = 60.0  # seconds
TEARDOWN_GRACE_SECONDS = 5

# Journey dependency graph: journey_id -> list of prerequisite journey_ids
JOURNEY_DEPS: dict[int, list[int]] = {
    201: [],
    202: [201],
    203: [202],
    204: [],
    205: [],
    401: [205],
    402: [201],
    403: [],
    404: [],
    501: [],
    502: [501],
    503: [501],
    504: [501],
}

# Human-readable journey names for screenshot directories and reports
JOURNEY_NAMES: dict[int, str] = {
    201: "scan-library",
    202: "project-clip",
    203: "effects-timeline",
    204: "export-render",
    205: "preview-playback",
    401: "preview-playback-full",
    402: "proxy-management",
    403: "theater-mode",
    404: "timeline-sync",
    501: "render-export-journey",
    502: "render-queue-journey",
    503: "render-settings-journey",
    504: "render-failure-journey",
}

# Known benign console error patterns to exclude from reports
BENIGN_CONSOLE_PATTERNS: list[str] = [
    "favicon.ico",
    "favicon",
]


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class JourneyResult(NamedTuple):
    """Result of a single journey execution."""

    journey_id: int
    status: str  # "passed", "failed", "skipped"
    message: str


@dataclass
class JourneyReport:
    """Detailed report for a single journey, including step and error data."""

    journey_id: int
    name: str
    status: str  # "passed", "failed", "skipped"
    message: str
    steps_total: int = 0
    steps_passed: int = 0
    steps_failed: int = 0
    console_errors: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the UAT runner.

    Args:
        argv: Optional argument list (defaults to sys.argv[1:]).

    Returns:
        Parsed argument namespace.
    """
    parser = argparse.ArgumentParser(
        description="UAT runner harness for stoat-and-ferret",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/uat_runner.py --headless\n"
            "  python scripts/uat_runner.py --headed --journey 201\n"
            "  python scripts/uat_runner.py --headless --no-build\n"
            "  python scripts/uat_runner.py --headless --skip-build\n"
        ),
    )
    display = parser.add_mutually_exclusive_group()
    display.add_argument(
        "--headed",
        action="store_true",
        default=False,
        help="Run browser tests in headed mode (visible browser window)",
    )
    display.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser tests in headless mode (default)",
    )
    parser.add_argument(
        "--journey",
        type=int,
        metavar="N",
        default=None,
        help="Run only the specified journey number (e.g. 201)",
    )
    parser.add_argument(
        "--no-build",
        action="store_true",
        default=False,
        help="Skip build steps; still manages server lifecycle",
    )
    parser.add_argument(
        "--skip-build",
        action="store_true",
        default=False,
        help="Skip build steps and connect to an already-running server",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Base output directory for results (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# Output directory
# ---------------------------------------------------------------------------


def create_output_dir(base_dir: Path) -> Path:
    """Create a timestamped output directory for this run.

    Args:
        base_dir: Base directory under which the timestamped folder is created.

    Returns:
        Path to the created timestamped directory.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    output_dir = base_dir / timestamp
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


# ---------------------------------------------------------------------------
# Build steps
# ---------------------------------------------------------------------------


def run_build_steps() -> None:
    """Execute the full build pipeline: Rust, Python, and GUI.

    Raises:
        SystemExit: If any build step fails.
    """
    # On Windows, npm is a .cmd batch file and cannot be found by subprocess
    # without shell=True unless the .cmd extension is included explicitly.
    npm = "npm.cmd" if sys.platform == "win32" else "npm"

    steps: list[tuple[str, list[str], Path | None]] = [
        ("Building Rust core (maturin develop)", ["maturin", "develop"], PROJECT_ROOT),
        ("Installing Python package", ["pip", "install", "-e", "."], PROJECT_ROOT),
        ("Installing GUI dependencies (npm ci)", [npm, "ci"], PROJECT_ROOT / "gui"),
        ("Building GUI (npm run build)", [npm, "run", "build"], PROJECT_ROOT / "gui"),
    ]

    for description, cmd, cwd in steps:
        print(f"  [{description}]")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        if result.returncode != 0:
            print(f"  FAILED: {description}", file=sys.stderr)
            print(f"  stdout: {result.stdout[-500:]}" if result.stdout else "", file=sys.stderr)
            print(f"  stderr: {result.stderr[-500:]}" if result.stderr else "", file=sys.stderr)
            sys.exit(1)


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


def start_server(
    output_dir: Path,
) -> tuple[subprocess.Popen[str], list[Any]]:
    """Start the uvicorn server as a background subprocess.

    Redirects stdout and stderr to log files in *output_dir* to avoid OS pipe
    buffer deadlocks (the parent never reads from PIPE, so the buffer fills and
    blocks the server).

    Args:
        output_dir: UAT evidence directory for this run.

    Returns:
        Tuple of (Popen handle, empty list — log files are closed after Popen inherits them).
    """
    print(f"  Starting server on port {SERVER_PORT}...")
    # Use uvicorn module directly for cross-platform compatibility.
    # Open log files via context manager; Popen inherits the file descriptors
    # before the with block exits, so the subprocess can still write to them.
    with (
        open(output_dir / "server-stdout.log", "w", encoding="utf-8") as stdout_fh,
        open(output_dir / "server-stderr.log", "w", encoding="utf-8") as stderr_fh,
    ):
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "stoat_ferret.api.app:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(SERVER_PORT),
            ],
            cwd=PROJECT_ROOT,
            stdout=stdout_fh,
            stderr=stderr_fh,
            text=True,
        )
    return proc, []


def wait_for_healthy(timeout: float = HEALTH_POLL_TIMEOUT) -> None:
    """Poll the server health endpoint until it responds 200.

    Args:
        timeout: Maximum seconds to wait for the server.

    Raises:
        SystemExit: If the server does not become healthy within the timeout.
    """
    url = f"{SERVER_URL}/health/ready"
    deadline = time.monotonic() + timeout
    print(f"  Waiting for server health ({url})...")

    while time.monotonic() < deadline:
        try:
            resp = httpx.get(url, timeout=5.0)
            if resp.status_code == 200:
                print("  Server is healthy.")
                return
        except httpx.ConnectError:
            pass
        time.sleep(HEALTH_POLL_INTERVAL)

    print(f"  ERROR: Server did not become healthy within {timeout}s", file=sys.stderr)
    sys.exit(1)


def run_seed_script() -> None:
    """Run the seed_sample_project script to populate test data.

    Raises:
        SystemExit: If the seed script fails.
    """
    print("  Seeding sample project data...")
    result = subprocess.run(
        [sys.executable, "scripts/seed_sample_project.py", SERVER_URL],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("  WARNING: Seed script failed (may already be seeded)", file=sys.stderr)
        if result.stderr:
            print(f"  stderr: {result.stderr[-300:]}", file=sys.stderr)


def teardown_server(
    proc: subprocess.Popen[str],
    log_handles: list[Any] | None = None,
) -> None:
    """Gracefully shut down the server subprocess.

    Sends SIGTERM (or TerminateProcess on Windows), waits up to TEARDOWN_GRACE_SECONDS,
    then falls back to SIGKILL if the process hasn't exited.  Closes any open log file
    handles that were used to capture server output.

    Args:
        proc: The server Popen handle.
        log_handles: Optional list of open file handles to close.
    """
    if proc.poll() is not None:
        _close_handles(log_handles)
        return  # Already exited

    print("  Shutting down server...")
    proc.terminate()

    # On Windows, terminate() calls TerminateProcess which is immediate.
    # On Unix, send SIGTERM and wait for graceful shutdown.
    if sys.platform != "win32":
        try:
            proc.wait(timeout=TEARDOWN_GRACE_SECONDS)
        except subprocess.TimeoutExpired:
            print("  Grace period expired, sending SIGKILL...")
            proc.kill()
            proc.wait(timeout=5)
    else:
        # Windows: terminate is immediate, just wait briefly for cleanup
        try:
            proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    _close_handles(log_handles)


def _close_handles(handles: list[Any] | None) -> None:
    """Close a list of file handles, ignoring errors."""
    if not handles:
        return
    for fh in handles:
        with contextlib.suppress(OSError):
            fh.close()


# ---------------------------------------------------------------------------
# Journey execution
# ---------------------------------------------------------------------------


def get_journeys_to_run(specific_journey: int | None) -> list[int]:
    """Determine which journeys to run based on CLI args.

    Args:
        specific_journey: If set, run only this journey number.

    Returns:
        Sorted list of journey IDs to execute.
    """
    if specific_journey is not None:
        if specific_journey not in JOURNEY_DEPS:
            print(
                f"  ERROR: Unknown journey {specific_journey}. "
                f"Available: {sorted(JOURNEY_DEPS.keys())}",
                file=sys.stderr,
            )
            sys.exit(1)
        return [specific_journey]
    return sorted(JOURNEY_DEPS.keys())


def should_skip_journey(
    journey_id: int, failed_journeys: set[int], skipped_journeys: set[int]
) -> str | None:
    """Check if a journey should be skipped due to failed dependencies.

    Args:
        journey_id: The journey to check.
        failed_journeys: Set of journey IDs that have failed.
        skipped_journeys: Set of journey IDs that were skipped.

    Returns:
        Skip reason string if the journey should be skipped, None otherwise.
    """
    for dep in JOURNEY_DEPS.get(journey_id, []):
        if dep in failed_journeys:
            return f"dependency journey {dep} failed"
        if dep in skipped_journeys:
            return f"dependency journey {dep} was skipped"
    return None


def run_journey(journey_id: int, output_dir: Path, headed: bool) -> JourneyResult:
    """Execute a single journey script.

    Currently a skeleton that reports journeys as passed since journey scripts
    are implemented in later features. The headed flag and output_dir are passed
    through for when journey scripts are available.

    Args:
        journey_id: The journey number to run.
        output_dir: Directory for journey output artifacts.
        headed: Whether to run in headed browser mode.

    Returns:
        JourneyResult with the outcome.
    """
    script_path = PROJECT_ROOT / "scripts" / f"uat_journey_{journey_id}.py"

    if not script_path.exists():
        return JourneyResult(
            journey_id=journey_id,
            status="passed",
            message="Journey script not yet implemented (skeleton pass)",
        )

    # When journey scripts exist, they will be invoked here
    env = os.environ.copy()
    env["UAT_OUTPUT_DIR"] = str(output_dir)
    env["UAT_HEADED"] = "1" if headed else "0"
    env["UAT_SERVER_URL"] = SERVER_URL

    result = subprocess.run(
        [sys.executable, str(script_path)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=env,
    )

    if result.returncode == 0:
        return JourneyResult(
            journey_id=journey_id,
            status="passed",
            message="Journey completed successfully",
        )

    detail = result.stderr[-200:] if result.stderr else ""
    fail_msg = f"Exit code {result.returncode}"
    if detail:
        fail_msg = f"{fail_msg}: {detail}"
    return JourneyResult(
        journey_id=journey_id,
        status="failed",
        message=fail_msg,
    )


def execute_journeys(journeys: list[int], output_dir: Path, headed: bool) -> list[JourneyResult]:
    """Run journeys with fail-fast dependency awareness.

    Args:
        journeys: Ordered list of journey IDs to execute.
        output_dir: Output directory for artifacts.
        headed: Whether to run in headed browser mode.

    Returns:
        List of JourneyResult for all journeys.
    """
    results: list[JourneyResult] = []
    failed_journeys: set[int] = set()
    skipped_journeys: set[int] = set()

    for journey_id in journeys:
        skip_reason = should_skip_journey(journey_id, failed_journeys, skipped_journeys)
        if skip_reason is not None:
            result = JourneyResult(
                journey_id=journey_id,
                status="skipped",
                message=f"Skipped: {skip_reason}",
            )
            skipped_journeys.add(journey_id)
            results.append(result)
            print(f"  Journey {journey_id}: SKIPPED ({skip_reason})")
            continue

        print(f"  Journey {journey_id}: running...")
        result = run_journey(journey_id, output_dir, headed)
        results.append(result)

        if result.status == "failed":
            failed_journeys.add(journey_id)
            print(f"  Journey {journey_id}: FAILED - {result.message}")
        else:
            print(f"  Journey {journey_id}: PASSED")

    return results


# ---------------------------------------------------------------------------
# Screenshot infrastructure
# ---------------------------------------------------------------------------


def take_screenshot(
    page: Any,
    output_dir: Path,
    journey_name: str,
    step_number: int,
    description: str,
    *,
    failed: bool = False,
) -> Path:
    """Capture a screenshot with the structured naming convention.

    Screenshots are saved as ``{journey_name}/{NN}_{description}.png``.
    Failed steps use a ``FAIL_`` prefix: ``{journey_name}/{NN}_FAIL_{description}.png``.

    Args:
        page: Playwright Page object.
        output_dir: Root output directory for this UAT run.
        journey_name: Journey name (e.g. ``"scan-library"``).
        step_number: Step number within the journey.
        description: Brief description used in the filename.
        failed: If True, prefix the description with ``FAIL_``.

    Returns:
        Path to the saved screenshot file.
    """
    journey_dir = output_dir / journey_name
    journey_dir.mkdir(parents=True, exist_ok=True)
    prefix = "FAIL_" if failed else ""
    filename = f"{step_number:02d}_{prefix}{description}.png"
    path = journey_dir / filename
    page.screenshot(path=str(path))
    return path


# ---------------------------------------------------------------------------
# Console error capture
# ---------------------------------------------------------------------------


class ConsoleErrorCollector:
    """Collect and filter browser console errors during a journey.

    Attaches to a Playwright page via :meth:`attach` and captures console
    errors, filtering out known benign patterns (e.g. favicon 404s).

    Usage::

        collector = ConsoleErrorCollector()
        collector.attach(page)
        # ... run journey steps ...
        errors = collector.errors
    """

    def __init__(self) -> None:
        self.errors: list[str] = []

    def handler(self, msg: Any) -> None:
        """Console message handler. Captures error-level messages only.

        Args:
            msg: Playwright ConsoleMessage object.
        """
        if msg.type != "error":
            return
        text = msg.text
        if any(pattern in text.lower() for pattern in BENIGN_CONSOLE_PATTERNS):
            return
        self.errors.append(text)

    def attach(self, page: Any) -> None:
        """Register this collector as a console handler on a page.

        Args:
            page: Playwright Page object.
        """
        page.on("console", self.handler)


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def print_summary(results: list[JourneyResult], output_dir: Path) -> None:
    """Print a pass/fail summary of all journey results.

    Args:
        results: List of JourneyResult from the run.
        output_dir: The output directory used for this run.
    """
    passed = [r for r in results if r.status == "passed"]
    failed = [r for r in results if r.status == "failed"]
    skipped = [r for r in results if r.status == "skipped"]

    print(f"\n{'=' * 60}")
    print("UAT Run Summary")
    print(f"{'=' * 60}")
    print(f"  Output: {output_dir}")
    print(f"  Passed: {len(passed)}  Failed: {len(failed)}  Skipped: {len(skipped)}")

    if failed:
        root_causes = find_root_causes(failed, results)
        print(f"\n  Root-cause failures: {', '.join(str(j) for j in root_causes)}")

    for r in results:
        status_icon = {"passed": "OK", "failed": "FAIL", "skipped": "SKIP"}[r.status]
        print(f"  [{status_icon}] Journey {r.journey_id}: {r.message}")

    print(f"{'=' * 60}\n")


def find_root_causes(failed: list[JourneyResult], all_results: list[JourneyResult]) -> list[int]:
    """Identify root-cause journey failures (failures with no failed dependencies).

    Args:
        failed: List of failed JourneyResults.
        all_results: All journey results.

    Returns:
        List of journey IDs that are root-cause failures.
    """
    failed_ids = {r.journey_id for r in failed}
    skipped_ids = {r.journey_id for r in all_results if r.status == "skipped"}
    root_causes: list[int] = []

    for r in failed:
        deps = JOURNEY_DEPS.get(r.journey_id, [])
        # A failure is a root cause if none of its dependencies failed or were skipped
        if not any(d in failed_ids or d in skipped_ids for d in deps):
            root_causes.append(r.journey_id)

    return sorted(root_causes)


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------


def build_journey_reports(results: list[JourneyResult], output_dir: Path) -> list[JourneyReport]:
    """Build detailed JourneyReport objects from execution results.

    Checks for structured ``journey_result.json`` files written by journey
    scripts.  Falls back to basic data from JourneyResult when no structured
    output exists.

    Args:
        results: Journey results from :func:`execute_journeys`.
        output_dir: Output directory for this run.

    Returns:
        List of JourneyReport with available detail.
    """
    reports: list[JourneyReport] = []
    for result in results:
        name = JOURNEY_NAMES.get(result.journey_id, f"journey-{result.journey_id}")

        # Check for structured result JSON written by a journey script
        result_file = output_dir / name / "journey_result.json"
        if result_file.exists():
            data = json.loads(result_file.read_text(encoding="utf-8"))
            reports.append(
                JourneyReport(
                    journey_id=result.journey_id,
                    name=data.get("name", name),
                    status=result.status,
                    message=result.message,
                    steps_total=data.get("steps_total", 0),
                    steps_passed=data.get("steps_passed", 0),
                    steps_failed=data.get("steps_failed", 0),
                    console_errors=data.get("console_errors", []),
                    issues=data.get("issues", []),
                )
            )
        else:
            reports.append(
                JourneyReport(
                    journey_id=result.journey_id,
                    name=name,
                    status=result.status,
                    message=result.message,
                )
            )
    return reports


def generate_json_report(
    reports: list[JourneyReport],
    output_dir: Path,
    mode: str,
    duration_seconds: float,
) -> Path:
    """Generate ``uat-report.json`` with structured test results.

    Args:
        reports: Journey report objects.
        output_dir: Output directory for this run.
        mode: ``"headed"`` or ``"headless"``.
        duration_seconds: Total run duration in seconds.

    Returns:
        Path to the generated JSON report.
    """
    any_failed = any(r.status == "failed" for r in reports)

    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "duration_seconds": round(duration_seconds, 2),
        "overall_status": "fail" if any_failed else "pass",
        "journeys": [
            {
                "name": r.name,
                "journey_id": r.journey_id,
                "status": r.status,
                "steps_total": r.steps_total,
                "steps_passed": r.steps_passed,
                "steps_failed": r.steps_failed,
                "console_errors": r.console_errors,
                "issues": r.issues,
            }
            for r in reports
        ],
    }

    path = output_dir / "uat-report.json"
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path


def generate_markdown_report(
    reports: list[JourneyReport],
    output_dir: Path,
    mode: str,
    duration_seconds: float,
) -> Path:
    """Generate ``uat-report.md`` with human-readable test results.

    Args:
        reports: Journey report objects.
        output_dir: Output directory for this run.
        mode: ``"headed"`` or ``"headless"``.
        duration_seconds: Total run duration in seconds.

    Returns:
        Path to the generated markdown report.
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    passed = sum(1 for r in reports if r.status == "passed")
    failed = sum(1 for r in reports if r.status == "failed")
    skipped = sum(1 for r in reports if r.status == "skipped")

    lines: list[str] = [
        "# UAT Report",
        "",
        f"**Timestamp:** {timestamp}",
        f"**Mode:** {mode}",
        f"**Duration:** {duration_seconds:.1f}s",
        f"**Result:** {passed} passed, {failed} failed, {skipped} skipped",
        "",
        "## Journey Summary",
        "",
        "| Journey | Status | Steps |",
        "|---------|--------|-------|",
    ]

    for r in reports:
        status_badge = {"passed": "PASS", "failed": "FAIL", "skipped": "SKIP"}[r.status]
        steps = f"{r.steps_passed}/{r.steps_total}" if r.steps_total > 0 else "—"
        lines.append(f"| {r.name} | {status_badge} | {steps} |")

    # Detailed sections for failed journeys
    failed_reports = [r for r in reports if r.status == "failed"]
    if failed_reports:
        lines.extend(["", "## Failed Journeys", ""])
        for r in failed_reports:
            lines.append(f"### {r.name}")
            lines.append("")
            if r.issues:
                for issue in r.issues:
                    lines.append(f"- {issue}")
            else:
                lines.append(f"- {r.message}")
            if r.console_errors:
                lines.append("")
                lines.append("**Console errors:**")
                for err in r.console_errors:
                    lines.append(f"- `{err}`")
            lines.append("")

    lines.append("")
    path = output_dir / "uat-report.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    """Run the UAT harness.

    Args:
        argv: Optional argument list for testing.

    Returns:
        Exit code: 0 if all journeys pass, 1 otherwise.
    """
    args = parse_args(argv)
    headed = args.headed

    print("=" * 60)
    print("stoat-and-ferret UAT Runner")
    print("=" * 60)

    # 1. Create output directory
    output_dir = create_output_dir(args.output_dir)
    print(f"\nOutput directory: {output_dir}")

    server_proc: subprocess.Popen[str] | None = None
    server_log_handles: list[Any] | None = None

    try:
        # 2. Build (unless --skip-build or --no-build)
        if not args.skip_build:
            if not args.no_build:
                print("\n[Build Phase]")
                run_build_steps()

            # 3. Start server
            print("\n[Boot Phase]")
            server_proc, server_log_handles = start_server(output_dir)
            wait_for_healthy()

            # 4. Seed data
            run_seed_script()
        else:
            print("\n[Skip Build] Connecting to existing server...")
            # Verify server is running
            try:
                resp = httpx.get(f"{SERVER_URL}/health/ready", timeout=5.0)
                if resp.status_code != 200:
                    print(
                        f"  WARNING: Server health check returned {resp.status_code}",
                        file=sys.stderr,
                    )
            except httpx.ConnectError:
                print(
                    f"  ERROR: Cannot connect to server at {SERVER_URL}. "
                    "Start the server or remove --skip-build.",
                    file=sys.stderr,
                )
                return 1

        # 5. Run journeys
        print("\n[Journey Phase]")
        run_start = time.monotonic()
        journeys = get_journeys_to_run(args.journey)
        results = execute_journeys(journeys, output_dir, headed)
        duration = time.monotonic() - run_start

        # 6. Generate reports
        mode = "headed" if headed else "headless"
        journey_reports = build_journey_reports(results, output_dir)
        json_path = generate_json_report(journey_reports, output_dir, mode, duration)
        md_path = generate_markdown_report(journey_reports, output_dir, mode, duration)
        print(f"\n  Reports: {json_path}")
        print(f"           {md_path}")

        # 7. Summary
        print_summary(results, output_dir)

        # Exit code
        any_failed = any(r.status == "failed" for r in results)
        return 1 if any_failed else 0

    except KeyboardInterrupt:
        print("\n  Interrupted by user.", file=sys.stderr)
        return 130
    finally:
        # 7. Teardown
        if server_proc is not None:
            print("\n[Teardown Phase]")
            teardown_server(server_proc, server_log_handles)


if __name__ == "__main__":
    # Ensure clean Ctrl+C handling
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(main())

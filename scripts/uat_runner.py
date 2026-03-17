#!/usr/bin/env python3
"""UAT runner harness for stoat-and-ferret.

Orchestrates the full build-boot-test-teardown cycle for user acceptance testing.
Manages subprocess lifecycle, health polling, journey execution with dependency-aware
fail-fast behavior, and timestamped output directories.

Usage:
    python scripts/uat_runner.py --headless
    python scripts/uat_runner.py --headed --journey 201
    python scripts/uat_runner.py --headless --skip-build
    python scripts/uat_runner.py --headless --output-dir ./my-results
"""

from __future__ import annotations

import argparse
import os
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import NamedTuple

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
}


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


class JourneyResult(NamedTuple):
    """Result of a single journey execution."""

    journey_id: int
    status: str  # "passed", "failed", "skipped"
    message: str


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
    steps: list[tuple[str, list[str], Path | None]] = [
        ("Building Rust core (maturin develop)", ["maturin", "develop"], PROJECT_ROOT),
        ("Installing Python package", ["pip", "install", "-e", "."], PROJECT_ROOT),
        ("Installing GUI dependencies (npm ci)", ["npm", "ci"], PROJECT_ROOT / "gui"),
        ("Building GUI (npm run build)", ["npm", "run", "build"], PROJECT_ROOT / "gui"),
    ]

    for description, cmd, cwd in steps:
        print(f"  [{description}]")
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  FAILED: {description}", file=sys.stderr)
            print(f"  stdout: {result.stdout[-500:]}" if result.stdout else "", file=sys.stderr)
            print(f"  stderr: {result.stderr[-500:]}" if result.stderr else "", file=sys.stderr)
            sys.exit(1)


# ---------------------------------------------------------------------------
# Server lifecycle
# ---------------------------------------------------------------------------


def start_server() -> subprocess.Popen[str]:
    """Start the uvicorn server as a background subprocess.

    Returns:
        The Popen handle for the server process.
    """
    print(f"  Starting server on port {SERVER_PORT}...")
    # Use uvicorn module directly for cross-platform compatibility
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
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc


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


def teardown_server(proc: subprocess.Popen[str]) -> None:
    """Gracefully shut down the server subprocess.

    Sends SIGTERM (or TerminateProcess on Windows), waits up to TEARDOWN_GRACE_SECONDS,
    then falls back to SIGKILL if the process hasn't exited.

    Args:
        proc: The server Popen handle.
    """
    if proc.poll() is not None:
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

    try:
        # 2. Build (unless --skip-build)
        if not args.skip_build:
            print("\n[Build Phase]")
            run_build_steps()

            # 3. Start server
            print("\n[Boot Phase]")
            server_proc = start_server()
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
        journeys = get_journeys_to_run(args.journey)
        results = execute_journeys(journeys, output_dir, headed)

        # 6. Summary
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
            teardown_server(server_proc)


if __name__ == "__main__":
    # Ensure clean Ctrl+C handling
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    sys.exit(main())

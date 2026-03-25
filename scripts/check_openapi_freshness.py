"""Check that the committed gui/openapi.json matches the live FastAPI spec.

Boots the FastAPI app, fetches /openapi.json, and compares against the
committed spec file. Exits 0 on match, 1 on mismatch or error.

Usage:
    uv run python scripts/check_openapi_freshness.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

COMMITTED_SPEC = Path("gui/openapi.json")
HOST = "127.0.0.1"
PORT = 18765  # Use a non-default port to avoid conflicts
BOOT_TIMEOUT = 20  # seconds
POLL_INTERVAL = 0.3  # seconds


def start_server() -> subprocess.Popen[bytes]:
    """Start the FastAPI server as a subprocess."""
    env_overrides = {
        "STOAT_API_HOST": HOST,
        "STOAT_API_PORT": str(PORT),
        "STOAT_LOG_LEVEL": "WARNING",
        # Use a non-existent GUI path so conditional GUI routes are never
        # registered, keeping the spec deterministic across environments.
        "STOAT_GUI_STATIC_PATH": "__nonexistent__",
    }
    import os

    env = {**os.environ, **env_overrides}
    return subprocess.Popen(
        [sys.executable, "-m", "stoat_ferret.api"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def wait_for_ready(timeout: float = BOOT_TIMEOUT) -> bool:
    """Poll /health/live until the server responds or timeout."""
    url = f"http://{HOST}:{PORT}/health/live"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            resp = urllib.request.urlopen(url, timeout=2)
            if resp.status == 200:
                return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(POLL_INTERVAL)
    return False


def fetch_live_spec() -> dict[str, object]:
    """Fetch the live OpenAPI spec from the running server."""
    url = f"http://{HOST}:{PORT}/openapi.json"
    resp = urllib.request.urlopen(url, timeout=10)
    result: dict[str, object] = json.loads(resp.read())
    return result


def normalize(spec: dict[str, object]) -> str:
    """Normalize a spec dict to sorted JSON string for comparison."""
    return json.dumps(spec, sort_keys=True, indent=2)


def find_enum_fields(spec: dict[str, object]) -> list[str]:
    """Find all schema properties that use the enum keyword.

    Returns a list of descriptive paths where enum is used.
    """
    found: list[str] = []
    _walk_for_enums(spec, "", found)
    return found


def _walk_for_enums(obj: object, path: str, found: list[str]) -> None:
    """Recursively walk a JSON structure looking for enum keywords."""
    if isinstance(obj, dict):
        if "enum" in obj and "type" in obj:
            found.append(path or "/")
        for key, value in obj.items():
            _walk_for_enums(value, f"{path}/{key}", found)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _walk_for_enums(item, f"{path}[{i}]", found)


def diff_specs(committed: str, live: str) -> str:
    """Produce a human-readable diff between two JSON strings."""
    committed_lines = committed.splitlines(keepends=True)
    live_lines = live.splitlines(keepends=True)

    import difflib

    diff = difflib.unified_diff(
        committed_lines,
        live_lines,
        fromfile="gui/openapi.json (committed)",
        tofile="/openapi.json (live)",
    )
    return "".join(diff)


def main() -> int:
    """Run the OpenAPI freshness check."""
    # Check committed spec exists
    if not COMMITTED_SPEC.exists():
        print(f"ERROR: Committed spec not found at {COMMITTED_SPEC}")
        return 1

    committed_spec = json.loads(COMMITTED_SPEC.read_text(encoding="utf-8"))

    # Boot server
    print(f"Starting server on {HOST}:{PORT}...")
    proc = start_server()
    try:
        if not wait_for_ready():
            stderr = proc.stderr.read().decode() if proc.stderr else ""
            print(f"ERROR: Server failed to start within {BOOT_TIMEOUT}s")
            if stderr:
                print(f"Server stderr:\n{stderr}")
            return 1

        print("Server is ready. Fetching live OpenAPI spec...")
        live_spec = fetch_live_spec()

        # Normalize and compare
        committed_json = normalize(committed_spec)
        live_json = normalize(live_spec)

        if committed_json != live_json:
            diff_output = diff_specs(committed_json, live_json)
            print("FAIL: Committed gui/openapi.json does not match live spec.")
            print("Diff (committed vs live):")
            print(diff_output)
            print(
                "\nTo fix: run the server locally and save /openapi.json "
                "to gui/openapi.json with sorted keys."
            )
            return 1

        print("PASS: Committed spec matches live spec.")

        # Verify enum format
        enum_fields = find_enum_fields(live_spec)
        if not enum_fields:
            print(
                "WARN: No enum fields found in OpenAPI spec. "
                "Expected at least one enum with {type: string, enum: [...]} format."
            )
            # This is a warning, not a failure — the spec may legitimately have no enums yet
        else:
            print(f"PASS: Found {len(enum_fields)} enum field(s) in spec:")
            for field in enum_fields:
                print(f"  - {field}")

        return 0
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()


if __name__ == "__main__":
    sys.exit(main())

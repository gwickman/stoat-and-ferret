#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Verify render output evidence fields are populated for a completed job."""

import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify render evidence fields",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Default mode queries GET /render/{job_id} and checks that status=='completed',\n"
            "output_path is non-empty, and progress==1.0.\n\n"
            "--full mode queries GET /render/{job_id}/evidence and checks command_args,\n"
            "exit_code, and output_size_bytes (requires STOAT_RENDER_EVIDENCE_FULL_ACCESS=true)."
        ),
    )
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--base-url", default="http://localhost:8765")
    parser.add_argument(
        "--full",
        action="store_true",
        help=(
            "Check full evidence endpoint (GET /render/{job_id}/evidence): "
            "asserts command_args, exit_code, and output_size_bytes are populated. "
            "Requires STOAT_RENDER_EVIDENCE_FULL_ACCESS=true on the server."
        ),
    )
    args = parser.parse_args()

    if args.full:
        url = f"{args.base_url}/api/v1/render/{args.job_id}/evidence"
        required_fields = ["command_args", "exit_code", "output_size_bytes"]
        check_mode = "full"
    else:
        url = f"{args.base_url}/api/v1/render/{args.job_id}"
        required_fields = []
        check_mode = "default"

    try:
        with urllib.request.urlopen(url) as resp:
            data = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        print(f"FAIL: HTTP {e.code} from {url}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"FAIL: {e}", file=sys.stderr)
        sys.exit(1)

    failures = []

    if check_mode == "full":
        for field in required_fields:
            val = data.get(field)
            if val is None or val == "" or val == []:
                failures.append(f"  {field}: absent or empty (got {val!r})")
    else:
        status = data.get("status")
        output_path = data.get("output_path")
        progress = data.get("progress")
        if status != "completed":
            failures.append(f"  status: expected 'completed', got {status!r}")
        if not output_path:
            failures.append(f"  output_path: absent or empty (got {output_path!r})")
        if progress != 1.0:
            failures.append(f"  progress: expected 1.0, got {progress!r}")

    if failures:
        print(f"FAIL: {len(failures)} check(s) failed:", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(1)

    print(f"PASS: all required evidence fields populated for job {args.job_id}")
    sys.exit(0)


if __name__ == "__main__":
    main()

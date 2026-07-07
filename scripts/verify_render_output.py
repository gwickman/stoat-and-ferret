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
    parser = argparse.ArgumentParser(description="Verify render evidence fields")
    parser.add_argument("--job-id", required=True)
    parser.add_argument("--base-url", default="http://localhost:8765")
    parser.add_argument(
        "--full",
        action="store_true",
        help="Check full evidence endpoint (requires STOAT_RENDER_EVIDENCE_FULL_ACCESS=true)",
    )
    args = parser.parse_args()

    if args.full:
        url = f"{args.base_url}/api/v1/render/{args.job_id}/evidence"
        required_fields = ["command_args", "exit_code", "output_size_bytes"]
    else:
        url = f"{args.base_url}/api/v1/render/{args.job_id}"
        required_fields = ["exit_code", "output_size_bytes"]

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
    for field in required_fields:
        val = data.get(field)
        if val is None or val == "" or val == []:
            failures.append(f"  {field}: absent or empty (got {val!r})")

    if failures:
        print(f"FAIL: {len(failures)} evidence field(s) missing:", file=sys.stderr)
        for f in failures:
            print(f, file=sys.stderr)
        sys.exit(1)

    print(f"PASS: all required evidence fields populated for job {args.job_id}")
    sys.exit(0)


if __name__ == "__main__":
    main()

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""QC assertion helpers for Release 2 test infrastructure."""

from __future__ import annotations

from typing import Any


def assert_qc_check(
    report: dict[str, Any],
    check_id: str,
    expected_pass: bool,
    measured_range: tuple[float, float],
) -> None:
    """Assert pass/fail and measured-vs-target on a named QC check.

    Raises KeyError if check_id not in report.
    Raises AssertionError if pass status or measured value is unexpected.
    """
    check: dict[str, Any] = report[check_id]  # KeyError if missing
    assert check["pass"] == expected_pass, (
        f"QC check {check_id}: expected pass={expected_pass}, got {check['pass']}"
    )
    measured = check.get("measured")
    if measured is not None:
        lo, hi = measured_range
        assert lo <= measured <= hi, (
            f"QC check {check_id}: measured {measured} outside range [{lo}, {hi}]"
        )

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit tests for assert_qc_check helper."""

from __future__ import annotations

import pytest

from tests.qc.helpers import assert_qc_check


def test_assert_qc_check_passes_when_conditions_met() -> None:
    """assert_qc_check passes when pass status and measured value match expectations."""
    report = {"LUFS": {"pass": True, "measured": -22.5}}
    assert_qc_check(report, "LUFS", expected_pass=True, measured_range=(-23, -22))


def test_assert_qc_check_raises_when_pass_status_wrong() -> None:
    """assert_qc_check raises AssertionError when pass status does not match."""
    report = {"LUFS": {"pass": False, "measured": -22.5}}
    with pytest.raises(AssertionError, match="expected pass=True"):
        assert_qc_check(report, "LUFS", expected_pass=True, measured_range=(-23, -22))


def test_assert_qc_check_raises_when_measured_out_of_range() -> None:
    """assert_qc_check raises AssertionError when measured value is outside range."""
    report = {"LUFS": {"pass": True, "measured": -20.0}}
    with pytest.raises(AssertionError, match="outside range"):
        assert_qc_check(report, "LUFS", expected_pass=True, measured_range=(-23, -22))


def test_assert_qc_check_raises_key_error_for_missing_check() -> None:
    """assert_qc_check raises KeyError when check_id is not in report."""
    report = {"LUFS": {"pass": True, "measured": -22.5}}
    with pytest.raises(KeyError):
        assert_qc_check(report, "MISSING_CHECK", expected_pass=True, measured_range=(-23, -22))


def test_assert_qc_check_passes_without_measured_field() -> None:
    """assert_qc_check passes when measured field is absent and pass status matches."""
    report = {"CLIPPING": {"pass": False}}
    assert_qc_check(report, "CLIPPING", expected_pass=False, measured_range=(0.0, 1.0))


def test_assert_qc_check_at_range_boundary() -> None:
    """assert_qc_check passes when measured value is exactly at a boundary."""
    report = {"LUFS": {"pass": True, "measured": -23.0}}
    assert_qc_check(report, "LUFS", expected_pass=True, measured_range=(-23, -22))

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Per-OC assertion tests against the golden QC fixture.

Tests run without FFmpeg — they load golden_qc_report.json and assert that
each machine-verifiable OC maps to the expected check IDs. Tests skip
gracefully when the fixture is still a placeholder (check values are null).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.qc.oc_mapping import OC_HUMAN_ONLY, OC_TO_QC_CHECK

GOLDEN_FIXTURE = Path(__file__).parent / "fixtures" / "golden_qc_report.json"


def _load_fixture() -> dict[str, Any]:
    return json.loads(GOLDEN_FIXTURE.read_text())  # type: ignore[no-any-return]


def _is_placeholder(fixture: dict[str, Any]) -> bool:
    return fixture.get("status") == "placeholder"


class TestOcMapping:
    def test_oc_to_qc_check_has_11_entries(self) -> None:
        assert len(OC_TO_QC_CHECK) == 11

    def test_every_check_id_is_non_empty_string(self) -> None:
        for oc, check_ids in OC_TO_QC_CHECK.items():
            assert check_ids, f"{oc} has empty check list"
            for cid in check_ids:
                assert isinstance(cid, str) and cid, f"{oc} has blank check id"

    def test_oc_human_only_has_four_entries(self) -> None:
        assert len(OC_HUMAN_ONLY) == 4

    def test_human_only_ocs_not_in_machine_verifiable_map(self) -> None:
        for oc in OC_HUMAN_ONLY:
            assert oc not in OC_TO_QC_CHECK, (
                f"{oc} appears in both OC_HUMAN_ONLY and OC_TO_QC_CHECK"
            )

    def test_oc_3_in_human_only(self) -> None:
        assert "OC-3" in OC_HUMAN_ONLY

    def test_oc_11_maps_to_loudness_and_peak(self) -> None:
        assert OC_TO_QC_CHECK["OC-11"] == ["loudness_integrated", "true_peak"]

    def test_chapters_present_covers_oc1_and_oc16(self) -> None:
        assert "chapters_present" in OC_TO_QC_CHECK["OC-1"]
        assert "chapters_present" in OC_TO_QC_CHECK["OC-16"]


class TestOcAssertionsAgainstFixture:
    """Assert each OC's check IDs are present in the golden fixture."""

    def test_golden_fixture_exists(self) -> None:
        assert GOLDEN_FIXTURE.exists(), f"Golden fixture missing: {GOLDEN_FIXTURE}"

    def test_golden_fixture_has_checks_key(self) -> None:
        fixture = _load_fixture()
        assert "checks" in fixture

    def test_all_machine_verifiable_check_ids_in_fixture(self) -> None:
        fixture = _load_fixture()
        checks = fixture.get("checks", {})
        for oc, check_ids in OC_TO_QC_CHECK.items():
            for cid in check_ids:
                assert cid in checks, f"OC {oc}: check_id '{cid}' missing from fixture"

    @pytest.mark.parametrize("oc,check_ids", list(OC_TO_QC_CHECK.items()))
    def test_oc_check_ids_present_in_fixture(self, oc: str, check_ids: list[str]) -> None:
        fixture = _load_fixture()
        checks = fixture.get("checks", {})
        for cid in check_ids:
            assert cid in checks, f"OC {oc}: check_id '{cid}' not found in fixture checks"

    @pytest.mark.parametrize("oc,check_ids", list(OC_TO_QC_CHECK.items()))
    def test_oc_fixture_pass_field_present_or_placeholder(
        self, oc: str, check_ids: list[str]
    ) -> None:
        fixture = _load_fixture()
        if _is_placeholder(fixture):
            pytest.skip("Golden fixture is a placeholder — skipping pass/fail assertions")
        checks = fixture["checks"]
        for cid in check_ids:
            assert "pass" in checks[cid], f"OC {oc}: check '{cid}' missing 'pass' field"

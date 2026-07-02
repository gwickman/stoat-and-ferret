# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path

BASELINE = Path("tests/fixtures/baseline-uat-failures.json")


def test_no_multi_clip_not_supported_in_baseline() -> None:
    """Regression guard: MULTI_CLIP_NOT_SUPPORTED must not appear in the UAT baseline.

    This string was a v089-era placeholder error code for the pre-v090 multi-clip
    rejection path (BL-551). The multi-clip render path shipped in v090 (BL-505),
    making any baseline entry referencing this code stale. BL-565 removes the stale
    J204/J501 entries; this test guards against re-introduction.
    """
    content = BASELINE.read_text()
    assert "MULTI_CLIP_NOT_SUPPORTED" not in content


def test_baseline_is_valid_json() -> None:
    """The baseline-uat-failures.json file must be parseable JSON at all times."""
    content = BASELINE.read_text()
    data = json.loads(content)
    assert isinstance(data, list)

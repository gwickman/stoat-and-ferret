"""Non-FFmpeg-gated unit tests for LoudnormPassOneResult.from_stderr() parser (BL-428).

These tests use captured stderr fixtures and do NOT require FFmpeg.
No @pytest.mark.skipif(not STOAT_TEST_FFMPEG, ...) guard here.
"""

from __future__ import annotations

import pytest

from stoat_ferret.effects.definitions import LoudnormPassOneResult, RenderError

# Captured loudnorm pass-1 JSON block as emitted by FFmpeg stderr
_LOUDNORM_STDERR_FIXTURE = """\
[Parsed_loudnorm_0 @ 0x00007f80] {
\t"input_i" : "-18.55",
\t"input_tp" : "-2.00",
\t"input_lra" : "9.20",
\t"input_thresh" : "-28.82",
\t"output_i" : "-16.00",
\t"output_tp" : "-1.00",
\t"output_lra" : "9.20",
\t"output_thresh" : "-26.27",
\t"normalization_type" : "dynamic",
\t"target_offset" : "0.32"
}
"""


def test_from_stderr_parses_4_fields_from_fixture() -> None:
    """from_stderr() extracts measured_i, measured_lra, measured_tp, offset from fixture."""
    result = LoudnormPassOneResult.from_stderr(_LOUDNORM_STDERR_FIXTURE)

    assert abs(result.measured_i - (-18.55)) < 1e-6, f"measured_i={result.measured_i}"
    assert abs(result.measured_lra - 9.20) < 1e-6, f"measured_lra={result.measured_lra}"
    assert abs(result.measured_tp - (-2.00)) < 1e-6, f"measured_tp={result.measured_tp}"
    assert abs(result.offset - 0.32) < 1e-6, f"offset={result.offset}"


def test_from_stderr_raises_render_error_on_malformed_json() -> None:
    """from_stderr() raises RenderError when the JSON block is malformed."""
    bad_stderr = "[Parsed_loudnorm_0 @ 0x00007f80] { invalid json !! }"
    with pytest.raises(RenderError, match="malformed"):
        LoudnormPassOneResult.from_stderr(bad_stderr)


def test_from_stderr_raises_render_error_when_no_json_block() -> None:
    """from_stderr() raises RenderError when no JSON block is present."""
    with pytest.raises(RenderError, match="no JSON block"):
        LoudnormPassOneResult.from_stderr("no json here at all")


def test_from_stderr_raises_render_error_on_missing_fields() -> None:
    """from_stderr() raises RenderError when required fields are absent."""
    incomplete = '{"input_i": "-18.0"}'  # missing input_lra, input_tp, target_offset
    with pytest.raises(RenderError, match="missing required fields"):
        LoudnormPassOneResult.from_stderr(incomplete)


def test_from_stderr_raises_render_error_on_non_float_field() -> None:
    """from_stderr() raises RenderError when a field value is not a valid float."""
    bad_value = (
        '{"input_i": "not_a_number", "input_lra": "9.2",'
        ' "input_tp": "-2.0", "target_offset": "0.3"}'
    )
    with pytest.raises(RenderError):
        LoudnormPassOneResult.from_stderr(bad_value)

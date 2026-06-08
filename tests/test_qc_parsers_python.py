"""Python smoke tests for QC measurement parser PyO3 bindings (BL-423-AC-6)."""

from __future__ import annotations

import pytest

import stoat_ferret_core as sfc

# ---------------------------------------------------------------------------
# Fixtures (representative FFmpeg output from interface-contracts.md)
# ---------------------------------------------------------------------------

LOUDNORM_JSON = """
{
  "input_i": "-16.23",
  "input_lra": "4.20",
  "input_tp": "-1.09"
}
"""

ASTATS_TEXT = """
[Parsed_astats_0 @ 0x7f001] Channel 1
[Parsed_astats_0 @ 0x7f001] Peak level dB: -3.200
[Parsed_astats_0 @ 0x7f001] Peak count: 0
[Parsed_astats_0 @ 0x7f001] Overall
[Parsed_astats_0 @ 0x7f001] Peak level dB: -0.003
[Parsed_astats_0 @ 0x7f001] Peak count: 12
"""

SILENCE_TEXT = """
[silencedetect @ 0x7f001] silence_start: 0.123456
[silencedetect @ 0x7f001] silence_end: 1.234567 | silence_duration: 1.111111
"""

SPECTRAL_TEXT = """
frame:0   pts:0     pts_time:0
lavfi.aspectralstats.1.mean=0.001234
lavfi.aspectralstats.2.mean=0.002345
"""

BLACKDETECT_TEXT = """
[blackdetect @ 0x7f001] black_start:0.123 black_end:1.234 black_duration:1.111
"""

FREEZEDETECT_TEXT = """
[freezedetect @ 0x7f001] lavfi.freezedetect.freeze_start: 1.234
[freezedetect @ 0x7f001] lavfi.freezedetect.freeze_end: 5.678
"""


# ---------------------------------------------------------------------------
# parse_loudness_report
# ---------------------------------------------------------------------------


def test_parse_loudness_report_returns_loudness_report():
    result = sfc.parse_loudness_report(LOUDNORM_JSON)
    assert isinstance(result, sfc.LoudnessReport)


def test_parse_loudness_report_field_values():
    result = sfc.parse_loudness_report(LOUDNORM_JSON)
    assert abs(result.integrated_lufs - (-16.23)) < 1e-9
    assert abs(result.lra - 4.20) < 1e-9
    assert abs(result.true_peak_dbtp - (-1.09)) < 1e-9


def test_parse_loudness_report_raises_on_empty():
    with pytest.raises(ValueError):
        sfc.parse_loudness_report("")


def test_loudness_report_repr():
    result = sfc.parse_loudness_report(LOUDNORM_JSON)
    r = repr(result)
    assert "LoudnessReport" in r
    assert "integrated_lufs" in r


def test_loudness_report_constructor():
    r = sfc.LoudnessReport(-23.0, 5.0, -1.5)
    assert r.integrated_lufs == -23.0
    assert r.lra == 5.0
    assert r.true_peak_dbtp == -1.5


# ---------------------------------------------------------------------------
# parse_peak_report
# ---------------------------------------------------------------------------


def test_parse_peak_report_returns_peak_report():
    result = sfc.parse_peak_report(ASTATS_TEXT)
    assert isinstance(result, sfc.PeakReport)


def test_parse_peak_report_field_values():
    result = sfc.parse_peak_report(ASTATS_TEXT)
    assert abs(result.peak_level - (-0.003)) < 1e-9
    assert result.clipped_samples == 12


def test_parse_peak_report_raises_on_empty():
    with pytest.raises(ValueError):
        sfc.parse_peak_report("")


def test_peak_report_repr():
    result = sfc.parse_peak_report(ASTATS_TEXT)
    r = repr(result)
    assert "PeakReport" in r


def test_peak_report_constructor():
    r = sfc.PeakReport(-0.5, 3)
    assert r.peak_level == -0.5
    assert r.clipped_samples == 3


# ---------------------------------------------------------------------------
# parse_silence_report
# ---------------------------------------------------------------------------


def test_parse_silence_report_returns_silence_report():
    result = sfc.parse_silence_report(SILENCE_TEXT)
    assert isinstance(result, sfc.SilenceReport)


def test_parse_silence_report_regions_type():
    result = sfc.parse_silence_report(SILENCE_TEXT)
    assert isinstance(result.regions, list)
    assert len(result.regions) == 1
    assert isinstance(result.regions[0], sfc.SilenceRegion)


def test_parse_silence_report_region_values():
    result = sfc.parse_silence_report(SILENCE_TEXT)
    region = result.regions[0]
    assert abs(region.start - 0.123456) < 1e-6
    assert abs(region.end - 1.234567) < 1e-6


def test_parse_silence_report_empty_input_ok():
    result = sfc.parse_silence_report("")
    assert result.regions == []


def test_silence_region_constructor():
    sr = sfc.SilenceRegion(1.0, 2.5)
    assert sr.start == 1.0
    assert sr.end == 2.5


def test_silence_report_constructor():
    rpt = sfc.SilenceReport([sfc.SilenceRegion(0.5, 1.0)])
    assert len(rpt.regions) == 1


# ---------------------------------------------------------------------------
# parse_spectral_report
# ---------------------------------------------------------------------------


def test_parse_spectral_report_returns_spectral_report():
    result = sfc.parse_spectral_report(SPECTRAL_TEXT)
    assert isinstance(result, sfc.SpectralReport)


def test_parse_spectral_report_field_values():
    result = sfc.parse_spectral_report(SPECTRAL_TEXT)
    assert result.channel_count == 2
    assert len(result.channel_means) == 2
    assert abs(result.channel_means[0] - 0.001234) < 1e-9
    assert abs(result.channel_means[1] - 0.002345) < 1e-9


def test_parse_spectral_report_raises_on_empty():
    with pytest.raises(ValueError):
        sfc.parse_spectral_report("")


def test_spectral_report_constructor():
    r = sfc.SpectralReport(2, [0.001, 0.002])
    assert r.channel_count == 2
    assert r.channel_means == [0.001, 0.002]


# ---------------------------------------------------------------------------
# parse_video_defect_report
# ---------------------------------------------------------------------------


def test_parse_video_defect_report_returns_video_defect_report():
    combined = BLACKDETECT_TEXT + FREEZEDETECT_TEXT
    result = sfc.parse_video_defect_report(combined)
    assert isinstance(result, sfc.VideoDefectReport)


def test_parse_video_defect_report_black_regions():
    result = sfc.parse_video_defect_report(BLACKDETECT_TEXT)
    assert isinstance(result.black_regions, list)
    assert len(result.black_regions) == 1
    assert isinstance(result.black_regions[0], sfc.Region)
    assert abs(result.black_regions[0].start - 0.123) < 1e-9
    assert abs(result.black_regions[0].end - 1.234) < 1e-9
    assert result.freeze_regions == []


def test_parse_video_defect_report_freeze_regions():
    result = sfc.parse_video_defect_report(FREEZEDETECT_TEXT)
    assert result.black_regions == []
    assert len(result.freeze_regions) == 1
    assert isinstance(result.freeze_regions[0], sfc.Region)
    assert abs(result.freeze_regions[0].start - 1.234) < 1e-9
    assert abs(result.freeze_regions[0].end - 5.678) < 1e-9


def test_parse_video_defect_report_empty_input_ok():
    result = sfc.parse_video_defect_report("")
    assert result.black_regions == []
    assert result.freeze_regions == []


def test_region_constructor():
    r = sfc.Region(1.0, 3.5)
    assert r.start == 1.0
    assert r.end == 3.5


def test_video_defect_report_constructor():
    rpt = sfc.VideoDefectReport([sfc.Region(0.0, 1.0)], [])
    assert len(rpt.black_regions) == 1
    assert rpt.freeze_regions == []


# ---------------------------------------------------------------------------
# __all__ exports
# ---------------------------------------------------------------------------


def test_all_exports_present():
    names = [
        "LoudnessReport",
        "PeakReport",
        "Region",
        "SilenceRegion",
        "SilenceReport",
        "SpectralReport",
        "VideoDefectReport",
        "parse_loudness_report",
        "parse_peak_report",
        "parse_silence_report",
        "parse_spectral_report",
        "parse_video_defect_report",
    ]
    for name in names:
        assert name in sfc.__all__, f"{name} missing from __all__"
        assert hasattr(sfc, name), f"{name} not accessible on sfc module"

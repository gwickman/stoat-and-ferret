# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for SubBassBuilder and ducking_effect_schema (BL-442)."""

from __future__ import annotations

import pytest

from stoat_ferret_core import SubBassBuilder, ducking_effect_schema

# ---------------------------------------------------------------------------
# SubBassBuilder unit tests
# ---------------------------------------------------------------------------


def test_sub_bass_contains_lowpass() -> None:
    """build() produces a lowpass filter."""
    chain = SubBassBuilder(80.0).build()
    assert "lowpass" in str(chain)


def test_sub_bass_cutoff_in_filter() -> None:
    """Cutoff frequency appears in the filter string."""
    chain = SubBassBuilder(80.0).build()
    assert "f=80.0" in str(chain)


def test_sub_bass_no_volume_at_zero_db() -> None:
    """No volume filter is added when level_db is 0."""
    chain = SubBassBuilder(80.0).build()
    assert "volume" not in str(chain)


def test_sub_bass_level_db_adds_volume() -> None:
    """Positive level_db adds a volume filter."""
    chain = SubBassBuilder(80.0).with_level_db(6.0).build()
    assert "volume" in str(chain)


def test_sub_bass_negative_level_db_adds_volume() -> None:
    """Negative level_db also adds a volume filter."""
    chain = SubBassBuilder(80.0).with_level_db(-6.0).build()
    assert "volume" in str(chain)


def test_sub_bass_cutoff_hz_property() -> None:
    """cutoff_hz property returns the configured value."""
    b = SubBassBuilder(60.0)
    assert b.cutoff_hz == 60.0


def test_sub_bass_level_db_property() -> None:
    """level_db property returns the configured value."""
    b = SubBassBuilder(80.0).with_level_db(-3.0)
    assert b.level_db == -3.0


def test_sub_bass_out_of_range_cutoff_low() -> None:
    """cutoff_hz below 20 Hz raises ValueError."""
    with pytest.raises(ValueError):
        SubBassBuilder(19.9)


def test_sub_bass_out_of_range_cutoff_high() -> None:
    """cutoff_hz above 300 Hz raises ValueError."""
    with pytest.raises(ValueError):
        SubBassBuilder(300.1)


def test_sub_bass_out_of_range_level_db() -> None:
    """level_db outside [-20, 20] raises ValueError."""
    builder_high = SubBassBuilder(80.0)
    with pytest.raises(ValueError):
        builder_high.with_level_db(21.0)
    builder_low = SubBassBuilder(80.0)
    with pytest.raises(ValueError):
        builder_low.with_level_db(-21.0)


def test_sub_bass_boundary_values() -> None:
    """Boundary values 20 Hz and 300 Hz are accepted."""
    assert SubBassBuilder(20.0).cutoff_hz == 20.0
    assert SubBassBuilder(300.0).cutoff_hz == 300.0


def test_sub_bass_repr() -> None:
    """__repr__ includes cutoff_hz and level_db."""
    b = SubBassBuilder(80.5).with_level_db(-6.0)
    r = repr(b)
    assert "SubBassBuilder" in r
    assert "80.5" in r


# ---------------------------------------------------------------------------
# ducking_effect_schema unit tests
# ---------------------------------------------------------------------------


def test_ducking_schema_returns_four_items() -> None:
    """ducking_effect_schema returns exactly 4 ParameterSchema items."""
    schemas = ducking_effect_schema()
    assert len(schemas) == 4


def test_ducking_schema_field_names() -> None:
    """All four ducking parameters are present by name."""
    names = {s.name for s in ducking_effect_schema()}
    assert names == {"threshold", "ratio", "attack", "release"}


def test_ducking_schema_all_float_type() -> None:
    """All ducking parameters have param_type 'float'."""
    for s in ducking_effect_schema():
        assert s.param_type == "float"


def test_ducking_schema_all_have_bounds() -> None:
    """All ducking parameters have min_value and max_value set."""
    for s in ducking_effect_schema():
        assert s.min_value is not None, f"{s.name} missing min_value"
        assert s.max_value is not None, f"{s.name} missing max_value"


def test_ducking_schema_threshold_range() -> None:
    """Threshold bounds match the DuckingPattern validation range."""
    schema = next(s for s in ducking_effect_schema() if s.name == "threshold")
    assert schema.min_value is not None and schema.min_value > 0.0
    assert schema.max_value == 1.0


def test_ducking_schema_ai_hints_non_empty() -> None:
    """All parameters have non-empty AI hints."""
    for s in ducking_effect_schema():
        assert s.ai_hint, f"{s.name} has empty ai_hint"

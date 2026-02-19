"""Parity and integration tests for audio mixing filter builders.

Tests the PyO3 bindings for VolumeBuilder, AfadeBuilder, AmixBuilder,
and DuckingPattern, verifying Python calls produce identical filter strings
to direct Rust construction.
"""

from __future__ import annotations

import pytest


class TestVolumeBuilderParity:
    """Parity tests for VolumeBuilder."""

    def test_basic_volume(self) -> None:
        """Test basic volume filter produces correct string."""
        from stoat_ferret_core import VolumeBuilder

        builder = VolumeBuilder(0.5)
        f = builder.build()
        assert str(f) == "volume=volume=0.5"

    def test_zero_volume(self) -> None:
        """Test zero volume (silence)."""
        from stoat_ferret_core import VolumeBuilder

        f = VolumeBuilder(0.0).build()
        assert str(f) == "volume=volume=0"

    def test_normal_volume(self) -> None:
        """Test normal volume (1.0)."""
        from stoat_ferret_core import VolumeBuilder

        f = VolumeBuilder(1.0).build()
        assert str(f) == "volume=volume=1"

    def test_max_volume(self) -> None:
        """Test maximum volume (10.0)."""
        from stoat_ferret_core import VolumeBuilder

        f = VolumeBuilder(10.0).build()
        assert str(f) == "volume=volume=10"

    def test_db_mode(self) -> None:
        """Test dB volume mode."""
        from stoat_ferret_core import VolumeBuilder

        f = VolumeBuilder.from_db("3dB").build()
        assert str(f) == "volume=volume=3dB"

    def test_negative_db(self) -> None:
        """Test negative dB volume."""
        from stoat_ferret_core import VolumeBuilder

        f = VolumeBuilder.from_db("-6dB").build()
        assert str(f) == "volume=volume=-6dB"

    def test_precision(self) -> None:
        """Test precision option."""
        from stoat_ferret_core import VolumeBuilder

        f = VolumeBuilder(0.5).precision("float").build()
        s = str(f)
        assert "volume=0.5" in s
        assert "precision=float" in s

    def test_invalid_volume_below(self) -> None:
        """Test volume below range raises ValueError."""
        from stoat_ferret_core import VolumeBuilder

        with pytest.raises(ValueError):
            VolumeBuilder(-0.1)

    def test_invalid_volume_above(self) -> None:
        """Test volume above range raises ValueError."""
        from stoat_ferret_core import VolumeBuilder

        with pytest.raises(ValueError):
            VolumeBuilder(10.1)

    def test_invalid_db(self) -> None:
        """Test invalid dB string raises ValueError."""
        from stoat_ferret_core import VolumeBuilder

        with pytest.raises(ValueError):
            VolumeBuilder.from_db("loud")

    def test_invalid_precision(self) -> None:
        """Test invalid precision raises ValueError."""
        from stoat_ferret_core import VolumeBuilder

        with pytest.raises(ValueError):
            VolumeBuilder(1.0).precision("invalid")


class TestAfadeBuilderParity:
    """Parity tests for AfadeBuilder."""

    def test_fade_in(self) -> None:
        """Test fade in produces correct string."""
        from stoat_ferret_core import AfadeBuilder

        f = AfadeBuilder("in", 3.0).build()
        assert str(f) == "afade=t=in:d=3"

    def test_fade_out(self) -> None:
        """Test fade out produces correct string."""
        from stoat_ferret_core import AfadeBuilder

        f = AfadeBuilder("out", 2.0).build()
        assert str(f) == "afade=t=out:d=2"

    def test_with_start_time(self) -> None:
        """Test fade with start time."""
        from stoat_ferret_core import AfadeBuilder

        f = AfadeBuilder("out", 2.0).start_time(10.0).build()
        assert str(f) == "afade=t=out:d=2:st=10"

    def test_with_curve(self) -> None:
        """Test fade with curve type."""
        from stoat_ferret_core import AfadeBuilder

        f = AfadeBuilder("in", 1.5).curve("qsin").build()
        assert str(f) == "afade=t=in:d=1.5:curve=qsin"

    def test_all_options(self) -> None:
        """Test fade with all options."""
        from stoat_ferret_core import AfadeBuilder

        f = AfadeBuilder("out", 2.5).start_time(5.0).curve("log").build()
        assert str(f) == "afade=t=out:d=2.5:st=5:curve=log"

    def test_all_curve_types(self) -> None:
        """Test all 11 curve types produce valid filter strings."""
        from stoat_ferret_core import AfadeBuilder

        curves = [
            "tri",
            "qsin",
            "hsin",
            "esin",
            "log",
            "ipar",
            "qua",
            "cub",
            "squ",
            "cbr",
            "par",
        ]
        for curve in curves:
            f = AfadeBuilder("in", 1.0).curve(curve).build()
            assert f"curve={curve}" in str(f), f"Missing curve {curve}"

    def test_invalid_type(self) -> None:
        """Test invalid fade type raises ValueError."""
        from stoat_ferret_core import AfadeBuilder

        with pytest.raises(ValueError):
            AfadeBuilder("up", 1.0)

    def test_invalid_curve(self) -> None:
        """Test invalid curve raises ValueError."""
        from stoat_ferret_core import AfadeBuilder

        with pytest.raises(ValueError):
            AfadeBuilder("in", 1.0).curve("invalid")

    def test_zero_duration(self) -> None:
        """Test zero duration raises ValueError."""
        from stoat_ferret_core import AfadeBuilder

        with pytest.raises(ValueError):
            AfadeBuilder("in", 0.0)

    def test_fractional_duration(self) -> None:
        """Test fractional duration."""
        from stoat_ferret_core import AfadeBuilder

        f = AfadeBuilder("in", 0.5).build()
        assert str(f) == "afade=t=in:d=0.5"

    def test_large_duration(self) -> None:
        """Test large duration handled gracefully."""
        from stoat_ferret_core import AfadeBuilder

        f = AfadeBuilder("in", 999.0).build()
        assert str(f) == "afade=t=in:d=999"


class TestAmixBuilderParity:
    """Parity tests for AmixBuilder."""

    def test_basic_mix(self) -> None:
        """Test basic amix filter."""
        from stoat_ferret_core import AmixBuilder

        f = AmixBuilder(4).build()
        assert str(f) == "amix=inputs=4"

    def test_two_inputs(self) -> None:
        """Test minimum input count."""
        from stoat_ferret_core import AmixBuilder

        f = AmixBuilder(2).build()
        assert str(f) == "amix=inputs=2"

    def test_max_inputs(self) -> None:
        """Test maximum input count."""
        from stoat_ferret_core import AmixBuilder

        f = AmixBuilder(32).build()
        assert str(f) == "amix=inputs=32"

    def test_duration_mode(self) -> None:
        """Test duration mode option."""
        from stoat_ferret_core import AmixBuilder

        f = AmixBuilder(3).duration_mode("longest").build()
        s = str(f)
        assert "inputs=3" in s
        assert "duration=longest" in s

    def test_weights(self) -> None:
        """Test per-input weights."""
        from stoat_ferret_core import AmixBuilder

        f = AmixBuilder(2).weights([0.8, 0.2]).build()
        assert "weights=0.8 0.2" in str(f)

    def test_normalize(self) -> None:
        """Test normalize flag."""
        from stoat_ferret_core import AmixBuilder

        f = AmixBuilder(2).normalize(False).build()
        assert "normalize=0" in str(f)

    def test_all_options(self) -> None:
        """Test all options combined."""
        from stoat_ferret_core import AmixBuilder

        f = AmixBuilder(3).duration_mode("longest").weights([1.0, 0.5, 0.5]).normalize(True).build()
        s = str(f)
        assert "inputs=3" in s
        assert "duration=longest" in s
        assert "weights=1 0.5 0.5" in s
        assert "normalize=1" in s

    def test_invalid_below_range(self) -> None:
        """Test input count below range raises ValueError."""
        from stoat_ferret_core import AmixBuilder

        with pytest.raises(ValueError):
            AmixBuilder(1)

    def test_invalid_above_range(self) -> None:
        """Test input count above range raises ValueError."""
        from stoat_ferret_core import AmixBuilder

        with pytest.raises(ValueError):
            AmixBuilder(33)

    def test_invalid_duration_mode(self) -> None:
        """Test invalid duration mode raises ValueError."""
        from stoat_ferret_core import AmixBuilder

        with pytest.raises(ValueError):
            AmixBuilder(2).duration_mode("invalid")


class TestDuckingPatternParity:
    """Parity tests for DuckingPattern."""

    def test_default_ducking(self) -> None:
        """Test default ducking pattern produces valid FilterGraph."""
        from stoat_ferret_core import DuckingPattern

        graph = DuckingPattern().build()
        s = str(graph)
        assert "asplit" in s
        assert "sidechaincompress" in s
        assert "threshold=0.125" in s
        assert "ratio=2" in s
        assert "attack=20" in s
        assert "release=250" in s

    def test_custom_params(self) -> None:
        """Test custom ducking parameters."""
        from stoat_ferret_core import DuckingPattern

        graph = DuckingPattern().threshold(0.5).ratio(4.0).attack(50.0).release(500.0).build()
        s = str(graph)
        assert "threshold=0.5" in s
        assert "ratio=4" in s
        assert "attack=50" in s
        assert "release=500" in s

    def test_graph_structure(self) -> None:
        """Test ducking graph has correct chain count."""
        from stoat_ferret_core import DuckingPattern

        graph = DuckingPattern().build()
        s = str(graph)
        # asplit ; sidechaincompress ; anull = 2 semicolons
        assert s.count(";") == 2

    def test_invalid_threshold(self) -> None:
        """Test invalid threshold raises ValueError."""
        from stoat_ferret_core import DuckingPattern

        with pytest.raises(ValueError):
            DuckingPattern().threshold(2.0)

    def test_invalid_ratio(self) -> None:
        """Test invalid ratio raises ValueError."""
        from stoat_ferret_core import DuckingPattern

        with pytest.raises(ValueError):
            DuckingPattern().ratio(25.0)

    def test_invalid_attack(self) -> None:
        """Test invalid attack raises ValueError."""
        from stoat_ferret_core import DuckingPattern

        with pytest.raises(ValueError):
            DuckingPattern().attack(3000.0)

    def test_invalid_release(self) -> None:
        """Test invalid release raises ValueError."""
        from stoat_ferret_core import DuckingPattern

        with pytest.raises(ValueError):
            DuckingPattern().release(10000.0)


class TestEdgeCases:
    """Edge case tests covering silence, clipping prevention, and format mismatches."""

    def test_zero_volume_no_error(self) -> None:
        """Zero-volume input handled without error."""
        from stoat_ferret_core import VolumeBuilder

        f = VolumeBuilder(0.0).build()
        assert "volume=0" in str(f)

    def test_high_volume_with_normalize(self) -> None:
        """Volume > 1.0 combined with amix normalize produces valid output."""
        from stoat_ferret_core import AmixBuilder, VolumeBuilder

        vol = VolumeBuilder(2.0).build()
        amix = AmixBuilder(2).normalize(True).build()
        assert "volume=2" in str(vol)
        assert "normalize=1" in str(amix)

    def test_large_fade_duration(self) -> None:
        """Fade duration longer than audio duration handled gracefully."""
        from stoat_ferret_core import AfadeBuilder

        f = AfadeBuilder("in", 999.0).build()
        assert "d=999" in str(f)

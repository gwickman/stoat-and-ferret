"""Integration tests for transition filter builder PyO3 bindings.

Tests the Rust-Python bindings for FadeBuilder, XfadeBuilder, TransitionType,
and AcrossfadeBuilder.
"""

from __future__ import annotations

import pytest


class TestTransitionType:
    """Tests for TransitionType enum."""

    def test_from_str_basic(self) -> None:
        """Test TransitionType.from_str with common variants."""
        from stoat_ferret_core import TransitionType

        tt = TransitionType.from_str("wipeleft")
        assert tt == TransitionType.Wipeleft

    def test_from_str_all_variants(self) -> None:
        """Test from_str round-trips for all 59 transition types."""
        from stoat_ferret_core import TransitionType

        all_names = [
            "fade",
            "fadeblack",
            "fadewhite",
            "fadegrays",
            "fadefast",
            "fadeslow",
            "wipeleft",
            "wiperight",
            "wipeup",
            "wipedown",
            "wipetl",
            "wipetr",
            "wipebl",
            "wipebr",
            "slideleft",
            "slideright",
            "slideup",
            "slidedown",
            "smoothleft",
            "smoothright",
            "smoothup",
            "smoothdown",
            "circlecrop",
            "rectcrop",
            "circleopen",
            "circleclose",
            "radial",
            "vertopen",
            "vertclose",
            "horzopen",
            "horzclose",
            "dissolve",
            "pixelize",
            "distance",
            "hblur",
            "diagtl",
            "diagtr",
            "diagbl",
            "diagbr",
            "hlslice",
            "hrslice",
            "vuslice",
            "vdslice",
            "squeezeh",
            "squeezev",
            "zoomin",
            "hlwind",
            "hrwind",
            "vuwind",
            "vdwind",
            "coverleft",
            "coverright",
            "coverup",
            "coverdown",
            "revealleft",
            "revealright",
            "revealup",
            "revealdown",
            "custom",
        ]
        assert len(all_names) == 59
        for name in all_names:
            tt = TransitionType.from_str(name)
            assert tt.as_str() == name

    def test_from_str_invalid(self) -> None:
        """Test TransitionType.from_str rejects invalid names."""
        from stoat_ferret_core import TransitionType

        with pytest.raises(ValueError, match="invalid transition type"):
            TransitionType.from_str("nonexistent")

    def test_as_str(self) -> None:
        """Test TransitionType.as_str returns FFmpeg string."""
        from stoat_ferret_core import TransitionType

        assert TransitionType.Dissolve.as_str() == "dissolve"
        assert TransitionType.Wipeleft.as_str() == "wipeleft"
        assert TransitionType.Custom.as_str() == "custom"

    def test_str(self) -> None:
        """Test str() returns FFmpeg string."""
        from stoat_ferret_core import TransitionType

        assert str(TransitionType.Dissolve) == "dissolve"

    def test_repr(self) -> None:
        """Test repr output."""
        from stoat_ferret_core import TransitionType

        r = repr(TransitionType.Dissolve)
        assert "TransitionType" in r
        assert "Dissolve" in r

    def test_equality(self) -> None:
        """Test TransitionType equality."""
        from stoat_ferret_core import TransitionType

        assert TransitionType.Fade == TransitionType.Fade
        assert TransitionType.Fade != TransitionType.Dissolve


class TestFadeBuilder:
    """Tests for FadeBuilder PyO3 bindings."""

    def test_fade_in_basic(self) -> None:
        """Test building a basic fade-in filter."""
        from stoat_ferret_core import FadeBuilder

        f = FadeBuilder("in", 3.0).build()
        assert str(f) == "fade=t=in:d=3"

    def test_fade_out_basic(self) -> None:
        """Test building a basic fade-out filter."""
        from stoat_ferret_core import FadeBuilder

        f = FadeBuilder("out", 2.0).build()
        assert str(f) == "fade=t=out:d=2"

    def test_fade_with_start_time(self) -> None:
        """Test fade with start_time."""
        from stoat_ferret_core import FadeBuilder

        f = FadeBuilder("out", 2.0).start_time(10.0).build()
        assert str(f) == "fade=t=out:d=2:st=10"

    def test_fade_with_color(self) -> None:
        """Test fade with custom color."""
        from stoat_ferret_core import FadeBuilder

        f = FadeBuilder("in", 1.0).color("white").build()
        assert str(f) == "fade=t=in:d=1:c=white"

    def test_fade_with_hex_color(self) -> None:
        """Test fade with hex color."""
        from stoat_ferret_core import FadeBuilder

        f = FadeBuilder("in", 1.0).color("#FF0000").build()
        assert str(f) == "fade=t=in:d=1:c=#FF0000"

    def test_fade_with_alpha(self) -> None:
        """Test fade with alpha channel mode."""
        from stoat_ferret_core import FadeBuilder

        f = FadeBuilder("in", 1.0).alpha(True).build()
        assert str(f) == "fade=t=in:d=1:alpha=1"

    def test_fade_with_nb_frames(self) -> None:
        """Test fade with nb_frames replaces duration."""
        from stoat_ferret_core import FadeBuilder

        f = FadeBuilder("in", 1.0).nb_frames(30).build()
        assert str(f) == "fade=t=in:nb_frames=30"

    def test_fade_all_options(self) -> None:
        """Test fade with all options set."""
        from stoat_ferret_core import FadeBuilder

        f = FadeBuilder("out", 2.5).start_time(5.0).color("white").alpha(True).build()
        s = str(f)
        assert "t=out" in s
        assert "d=2.5" in s
        assert "st=5" in s
        assert "c=white" in s
        assert "alpha=1" in s

    def test_fade_fractional_duration(self) -> None:
        """Test fade with fractional duration."""
        from stoat_ferret_core import FadeBuilder

        f = FadeBuilder("in", 0.5).build()
        assert str(f) == "fade=t=in:d=0.5"

    def test_fade_invalid_type(self) -> None:
        """Test FadeBuilder rejects invalid fade type."""
        from stoat_ferret_core import FadeBuilder

        with pytest.raises(ValueError, match="'in' or 'out'"):
            FadeBuilder("up", 1.0)

    def test_fade_zero_duration(self) -> None:
        """Test FadeBuilder rejects zero duration."""
        from stoat_ferret_core import FadeBuilder

        with pytest.raises(ValueError, match="> 0"):
            FadeBuilder("in", 0.0)

    def test_fade_negative_duration(self) -> None:
        """Test FadeBuilder rejects negative duration."""
        from stoat_ferret_core import FadeBuilder

        with pytest.raises(ValueError):
            FadeBuilder("in", -1.0)

    def test_fade_method_chaining(self) -> None:
        """Test full method chaining returns correct filter."""
        from stoat_ferret_core import FadeBuilder

        f = FadeBuilder("in", 2.0).start_time(1.0).color("black").alpha(False).build()
        s = str(f)
        assert "fade=" in s
        assert "t=in" in s
        assert "d=2" in s
        assert "st=1" in s
        assert "c=black" in s

    def test_build_returns_filter(self) -> None:
        """Test build() returns a Filter object."""
        from stoat_ferret_core import FadeBuilder, Filter

        f = FadeBuilder("in", 1.0).build()
        assert isinstance(f, Filter)

    def test_repr(self) -> None:
        """Test repr output."""
        from stoat_ferret_core import FadeBuilder

        b = FadeBuilder("in", 2.0)
        r = repr(b)
        assert "FadeBuilder" in r
        assert "in" in r

    def test_in_filter_chain(self) -> None:
        """Test FadeBuilder output works in a FilterChain."""
        from stoat_ferret_core import FadeBuilder, FilterChain

        f = FadeBuilder("in", 1.0).build()
        chain = FilterChain().input("0:v").filter(f).output("out")
        s = str(chain)
        assert "[0:v]" in s
        assert "fade=" in s
        assert "[out]" in s


class TestXfadeBuilder:
    """Tests for XfadeBuilder PyO3 bindings."""

    def test_xfade_basic(self) -> None:
        """Test building a basic xfade filter."""
        from stoat_ferret_core import TransitionType, XfadeBuilder

        f = XfadeBuilder(TransitionType.Wipeleft, 2.0, 5.0).build()
        assert str(f) == "xfade=transition=wipeleft:duration=2:offset=5"

    def test_xfade_dissolve(self) -> None:
        """Test xfade with dissolve transition."""
        from stoat_ferret_core import TransitionType, XfadeBuilder

        f = XfadeBuilder(TransitionType.Dissolve, 1.5, 3.0).build()
        assert str(f) == "xfade=transition=dissolve:duration=1.5:offset=3"

    def test_xfade_various_transitions(self) -> None:
        """Test xfade with several different transition types."""
        from stoat_ferret_core import TransitionType, XfadeBuilder

        types = [
            TransitionType.Fade,
            TransitionType.Fadeblack,
            TransitionType.Circlecrop,
            TransitionType.Zoomin,
            TransitionType.Custom,
        ]
        for tt in types:
            f = XfadeBuilder(tt, 1.0, 0.0).build()
            s = str(f)
            assert f"transition={tt.as_str()}" in s

    def test_xfade_duration_min(self) -> None:
        """Test xfade at minimum duration (0.0)."""
        from stoat_ferret_core import TransitionType, XfadeBuilder

        f = XfadeBuilder(TransitionType.Fade, 0.0, 0.0).build()
        assert "duration=0" in str(f)

    def test_xfade_duration_max(self) -> None:
        """Test xfade at maximum duration (60.0)."""
        from stoat_ferret_core import TransitionType, XfadeBuilder

        f = XfadeBuilder(TransitionType.Fade, 60.0, 0.0).build()
        assert "duration=60" in str(f)

    def test_xfade_duration_below_range(self) -> None:
        """Test xfade rejects duration below 0."""
        from stoat_ferret_core import TransitionType, XfadeBuilder

        with pytest.raises(ValueError, match="0.0-60.0"):
            XfadeBuilder(TransitionType.Fade, -0.1, 0.0)

    def test_xfade_duration_above_range(self) -> None:
        """Test xfade rejects duration above 60."""
        from stoat_ferret_core import TransitionType, XfadeBuilder

        with pytest.raises(ValueError, match="0.0-60.0"):
            XfadeBuilder(TransitionType.Fade, 60.1, 0.0)

    def test_build_returns_filter(self) -> None:
        """Test build() returns a Filter object."""
        from stoat_ferret_core import Filter, TransitionType, XfadeBuilder

        f = XfadeBuilder(TransitionType.Dissolve, 1.0, 0.0).build()
        assert isinstance(f, Filter)

    def test_repr(self) -> None:
        """Test repr output."""
        from stoat_ferret_core import TransitionType, XfadeBuilder

        b = XfadeBuilder(TransitionType.Wipeleft, 2.0, 5.0)
        r = repr(b)
        assert "XfadeBuilder" in r
        assert "wipeleft" in r

    def test_in_filter_chain(self) -> None:
        """Test XfadeBuilder output works in a FilterChain/FilterGraph."""
        from stoat_ferret_core import FilterChain, FilterGraph, TransitionType, XfadeBuilder

        xfade = XfadeBuilder(TransitionType.Wipeleft, 2.0, 5.0).build()
        graph = FilterGraph().chain(
            FilterChain().input("0:v").input("1:v").filter(xfade).output("out")
        )
        s = str(graph)
        assert "[0:v][1:v]" in s
        assert "xfade=" in s
        assert "[out]" in s


class TestAcrossfadeBuilder:
    """Tests for AcrossfadeBuilder PyO3 bindings."""

    def test_acrossfade_basic(self) -> None:
        """Test building a basic acrossfade filter."""
        from stoat_ferret_core import AcrossfadeBuilder

        f = AcrossfadeBuilder(2.0).build()
        assert str(f) == "acrossfade=d=2"

    def test_acrossfade_with_curves(self) -> None:
        """Test acrossfade with curve1 and curve2."""
        from stoat_ferret_core import AcrossfadeBuilder

        f = AcrossfadeBuilder(1.5).curve1("qsin").curve2("log").build()
        assert str(f) == "acrossfade=d=1.5:c1=qsin:c2=log"

    def test_acrossfade_overlap_disabled(self) -> None:
        """Test acrossfade with overlap disabled."""
        from stoat_ferret_core import AcrossfadeBuilder

        f = AcrossfadeBuilder(2.0).overlap(False).build()
        assert str(f) == "acrossfade=d=2:o=0"

    def test_acrossfade_overlap_enabled(self) -> None:
        """Test acrossfade with overlap explicitly enabled."""
        from stoat_ferret_core import AcrossfadeBuilder

        f = AcrossfadeBuilder(2.0).overlap(True).build()
        assert str(f) == "acrossfade=d=2:o=1"

    def test_acrossfade_all_options(self) -> None:
        """Test acrossfade with all options set."""
        from stoat_ferret_core import AcrossfadeBuilder

        f = AcrossfadeBuilder(3.0).curve1("hsin").curve2("esin").overlap(False).build()
        s = str(f)
        assert "d=3" in s
        assert "c1=hsin" in s
        assert "c2=esin" in s
        assert "o=0" in s

    def test_acrossfade_zero_duration(self) -> None:
        """Test AcrossfadeBuilder rejects zero duration."""
        from stoat_ferret_core import AcrossfadeBuilder

        with pytest.raises(ValueError):
            AcrossfadeBuilder(0.0)

    def test_acrossfade_negative_duration(self) -> None:
        """Test AcrossfadeBuilder rejects negative duration."""
        from stoat_ferret_core import AcrossfadeBuilder

        with pytest.raises(ValueError):
            AcrossfadeBuilder(-1.0)

    def test_acrossfade_above_max_duration(self) -> None:
        """Test AcrossfadeBuilder rejects duration > 60."""
        from stoat_ferret_core import AcrossfadeBuilder

        with pytest.raises(ValueError):
            AcrossfadeBuilder(61.0)

    def test_acrossfade_invalid_curve(self) -> None:
        """Test AcrossfadeBuilder rejects invalid curve name."""
        from stoat_ferret_core import AcrossfadeBuilder

        with pytest.raises(ValueError):
            AcrossfadeBuilder(2.0).curve1("invalid_curve")

    def test_build_returns_filter(self) -> None:
        """Test build() returns a Filter object."""
        from stoat_ferret_core import AcrossfadeBuilder, Filter

        f = AcrossfadeBuilder(2.0).build()
        assert isinstance(f, Filter)

    def test_repr(self) -> None:
        """Test repr output."""
        from stoat_ferret_core import AcrossfadeBuilder

        b = AcrossfadeBuilder(2.0)
        r = repr(b)
        assert "AcrossfadeBuilder" in r

    def test_in_filter_chain(self) -> None:
        """Test AcrossfadeBuilder output works in a FilterChain/FilterGraph."""
        from stoat_ferret_core import AcrossfadeBuilder, FilterChain, FilterGraph

        acf = AcrossfadeBuilder(2.0).build()
        graph = FilterGraph().chain(
            FilterChain().input("0:a").input("1:a").filter(acf).output("aout")
        )
        s = str(graph)
        assert "[0:a][1:a]" in s
        assert "acrossfade=" in s
        assert "[aout]" in s

    def test_method_chaining(self) -> None:
        """Test full method chaining works."""
        from stoat_ferret_core import AcrossfadeBuilder

        f = AcrossfadeBuilder(1.0).curve1("tri").curve2("tri").overlap(True).build()
        s = str(f)
        assert "acrossfade=" in s
        assert "c1=tri" in s
        assert "c2=tri" in s
        assert "o=1" in s

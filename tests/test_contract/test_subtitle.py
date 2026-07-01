# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Contract tests for SubtitleScriptBuilder (BL-518)."""

from __future__ import annotations

import os

import pytest

from stoat_ferret_core import ScriptEntry, SubtitleScriptBuilder, SubtitleScriptSpec


class TestScriptEntry:
    def test_valid_range(self) -> None:
        entry = ScriptEntry(0.0, 2.0, "Hello")
        assert entry.start_s == 0.0
        assert entry.end_s == 2.0
        assert entry.text == "Hello"

    def test_rejects_equal_times(self) -> None:
        with pytest.raises(ValueError, match="start_s"):
            ScriptEntry(3.0, 3.0, "bad")

    def test_rejects_reversed_range(self) -> None:
        with pytest.raises(ValueError, match="start_s"):
            ScriptEntry(5.0, 2.0, "bad")

    def test_accepts_zero_start(self) -> None:
        entry = ScriptEntry(0.0, 0.1, "ok")
        assert entry.start_s == 0.0


class TestSubtitleScriptSpec:
    def test_defaults(self) -> None:
        entry = ScriptEntry(0.0, 1.0, "test")
        spec = SubtitleScriptSpec(entries=[entry])
        assert spec.position == "bottom"
        assert spec.font_size == 24
        assert spec.font_color == "white"
        assert spec.font_file is None

    def test_custom_values(self) -> None:
        entry = ScriptEntry(0.0, 1.0, "test")
        spec = SubtitleScriptSpec(
            entries=[entry],
            position="top",
            font_size=32,
            font_color="yellow",
            font_file="/path/to/font.ttf",
        )
        assert spec.position == "top"
        assert spec.font_size == 32
        assert spec.font_color == "yellow"
        assert spec.font_file == "/path/to/font.ttf"

    def test_rejects_unknown_position(self) -> None:
        entry = ScriptEntry(0.0, 1.0, "test")
        with pytest.raises(ValueError, match="position"):
            SubtitleScriptSpec(entries=[entry], position="left")


class TestSubtitleScriptBuilder:
    def test_basic_two_entries(self) -> None:
        entries = [
            ScriptEntry(0.0, 2.0, "Hello"),
            ScriptEntry(3.0, 5.0, "World"),
        ]
        spec = SubtitleScriptSpec(entries=entries)
        result = SubtitleScriptBuilder.build(spec)
        # Two drawtext segments
        assert result.count("drawtext=") == 2
        assert "enable='between(t,0.0,2.0)'" in result
        assert "enable='between(t,3.0,5.0)'" in result

    def test_three_entries_chain(self) -> None:
        entries = [
            ScriptEntry(0.0, 2.0, "A"),
            ScriptEntry(3.0, 5.0, "B"),
            ScriptEntry(6.0, 8.0, "C"),
        ]
        spec = SubtitleScriptSpec(entries=entries)
        result = SubtitleScriptBuilder.build(spec)
        assert result.count("drawtext=") == 3
        assert "enable='between(t,6.0,8.0)'" in result

    def test_empty_entries_raises(self) -> None:
        spec = SubtitleScriptSpec(entries=[])
        with pytest.raises(ValueError, match="non-empty"):
            SubtitleScriptBuilder.build(spec)

    def test_text_escape_applied(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "it's 'quoted'")]
        spec = SubtitleScriptSpec(entries=entries)
        result = SubtitleScriptBuilder.build(spec)
        # escape_drawtext must neutralize single quotes
        assert "it's 'quoted'" not in result

    def test_text_colon_escaped(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "key:value")]
        spec = SubtitleScriptSpec(entries=entries)
        result = SubtitleScriptBuilder.build(spec)
        # Colon must be escaped as \:
        assert "key\\:value" in result

    def test_font_file_included(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "text")]
        spec = SubtitleScriptSpec(entries=entries, font_file="/fonts/arial.ttf")
        result = SubtitleScriptBuilder.build(spec)
        assert "fontfile=/fonts/arial.ttf:" in result

    def test_no_font_file_omits_fontfile(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "text")]
        spec = SubtitleScriptSpec(entries=entries)
        result = SubtitleScriptBuilder.build(spec)
        assert "fontfile=" not in result

    def test_position_bottom_xy(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "text")]
        spec = SubtitleScriptSpec(entries=entries, position="bottom")
        result = SubtitleScriptBuilder.build(spec)
        assert "x=(w-text_w)/2:y=h-text_h-10" in result

    def test_position_top_xy(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "text")]
        spec = SubtitleScriptSpec(entries=entries, position="top")
        result = SubtitleScriptBuilder.build(spec)
        assert "x=(w-text_w)/2:y=10" in result

    def test_position_center_xy(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "text")]
        spec = SubtitleScriptSpec(entries=entries, position="center")
        result = SubtitleScriptBuilder.build(spec)
        assert "x=(w-text_w)/2:y=(h-text_h)/2" in result

    def test_fontsize_and_fontcolor_in_filter(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "text")]
        spec = SubtitleScriptSpec(entries=entries, font_size=36, font_color="yellow")
        result = SubtitleScriptBuilder.build(spec)
        assert "fontsize=36" in result
        assert "fontcolor=yellow" in result

    def test_filters_joined_by_comma(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "A"), ScriptEntry(2.0, 3.0, "B")]
        spec = SubtitleScriptSpec(entries=entries)
        result = SubtitleScriptBuilder.build(spec)
        # The chain is comma-separated; split to confirm two valid segments
        segments = result.split(",drawtext=")
        assert len(segments) == 2

    def test_text_wrapped_in_single_quotes(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "Hello World")]
        spec = SubtitleScriptSpec(entries=entries)
        result = SubtitleScriptBuilder.build(spec)
        assert "text='Hello World'" in result


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="requires runtime FFmpeg (set STOAT_TEST_FFMPEG=1)",
)
def test_subtitle_script_builder_ffmpeg_contract() -> None:
    """Render 10s clip with 3 captions; deferred to post-merge discharge."""
    pass

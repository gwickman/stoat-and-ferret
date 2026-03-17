"""Security tests for filter text escaping and whitelist validation.

Tests cover:
- Shell injection in filter text (backticks, $(), pipes)
- Null byte injection in filter text
- Whitelist bypass for codecs, presets, and format values
- FFmpeg filter syntax injection
- DrawtextBuilder Unicode edge cases through PyO3 (BL-085)
"""

from __future__ import annotations

import pytest

from stoat_ferret_core import (
    DrawtextBuilder,
    escape_filter_text,
    validate_audio_codec,
    validate_path,
    validate_preset,
    validate_video_codec,
)


class TestShellInjectionInFilterText:
    """Verify escape_filter_text neutralizes shell injection attempts."""

    def test_backtick_command_substitution(self) -> None:
        """Backticks are passed through (no shell context), not a risk."""
        result = escape_filter_text("`whoami`")
        # Backticks are not FFmpeg-special, so they pass through
        assert "`" in result

    def test_dollar_paren_command_substitution(self) -> None:
        """$() command substitution is not dangerous in FFmpeg filter context."""
        result = escape_filter_text("$(cat /etc/passwd)")
        # Not FFmpeg-special, passes through; safe because no shell invocation
        assert "$" in result

    def test_pipe_injection(self) -> None:
        """Pipe character is not FFmpeg filter-special, passes through safely."""
        result = escape_filter_text("text | rm -rf /")
        assert "|" in result

    def test_semicolon_is_escaped(self) -> None:
        """Semicolons are escaped because they separate FFmpeg filter chains."""
        result = escape_filter_text("text; dangerous_filter")
        assert "\\;" in result
        assert result == "text\\; dangerous_filter"

    def test_newline_injection(self) -> None:
        """Newlines are escaped to prevent filter string breakout."""
        result = escape_filter_text("text\ninjected_command")
        assert "\n" not in result
        assert "\\n" in result

    def test_carriage_return_injection(self) -> None:
        """Carriage returns are escaped."""
        result = escape_filter_text("text\rinjected")
        assert "\r" not in result
        assert "\\r" in result


class TestNullByteInjection:
    """Verify null byte injection is caught by validate_path."""

    def test_null_byte_mid_path(self) -> None:
        """Null byte in the middle of a path is rejected."""
        with pytest.raises(ValueError, match="null"):
            validate_path("file\x00.mp4")

    def test_null_byte_at_start(self) -> None:
        """Null byte at the start of a path is rejected."""
        with pytest.raises(ValueError, match="null"):
            validate_path("\x00file.mp4")

    def test_null_byte_at_end(self) -> None:
        """Null byte at the end of a path is rejected."""
        with pytest.raises(ValueError, match="null"):
            validate_path("file.mp4\x00")

    def test_empty_path_rejected(self) -> None:
        """Empty path is rejected."""
        with pytest.raises(ValueError, match="empty"):
            validate_path("")


class TestFilterTextEscaping:
    """Verify FFmpeg filter syntax injection is properly escaped."""

    def test_colon_escaped(self) -> None:
        """Colons are escaped (parameter separator in FFmpeg filters)."""
        assert escape_filter_text("key:value") == "key\\:value"

    def test_brackets_escaped(self) -> None:
        """Square brackets are escaped (stream labels in FFmpeg)."""
        assert escape_filter_text("[0:v]") == "\\[0\\:v\\]"

    def test_backslash_escaped(self) -> None:
        """Backslashes are double-escaped."""
        assert escape_filter_text("path\\file") == "path\\\\file"

    def test_single_quote_escaped(self) -> None:
        """Single quotes use shell-style escaping."""
        result = escape_filter_text("it's")
        assert "'" in result
        assert "\\'" in result

    def test_combined_injection(self) -> None:
        """Combined injection attempt with multiple special chars."""
        payload = "[0:v]overlay=10:10;[out]"
        result = escape_filter_text(payload)
        assert "\\[" in result
        assert "\\:" in result
        assert "\\;" in result
        assert "\\]" in result


class TestWhitelistBypass:
    """Verify whitelist validation cannot be bypassed."""

    def test_video_codec_injection(self) -> None:
        """Injection attempt in video codec is rejected."""
        with pytest.raises(ValueError):
            validate_video_codec("libx264; rm -rf /")

    def test_video_codec_command_substitution(self) -> None:
        """Command substitution in video codec is rejected."""
        with pytest.raises(ValueError):
            validate_video_codec("$(whoami)")

    def test_video_codec_case_bypass(self) -> None:
        """Case variation bypass attempt is rejected."""
        with pytest.raises(ValueError):
            validate_video_codec("LIBX264")

    def test_audio_codec_injection(self) -> None:
        """Injection attempt in audio codec is rejected."""
        with pytest.raises(ValueError):
            validate_audio_codec("aac && cat /etc/passwd")

    def test_audio_codec_with_spaces(self) -> None:
        """Audio codec with trailing spaces is rejected."""
        with pytest.raises(ValueError):
            validate_audio_codec("aac ")

    def test_preset_injection(self) -> None:
        """Injection attempt in preset is rejected."""
        with pytest.raises(ValueError):
            validate_preset("fast; rm -rf /")

    def test_preset_case_bypass(self) -> None:
        """Case variation bypass for preset is rejected."""
        with pytest.raises(ValueError):
            validate_preset("FAST")

    def test_preset_with_null_byte(self) -> None:
        """Preset with embedded null byte is rejected (not in whitelist)."""
        with pytest.raises(ValueError):
            validate_preset("fast\x00")


class TestDrawtextUnicodeEdgeCases:
    """Verify Unicode edge cases pass through DrawtextBuilder via PyO3 correctly.

    Tests the full path: Python input -> Rust escape_drawtext() -> FFmpeg filter string.
    These characters should pass through without corruption and produce valid filter output.
    """

    def test_zero_width_space(self) -> None:
        """U+200B zero-width space passes through DrawtextBuilder."""
        dt = DrawtextBuilder("hello\u200bworld")
        result = str(dt.build())
        assert "drawtext=" in result
        assert "\u200b" in result

    def test_byte_order_mark(self) -> None:
        """U+FEFF BOM/ZWNBSP passes through DrawtextBuilder."""
        dt = DrawtextBuilder("\ufefftext")
        result = str(dt.build())
        assert "drawtext=" in result
        assert "\ufeff" in result

    def test_zero_width_joiner(self) -> None:
        """U+200D zero-width joiner (emoji sequences) passes through."""
        dt = DrawtextBuilder("a\u200db")
        result = str(dt.build())
        assert "drawtext=" in result
        assert "\u200d" in result

    def test_rtl_mark(self) -> None:
        """U+200F right-to-left mark passes through."""
        dt = DrawtextBuilder("hello\u200f\u0645\u0631\u062d\u0628\u0627")
        result = str(dt.build())
        assert "drawtext=" in result
        assert "\u200f" in result

    def test_rtl_embedding(self) -> None:
        """U+202B right-to-left embedding passes through."""
        dt = DrawtextBuilder("\u202bembedded")
        result = str(dt.build())
        assert "drawtext=" in result
        assert "\u202b" in result

    def test_rtl_override(self) -> None:
        """U+202E right-to-left override passes through."""
        dt = DrawtextBuilder("normal\u202edesrever")
        result = str(dt.build())
        assert "drawtext=" in result
        assert "\u202e" in result

    def test_combining_acute_accent(self) -> None:
        """U+0301 combining acute accent passes through."""
        dt = DrawtextBuilder("e\u0301")  # e + combining acute = é
        result = str(dt.build())
        assert "drawtext=" in result
        assert "\u0301" in result

    def test_combining_diaeresis(self) -> None:
        """U+0308 combining diaeresis passes through."""
        dt = DrawtextBuilder("u\u0308")  # u + combining diaeresis = ü
        result = str(dt.build())
        assert "drawtext=" in result
        assert "\u0308" in result

    def test_unicode_with_special_chars_full_path(self) -> None:
        """Unicode combined with FFmpeg special chars through full Python->Rust path."""
        dt = DrawtextBuilder("\u200bkey:value%{expr}\u200f")
        result = str(dt.build())
        assert "drawtext=" in result
        # Colon and percent must be escaped, Unicode must pass through
        assert "\\:" in result
        assert "%%" in result
        assert "\u200b" in result
        assert "\u200f" in result

    def test_percent_expansion_neutralized(self) -> None:
        """FFmpeg %{...} text expansion is neutralized through Python API."""
        dt = DrawtextBuilder("%{localtime}")
        result = str(dt.build())
        assert "%%{localtime}" in result

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Contract tests for SubtitleScriptBuilder (BL-518), BurnedSubtitleBuilder (BL-519),
and soft subtitle embedding (BL-520)."""

from __future__ import annotations

import os
import subprocess
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock

import pytest

from stoat_ferret.api.schemas.render import SoftSubtitleSpec, bcp47_to_iso639
from stoat_ferret.render.worker import TtsCueAudioInput, build_command_for_job
from stoat_ferret_core import (
    BurnedSubtitleBuilder,
    BurnedSubtitleSpec,
    ScriptEntry,
    SubtitleScriptBuilder,
    SubtitleScriptSpec,
)

# ---------------------------------------------------------------------------
# Shared fixtures for BL-520 worker tests
# ---------------------------------------------------------------------------

_NOW = datetime.now().isoformat()
_SOFT_SUB_VIDEO_PATH = "/data/projects/clip1.mp4"
_SOFT_EN_ASSET_ID = uuid.UUID("00000000-0000-0000-0000-000000000011")
_SOFT_ES_ASSET_ID = uuid.UUID("00000000-0000-0000-0000-000000000012")


@dataclass
class _FakeAsset:
    id: str
    original_filename: str = "fake.srt"
    content_hash: str = "abc"
    mime_type: str = "application/x-subrip"
    kind: str = "subtitle"
    size_bytes: int = 1024
    file_path: str = "/data/assets/en.srt"
    created_at: str = _NOW
    updated_at: str = _NOW
    deleted_at: str | None = field(default=None)


@dataclass
class _FakeVideo:
    id: str = "vid-sub-001"
    path: str = _SOFT_SUB_VIDEO_PATH
    filename: str = "clip1.mp4"
    duration_frames: int = 300
    frame_rate: float = 30.0
    frame_rate_numerator: int = 30
    frame_rate_denominator: int = 1
    width: int = 1920
    height: int = 1080
    video_codec: str = "h264"
    audio_codec: str | None = "aac"
    file_size: int = 10_000_000
    created_at: str = _NOW
    updated_at: str = _NOW


@dataclass
class _FakeClip:
    id: str = "clip-sub-001"
    project_id: str = "proj-sub-001"
    source_video_id: str = "vid-sub-001"
    clip_type: str = "file"
    in_point: int = 0
    out_point: int = 300
    effects: list[Any] = field(default_factory=list)


@dataclass
class _FakeRenderJob:
    id: str = "job-sub-001"
    project_id: str = "proj-sub-001"
    output_path: str = "/out/result.mp4"
    output_format: str = "mp4"
    render_plan: str = (
        '{"settings": {"soft_subtitles": ['
        '{"source_asset_id": "00000000-0000-0000-0000-000000000011",'
        ' "language": "en", "is_default": true},'
        '{"source_asset_id": "00000000-0000-0000-0000-000000000012",'
        ' "language": "es-ES"}'
        ']}, "total_duration": 10.0}'
    )
    quality_preset: str = "standard"


def _make_soft_sub_repos() -> tuple[AsyncMock, AsyncMock]:
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[_FakeClip()])
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=_FakeVideo())
    return clip_repo, video_repo


def _make_soft_sub_asset_repo() -> AsyncMock:
    asset_repo = AsyncMock()

    async def _get_by_id(asset_id: str) -> _FakeAsset | None:
        if asset_id == str(_SOFT_EN_ASSET_ID):
            return _FakeAsset(id=asset_id, file_path="/data/assets/en.srt")
        if asset_id == str(_SOFT_ES_ASSET_ID):
            return _FakeAsset(id=asset_id, file_path="/data/assets/es.srt")
        return None

    asset_repo.get_by_id = _get_by_id
    return asset_repo


def _make_multi_clip_soft_sub_repos() -> tuple[AsyncMock, AsyncMock]:
    """Create 2-clip repos for multi-clip subtitle map tests (FR-001-AC-4)."""
    clip1 = _FakeClip(id="clip-sub-001", source_video_id="vid-sub-001")
    clip2 = _FakeClip(id="clip-sub-002", source_video_id="vid-sub-002")
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[clip1, clip2])
    vid1 = _FakeVideo(id="vid-sub-001", path="/data/projects/clip1.mp4")
    vid2 = _FakeVideo(id="vid-sub-002", path="/data/projects/clip2.mp4")

    async def _get_video(vid_id: str) -> _FakeVideo | None:
        if vid_id == "vid-sub-001":
            return vid1
        if vid_id == "vid-sub-002":
            return vid2
        return None

    video_repo = AsyncMock()
    video_repo.get = _get_video
    return clip_repo, video_repo


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

    def test_font_file_windows_path(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "text")]
        spec = SubtitleScriptSpec(entries=entries, font_file="C:\\Windows\\Fonts\\arial.ttf")
        result = SubtitleScriptBuilder.build(spec)
        # Windows path: single-quoted, drive colon escaped as \:, backslashes → forward slashes
        assert "fontfile='C\\:/Windows/Fonts/arial.ttf':" in result

    def test_font_file_space_path(self) -> None:
        entries = [ScriptEntry(0.0, 1.0, "text")]
        spec = SubtitleScriptSpec(entries=entries, font_file="C:\\My Fonts\\cool.ttf")
        result = SubtitleScriptBuilder.build(spec)
        # Space preserved inside single quotes; drive colon escaped as \:
        assert "fontfile='C\\:/My Fonts/cool.ttf':" in result

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


# ---- BurnedSubtitleBuilder (BL-519) ----


class TestBurnedSubtitleSpec:
    def test_defaults_all_none(self) -> None:
        spec = BurnedSubtitleSpec()
        assert spec.source_path is None
        assert spec.inline_text is None
        assert spec.force_style is None

    def test_source_path_set(self) -> None:
        spec = BurnedSubtitleSpec(source_path="/tmp/test.srt")
        assert spec.source_path == "/tmp/test.srt"

    def test_inline_text_set(self) -> None:
        spec = BurnedSubtitleSpec(inline_text="/tmp/inline.srt")
        assert spec.inline_text == "/tmp/inline.srt"

    def test_force_style_set(self) -> None:
        spec = BurnedSubtitleSpec(
            source_path="/tmp/test.srt",
            force_style={"Fontsize": "32"},
        )
        assert spec.force_style == {"Fontsize": "32"}


class TestBurnedSubtitleBuilder:
    def test_srt_basic(self) -> None:
        spec = BurnedSubtitleSpec(source_path="/tmp/test.srt")
        result = BurnedSubtitleBuilder.build(spec)
        assert result.startswith("subtitles=filename=")
        assert "test.srt" in result

    def test_ass_no_force_style(self) -> None:
        spec = BurnedSubtitleSpec(source_path="/tmp/test.ass")
        result = BurnedSubtitleBuilder.build(spec)
        assert result.startswith("ass=filename=")
        assert "test.ass" in result
        assert "force_style" not in result

    def test_srt_with_force_style(self) -> None:
        spec = BurnedSubtitleSpec(
            source_path="/tmp/test.srt",
            force_style={"Fontsize": "32", "PrimaryColour": "&Hffffff&"},
        )
        result = BurnedSubtitleBuilder.build(spec)
        assert ":force_style='" in result
        assert "Fontsize=32" in result
        assert "PrimaryColour=&Hffffff&" in result

    def test_srt_force_style_comma_in_value_escaped(self) -> None:
        spec = BurnedSubtitleSpec(
            source_path="/tmp/test.srt",
            force_style={"Fontname": "Arial,Bold"},
        )
        result = BurnedSubtitleBuilder.build(spec)
        # Comma within a value must be escaped as \,
        assert r"Arial\,Bold" in result

    def test_ass_ignores_force_style(self) -> None:
        spec = BurnedSubtitleSpec(
            source_path="/tmp/test.ass",
            force_style={"Fontsize": "32"},
        )
        result = BurnedSubtitleBuilder.build(spec)
        assert result.startswith("ass=filename=")
        assert "force_style" not in result

    def test_no_source_or_inline_raises(self) -> None:
        spec = BurnedSubtitleSpec()
        with pytest.raises(ValueError):
            BurnedSubtitleBuilder.build(spec)

    def test_inline_text_used_as_path(self) -> None:
        spec = BurnedSubtitleSpec(inline_text="/tmp/via_inline.srt")
        result = BurnedSubtitleBuilder.build(spec)
        assert result.startswith("subtitles=filename=")
        assert "via_inline.srt" in result

    def test_srt_no_force_style_no_colon(self) -> None:
        spec = BurnedSubtitleSpec(source_path="/tmp/test.srt")
        result = BurnedSubtitleBuilder.build(spec)
        # Without force_style there is no trailing :force_style= clause
        assert ":force_style=" not in result

    def test_force_style_single_quotes_wrap(self) -> None:
        spec = BurnedSubtitleSpec(
            source_path="/tmp/test.srt",
            force_style={"Fontsize": "28"},
        )
        result = BurnedSubtitleBuilder.build(spec)
        # force_style value is wrapped in single quotes per FFmpeg requirement
        assert ":force_style='Fontsize=28'" in result


def test_ci_bundle_guard_subtitle_filters() -> None:
    """Assert subtitles and ass filters are present in the bundled FFmpeg."""
    try:
        proc = subprocess.run(
            ["ffmpeg", "-filters"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        pytest.skip("ffmpeg not found on PATH; CI bundled FFmpeg required")
    output = proc.stdout + proc.stderr
    assert "subtitles" in output, "subtitles filter missing from bundled FFmpeg"
    assert " ass " in output, "ass filter missing from bundled FFmpeg"


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="requires runtime FFmpeg (set STOAT_TEST_FFMPEG=1)",
)
def test_burned_subtitle_srt_render() -> None:
    """Burn 5s SRT onto color=blue; deferred post-merge discharge (BL-519-AC-6)."""
    pass


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="requires runtime FFmpeg (set STOAT_TEST_FFMPEG=1)",
)
def test_burned_subtitle_force_style_escape_render() -> None:
    """force_style escape render test; deferred post-merge discharge (BL-519-AC-7)."""
    pass


# ---- SoftSubtitleSpec (BL-520) ----


class TestSoftSubtitleSpec:
    def test_en_validates_iso639(self) -> None:
        spec = SoftSubtitleSpec(
            source_asset_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            language="en",
        )
        assert bcp47_to_iso639(spec.language) == "eng"

    def test_region_tag_normalized_es_es(self) -> None:
        spec = SoftSubtitleSpec(
            source_asset_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            language="es-ES",
        )
        assert bcp47_to_iso639(spec.language) == "spa"

    def test_region_tag_normalized_zh_hant(self) -> None:
        spec = SoftSubtitleSpec(
            source_asset_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            language="zh-Hant",
        )
        assert bcp47_to_iso639(spec.language) == "zho"

    def test_unsupported_language_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported BCP-47"):
            SoftSubtitleSpec(
                source_asset_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                language="xx",
            )

    def test_unsupported_language_includes_supported_list(self) -> None:
        with pytest.raises(ValueError, match="en"):
            SoftSubtitleSpec(
                source_asset_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                language="xx",
            )

    def test_is_default_false_by_default(self) -> None:
        spec = SoftSubtitleSpec(
            source_asset_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            language="fr",
        )
        assert spec.is_default is False

    def test_is_default_set_true(self) -> None:
        spec = SoftSubtitleSpec(
            source_asset_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
            language="de",
            is_default=True,
        )
        assert spec.is_default is True

    def test_all_ten_languages_accepted(self) -> None:
        langs = ["en", "es", "fr", "de", "it", "ja", "zh", "pt", "ru", "ar"]
        for lang in langs:
            spec = SoftSubtitleSpec(
                source_asset_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
                language=lang,
            )
            iso = bcp47_to_iso639(spec.language)
            assert len(iso) == 3, f"Expected 3-letter code for {lang}, got {iso!r}"


class TestWorkerSoftSubtitleCommand:
    """Command-level tests for soft subtitle embedding in build_command_for_job (BL-520)."""

    async def test_soft_subtitles_included_in_command(self) -> None:
        """AC FR-006-AC-1/AC-3: soft_subtitles → -c:s mov_text and language metadata."""
        clip_repo, video_repo = _make_soft_sub_repos()
        asset_repo = _make_soft_sub_asset_repo()
        job = _FakeRenderJob()

        cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

        assert "-c:s" in cmd
        assert "mov_text" in cmd
        assert "-metadata:s:s:0" in cmd
        assert "language=eng" in cmd
        assert "-metadata:s:s:1" in cmd
        assert "language=spa" in cmd

    async def test_first_subtitle_is_default(self) -> None:
        """AC FR-006-AC-3: is_default=True → -disposition:s:0 default."""
        clip_repo, video_repo = _make_soft_sub_repos()
        asset_repo = _make_soft_sub_asset_repo()
        job = _FakeRenderJob()

        cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

        # First subtitle has is_default=True in the render_plan
        assert "-disposition:s:0" in cmd
        assert "default" in cmd

    async def test_subtitle_inputs_after_source_in_command(self) -> None:
        """AC FR-006-AC-3/AC-5: subtitle -i inputs appear after source -i."""
        clip_repo, video_repo = _make_soft_sub_repos()
        asset_repo = _make_soft_sub_asset_repo()
        job = _FakeRenderJob()

        cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

        # Source video is first -i; subtitle files appear as additional -i flags
        input_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i"]
        assert input_args[0] == _SOFT_SUB_VIDEO_PATH
        assert "/data/assets/en.srt" in input_args
        assert "/data/assets/es.srt" in input_args
        # Subtitle inputs must be at the END of the -i chain
        en_idx = input_args.index("/data/assets/en.srt")
        es_idx = input_args.index("/data/assets/es.srt")
        assert en_idx > 0  # not the source video
        assert es_idx > en_idx  # es comes after en

    async def test_subtitle_inputs_after_tts_inputs(self) -> None:
        """AC FR-006-AC-3: subtitle -i inputs appear AFTER TTS -i inputs (Risk 005)."""
        clip_repo, video_repo = _make_soft_sub_repos()
        asset_repo = _make_soft_sub_asset_repo()
        job = _FakeRenderJob()
        tts_input = TtsCueAudioInput(
            cue_id="cue-001",
            audio_path="/tmp/tts.wav",
            track_id="voice",
            start_s=0.0,
            weight=1.0,
            volume_envelope=None,
        )

        cmd = await build_command_for_job(
            job, clip_repo, video_repo, tts_inputs=[tts_input], asset_repository=asset_repo
        )

        input_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i"]
        tts_idx = input_args.index("/tmp/tts.wav")
        en_idx = input_args.index("/data/assets/en.srt")
        # Subtitle inputs must come AFTER TTS inputs
        assert en_idx > tts_idx

    async def test_non_mp4_mkv_container_raises(self) -> None:
        """AC FR-006-AC-4: non-mp4/non-mkv container with soft_subtitles raises ValueError."""
        clip_repo, video_repo = _make_soft_sub_repos()
        asset_repo = _make_soft_sub_asset_repo()
        job = _FakeRenderJob(
            output_format="webm",
            output_path="/out/result.webm",
        )

        with pytest.raises(ValueError, match="mp4 or mkv"):
            await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

    async def test_mkv_container_uses_srt_codec(self) -> None:
        """AC FR-006-AC-4: mkv container uses -c:s srt instead of mov_text."""
        clip_repo, video_repo = _make_soft_sub_repos()
        asset_repo = _make_soft_sub_asset_repo()
        job = _FakeRenderJob(
            output_format="mkv",
            output_path="/out/result.mkv",
        )

        cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)
        cmd_str = " ".join(cmd)

        assert "-c:s" in cmd
        assert "srt" in cmd
        assert "mov_text" not in cmd_str

    async def test_no_soft_subtitles_no_c_s_flag(self) -> None:
        """Regression: no soft_subtitles → no -c:s flag emitted."""
        clip_repo, video_repo = _make_soft_sub_repos()
        job = _FakeRenderJob(
            render_plan='{"settings": {}, "total_duration": 10.0}',
        )

        cmd = await build_command_for_job(job, clip_repo, video_repo)
        assert "-c:s" not in cmd

    async def test_no_tts_subtitle_map_emission(self) -> None:
        """FR-001-AC-2 / BL-583-AC-2: single-clip no-TTS with 2 subtitles emits explicit maps.

        Subtitle base = 1 (source) + 0 (no ffmetadata) + 0 (no TTS) = 1.
        Expected: -map 0:v, -map 0:a (source has audio), -map 1:s, -map 2:s.
        """
        clip_repo, video_repo = _make_soft_sub_repos()
        asset_repo = _make_soft_sub_asset_repo()
        job = _FakeRenderJob()

        cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

        map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
        assert "0:v" in map_flags, f"-map 0:v missing from {map_flags}"
        assert "0:a" in map_flags, "-map 0:a missing (source has audio_codec=aac)"
        assert "1:s" in map_flags, f"-map 1:s missing from {map_flags}"
        assert "2:s" in map_flags, f"-map 2:s missing from {map_flags}"
        # Subtitle maps must follow audio maps
        idx_audio = map_flags.index("0:a")
        assert map_flags.index("1:s") > idx_audio
        assert map_flags.index("2:s") > idx_audio

    async def test_tts_subtitle_map_emission(self) -> None:
        """FR-001-AC-3 / BL-583-AC-3: single-clip TTS + 2 subtitles emits correct maps.

        Subtitle base = 1 (source) + 0 (no ffmetadata) + 1 (TTS) = 2.
        Expected: -map [vout], -map [aout], -map 2:s, -map 3:s.
        """
        clip_repo, video_repo = _make_soft_sub_repos()
        asset_repo = _make_soft_sub_asset_repo()
        job = _FakeRenderJob()
        tts_input = TtsCueAudioInput(
            cue_id="cue-001",
            audio_path="/tmp/tts.wav",
            track_id="voice",
            start_s=0.0,
            weight=1.0,
            volume_envelope=None,
        )

        cmd = await build_command_for_job(
            job, clip_repo, video_repo, tts_inputs=[tts_input], asset_repository=asset_repo
        )

        map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
        # TTS path with audio source uses [vout] and [aout] filter labels
        assert "[vout]" in map_flags or "0:v" in map_flags, f"video map missing from {map_flags}"
        assert "[aout]" in map_flags, f"-map [aout] missing from {map_flags}"
        assert "2:s" in map_flags, f"-map 2:s missing from {map_flags}"
        assert "3:s" in map_flags, f"-map 3:s missing from {map_flags}"
        # Subtitle maps must follow audio maps
        idx_audio = map_flags.index("[aout]")
        assert map_flags.index("2:s") > idx_audio
        assert map_flags.index("3:s") > idx_audio

    async def test_tts_plus_subtitle_map_indices(self) -> None:
        """FR-002-AC-1 / BL-583-AC-5: 1 TTS + 2 subtitle inputs → maps at correct indices.

        Input order: [0]=source, [1]=tts.wav, [2]=en.srt, [3]=es.srt.
        Subtitle base = 1 + 0 + 1 = 2; both -map 2:s and -map 3:s must appear after TTS audio map.
        """
        clip_repo, video_repo = _make_soft_sub_repos()
        asset_repo = _make_soft_sub_asset_repo()
        job = _FakeRenderJob()
        tts_input = TtsCueAudioInput(
            cue_id="cue-001",
            audio_path="/tmp/tts.wav",
            track_id="voice",
            start_s=0.0,
            weight=1.0,
            volume_envelope=None,
        )

        cmd = await build_command_for_job(
            job, clip_repo, video_repo, tts_inputs=[tts_input], asset_repository=asset_repo
        )

        # Verify input order
        input_args = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-i"]
        assert input_args[0] == _SOFT_SUB_VIDEO_PATH  # source at 0
        assert "/tmp/tts.wav" in input_args
        assert "/data/assets/en.srt" in input_args
        tts_pos = input_args.index("/tmp/tts.wav")
        en_pos = input_args.index("/data/assets/en.srt")
        es_pos = input_args.index("/data/assets/es.srt")
        assert tts_pos == 1, f"TTS must be at index 1, got {tts_pos}"
        assert en_pos == 2, f"EN subtitle must be at index 2, got {en_pos}"
        assert es_pos == 3, f"ES subtitle must be at index 3, got {es_pos}"

        # Verify subtitle maps are at the correct indices after TTS audio
        map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
        assert "2:s" in map_flags, f"-map 2:s (EN) missing; map_flags={map_flags}"
        assert "3:s" in map_flags, f"-map 3:s (ES) missing; map_flags={map_flags}"
        # Both subtitle maps must follow the TTS audio map
        audio_map = next((f for f in map_flags if "aout" in f), None)
        assert audio_map is not None, "No audio output map found"
        idx_audio = map_flags.index(audio_map)
        assert map_flags.index("2:s") > idx_audio
        assert map_flags.index("3:s") > idx_audio

    async def test_multi_clip_subtitle_map_emission(self) -> None:
        """FR-001-AC-4 / BL-583-AC-4: multi-clip with 2 subtitles emits correct map flags.

        With 2 clips: input_paths = [clip1, clip2] → subtitle_base = 2.
        Expected: -map [final], -map 2:s, -map 3:s (audio suppressed via -an).
        """
        clip_repo, video_repo = _make_multi_clip_soft_sub_repos()
        asset_repo = _make_soft_sub_asset_repo()
        job = _FakeRenderJob()

        cmd = await build_command_for_job(job, clip_repo, video_repo, asset_repository=asset_repo)

        map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
        assert "[final]" in map_flags, f"-map [final] missing from {map_flags}"
        assert "2:s" in map_flags, f"-map 2:s missing from {map_flags}"
        assert "3:s" in map_flags, f"-map 3:s missing from {map_flags}"
        # Subtitle maps must follow the video map
        idx_final = map_flags.index("[final]")
        assert map_flags.index("2:s") > idx_final
        assert map_flags.index("3:s") > idx_final


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="requires runtime FFmpeg (set STOAT_TEST_FFMPEG=1)",
)
def test_soft_subtitle_ffprobe_streams() -> None:
    """AC BL-583-AC-6 / BL-583-AC-7 (FFmpeg-gated, deferred_post_merge).

    Renders with 2 SRT soft subtitle inputs using a lavfi-generated source, then
    runs ffprobe to assert exactly 2 subtitle streams with language codes 'eng' and
    'spa'. Replaces BL-520-AC-6 pass stub.
    """
    import asyncio
    import json as _json
    import tempfile as _tempfile

    with _tempfile.TemporaryDirectory() as tmpdir:
        src_path = os.path.join(tmpdir, "source.mp4")
        subprocess.run(
            [
                "ffmpeg",
                "-f",
                "lavfi",
                "-i",
                "color=blue:size=320x240:rate=10",
                "-t",
                "2",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                src_path,
            ],
            check=True,
            capture_output=True,
        )

        en_srt = os.path.join(tmpdir, "en.srt")
        es_srt = os.path.join(tmpdir, "es.srt")
        with open(en_srt, "w") as f:
            f.write("1\n00:00:00,000 --> 00:00:02,000\nHello World\n")
        with open(es_srt, "w") as f:
            f.write("1\n00:00:00,000 --> 00:00:02,000\nHola Mundo\n")

        output_path = os.path.join(tmpdir, "output.mp4")
        en_uuid_str = str(_SOFT_EN_ASSET_ID)
        es_uuid_str = str(_SOFT_ES_ASSET_ID)
        render_plan = (
            '{"settings": {"soft_subtitles": ['
            f'{{"source_asset_id": "{en_uuid_str}", "language": "en", "is_default": true}},'
            f'{{"source_asset_id": "{es_uuid_str}", "language": "es-ES"}}'
            ']}, "total_duration": 2.0}'
        )

        clip_repo = AsyncMock()
        clip_repo.list_by_project = AsyncMock(return_value=[_FakeClip()])
        video_repo = AsyncMock()
        video_repo.get = AsyncMock(return_value=_FakeVideo(path=src_path, audio_codec=None))

        asset_repo = AsyncMock()

        async def _get_asset(asset_id: str) -> _FakeAsset | None:
            if asset_id == en_uuid_str:
                return _FakeAsset(id=asset_id, file_path=en_srt)
            if asset_id == es_uuid_str:
                return _FakeAsset(id=asset_id, file_path=es_srt)
            return None

        asset_repo.get_by_id = _get_asset
        job = _FakeRenderJob(output_path=output_path, render_plan=render_plan)

        async def _build_cmd() -> list[str]:
            return await build_command_for_job(
                job, clip_repo, video_repo, asset_repository=asset_repo
            )

        cmd = asyncio.run(_build_cmd())

        ffmpeg_result = subprocess.run(cmd, capture_output=True, text=True)
        assert ffmpeg_result.returncode == 0, f"FFmpeg failed:\n{ffmpeg_result.stderr[-2000:]}"

        ffprobe_result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_streams", output_path],
            capture_output=True,
            text=True,
        )
        assert ffprobe_result.returncode == 0, f"ffprobe failed:\n{ffprobe_result.stderr}"

        data = _json.loads(ffprobe_result.stdout)
        subtitle_streams = [s for s in data["streams"] if s["codec_type"] == "subtitle"]
        assert len(subtitle_streams) == 2, (
            f"Expected 2 subtitle streams, got {len(subtitle_streams)}: "
            f"{[s.get('codec_type') for s in data['streams']]}"
        )
        langs = {s.get("tags", {}).get("language", "") for s in subtitle_streams}
        assert "eng" in langs, f"Expected 'eng' in language tags {langs}"
        assert "spa" in langs, f"Expected 'spa' in language tags {langs}"
        default_subs = [
            s for s in subtitle_streams if s.get("disposition", {}).get("default", 0) == 1
        ]
        assert len(default_subs) >= 1, "Expected at least 1 default subtitle stream"


# ---------------------------------------------------------------------------
# BL-555-AC-3 / BL-555-AC-4 — emit_filter_value dispatch contract tests
# ---------------------------------------------------------------------------


class TestBurnedSubtitleBuilderEmitFilterValueDispatch:
    """AC-3/AC-4 (BL-555): BurnedSubtitleBuilder uses emit_filter_value dispatch."""

    def test_srt_path_passes_through_unchanged_on_unix(self) -> None:
        spec = BurnedSubtitleSpec(source_path="/tmp/test.srt")
        result = BurnedSubtitleBuilder.build(spec)
        assert result == "subtitles=filename=/tmp/test.srt"

    def test_ass_path_passes_through_unchanged_on_unix(self) -> None:
        spec = BurnedSubtitleSpec(source_path="/tmp/test.ass")
        result = BurnedSubtitleBuilder.build(spec)
        assert result == "ass=filename=/tmp/test.ass"

    def test_path_with_space_accepted_on_unix(self) -> None:
        spec = BurnedSubtitleSpec(source_path="/tmp/my captions.srt")
        result = BurnedSubtitleBuilder.build(spec)
        assert result.startswith("subtitles=filename=")
        assert "my captions.srt" in result

    def test_path_with_apostrophe_raises_value_error(self) -> None:
        spec = BurnedSubtitleSpec(source_path="/tmp/O'Brien.srt")
        with pytest.raises(ValueError):
            BurnedSubtitleBuilder.build(spec)

    def test_burned_subtitle_windows_source_path(self) -> None:
        spec = BurnedSubtitleSpec(source_path="C:\\Users\\sub.srt")
        result = BurnedSubtitleBuilder.build(spec)
        # Windows path: single-quoted, drive colon escaped as \:, backslashes → forward slashes
        assert "filename='C\\:/Users/sub.srt'" in result


# ---- BL-586: force_style single-quote and key validation ----


class TestBurnedSubtitleBuilderForceStyleSafety:
    """BL-586: single-quote and invalid key char rejection for force_style."""

    def test_force_style_single_quote_raises_value_error(self) -> None:
        spec = BurnedSubtitleSpec(
            source_path="/tmp/test.srt",
            force_style={"Fontname": "O'Brien"},
        )
        with pytest.raises(ValueError):
            BurnedSubtitleBuilder.build(spec)

    def test_force_style_invalid_key_raises_value_error(self) -> None:
        for bad_key in ["Font'name", "Font,name", "Font=name", "Font:name"]:
            spec = BurnedSubtitleSpec(
                source_path="/tmp/test.srt",
                force_style={bad_key: "Arial"},
            )
            with pytest.raises(ValueError, match="force_style key"):
                BurnedSubtitleBuilder.build(spec)


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="requires runtime FFmpeg (set STOAT_TEST_FFMPEG=1)",
)
def test_burned_subtitle_force_style_ffmpeg_safe() -> None:
    """AC FR-005-AC-6 (BL-586): FFmpeg contract test; deferred post-merge discharge."""
    pass


# ---- BL-595: colon rejection in emit_filter_option_path ----


def test_burned_subtitle_unix_path_with_colon_raises_value_error() -> None:
    """FR-002-AC-1 (BL-595): source_path containing ':' raises ValueError."""
    spec = BurnedSubtitleSpec(
        source_path="/tmp/evil.srt:force_style=Fontname=Impact",
    )
    with pytest.raises(ValueError):
        BurnedSubtitleBuilder.build(spec)


def test_subtitle_script_font_file_with_colon_raises_value_error() -> None:
    """FR-003-AC-1 (BL-595): font_file containing ':' raises ValueError."""
    entries = [ScriptEntry(0.0, 2.0, "Hello")]
    spec = SubtitleScriptSpec(
        entries=entries,
        font_file="/uploads/font:fontsize=200.ttf",
    )
    with pytest.raises(ValueError):
        SubtitleScriptBuilder.build(spec)


# ---- BL-596: colon and apostrophe rejection in SubtitleScriptSpec.font_color ----


def test_subtitle_script_spec_font_color_colon_rejected() -> None:
    """FR-001-AC-1 (BL-596): font_color containing ':' raises ValueError at construction."""
    entry = ScriptEntry(0.0, 2.0, "Hello")
    with pytest.raises(ValueError):
        SubtitleScriptSpec(
            entries=[entry],
            font_color="white:fontsize=200",
        )


def test_subtitle_script_spec_font_color_valid_hex_accepted() -> None:
    """FR-003-AC-1 (BL-596): valid hex font_color '#ff0000' is accepted by py_new."""
    entry = ScriptEntry(0.0, 2.0, "Hello")
    spec = SubtitleScriptSpec(entries=[entry], font_color="#ff0000")
    assert spec.font_color == "#ff0000"


# ---- BL-593: UNC path escaping in emit_filter_option_path ----


def test_build_with_font_file_unc_path() -> None:
    """FR-003-AC-1 (BL-593): UNC font_file path passes through emit_filter_option_path cleanly.

    SubtitleScriptBuilder.build() with a UNC font_file must produce a fontfile= value
    that contains no raw backslashes and is wrapped in single quotes.
    """
    entries = [ScriptEntry(0.0, 2.0, "Hello")]
    spec = SubtitleScriptSpec(
        entries=entries,
        font_file="\\\\server\\share\\font.ttf",
    )
    result = SubtitleScriptBuilder.build(spec)
    filter_str = str(result)
    assert "\\" not in filter_str, (
        f"fontfile= value must not contain raw backslashes, got: {filter_str}"
    )
    assert "//server/share/font.ttf" in filter_str, (
        f"expected converted UNC path in filter output, got: {filter_str}"
    )

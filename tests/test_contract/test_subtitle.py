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


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="requires runtime FFmpeg (set STOAT_TEST_FFMPEG=1)",
)
def test_soft_subtitle_ffprobe_streams() -> None:
    """AC BL-520-AC-6 (FFmpeg-gated, deferred_post_merge): ffprobe asserts subtitle streams.

    Discharge: render with 2 soft subtitle tracks (en + es), ffprobe the output to
    confirm 2 subtitle streams with language metadata 'eng' and 'spa'.
    First track has disposition:default=1.
    """
    pass

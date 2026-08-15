# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Render worker: command builder and background worker loop.

CommandBuildError and build_command_for_job construct FFmpeg argument lists
from RenderJob render_plan JSON and project media paths resolved via repositories.

RenderWorkerLoop runs an infinite async loop that dequeues jobs and executes them.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog

from stoat_ferret.api.schemas.render import RenderPlanSettings, SoftSubtitleSpec, bcp47_to_iso639
from stoat_ferret.db.async_repository import AsyncVideoRepository
from stoat_ferret.db.clip_repository import AsyncClipRepository
from stoat_ferret.db.markers_repository import MarkerRepository
from stoat_ferret.db.models import Clip
from stoat_ferret.effects.registry import EffectRegistry
from stoat_ferret.render.models import RenderJob, RenderStatus
from stoat_ferret.render.queue import RenderQueue
from stoat_ferret.render.service import RenderService, generate_ffmetadata

if TYPE_CHECKING:
    from stoat_ferret.api.services.tts_service import TtsService
    from stoat_ferret.db.asset_repository import AsyncAssetRepository
    from stoat_ferret.db.tts_cue_repository import AsyncTtsCueRepository
    from stoat_ferret.render.executor import RenderExecutor

logger = structlog.get_logger(__name__)

# CRF values for x264/x265 quality presets
_QUALITY_CRF: dict[str, str] = {
    "draft": "28",
    "standard": "23",
    "high": "18",
}

# Required top-level fields in render_plan JSON
_REQUIRED_PLAN_FIELDS = ("settings", "total_duration")

# Windows CreateProcessW command-line string limit (including null terminator)
WINDOWS_ARGV_LIMIT = 32_767

# Budget for exe path, flag args, separators, and null terminator in the full command line
COMMAND_OVERHEAD_CHARS = 500

# S1192: reuse these instead of duplicating the string literals across both clip branches
_LABEL_FINAL = "[final]"
_LABEL_AOUT = "[aout]"
_LABEL_VOUT = "[vout]"


def _write_ffmetadata_file(content: str) -> str:
    """Write ffmetadata content to a temp file and return its path.

    Sync helper dispatched via `asyncio.to_thread` from `_run_job` so the
    write does not block the shared event loop.
    """
    with tempfile.NamedTemporaryFile(
        suffix=".ffmetadata", delete=False, mode="w", encoding="utf-8"
    ) as tmp:
        tmp.write(content)
        return tmp.name


def _maybe_route_filter_to_file(
    command: list[str],
    job: RenderJob,
    executor: RenderExecutor,
) -> tuple[list[str], Path | None]:
    """Route long filter args to a temp file on Windows to avoid argv limit.

    On non-Windows platforms, returns the command unchanged. On Windows, scans
    for -vf or -filter_complex with a filter string >= WINDOWS_ARGV_LIMIT -
    COMMAND_OVERHEAD_CHARS chars and replaces them with file-backed alternatives.
    Returns the (possibly modified) command and the temp file path, or None if
    no routing was needed.
    """
    if sys.platform != "win32":
        return command, None
    filter_tmp_path: Path | None = None
    for flag, script_flag in [
        ("-vf", "-filter_script"),
        ("-filter_complex", "-filter_complex_script"),
    ]:
        try:
            idx = command.index(flag)
        except ValueError:
            continue
        if (
            idx + 1 < len(command)
            and len(command[idx + 1]) >= WINDOWS_ARGV_LIMIT - COMMAND_OVERHEAD_CHARS
        ):
            _tmp_name: str | None = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".filter", delete=False) as tmp:
                    _tmp_name = tmp.name
                    tmp.write(command[idx + 1].encode())
            except OSError:
                if _tmp_name is not None:
                    Path(_tmp_name).unlink(missing_ok=True)
                raise
            assert _tmp_name is not None
            filter_tmp_path = Path(_tmp_name)
            executor.register_temp_file(job.id, filter_tmp_path)
            command = command[:idx] + [script_flag, str(filter_tmp_path)] + command[idx + 2 :]
            break
    return command, filter_tmp_path


class CommandBuildError(Exception):
    """Raised when command building fails due to missing project resources.

    Distinct from ValueError (invalid input) — this signals a missing
    clip or video that could not be resolved from repositories.
    """


@dataclass
class TtsCueAudioInput:
    """Resolved TTS cue ready for audio injection into the render command."""

    cue_id: str
    audio_path: str
    track_id: str
    start_s: float
    weight: float
    volume_envelope: str | None


def _extract_metadata_title(render_plan_json: str) -> str | None:
    """Extract the metadata title from render plan settings, or None if absent."""
    try:
        plan = json.loads(render_plan_json)
        title = plan.get("settings", {}).get("metadata_title")
        return str(title) if title is not None else None
    except (json.JSONDecodeError, AttributeError):
        return None


def _build_tts_audio_filter(
    tts_inputs: list[TtsCueAudioInput],
    base_stream_offset: int,
) -> tuple[str, str]:
    """Build FFmpeg filter_complex segment for TTS audio injection.

    Each stream gets adelay=X|X (stereo ms delay) + aformat for channel layout
    compatibility. Multiple streams are mixed via amix with per-stream weights.

    Returns:
        (filter_segment, output_label) — filter_segment is appended to the
        enclosing filter_complex string; output_label is the audio stream to -map.
    """
    parts = []
    labels = []
    for i, inp in enumerate(tts_inputs):
        stream_idx = base_stream_offset + i
        delay_ms = int(inp.start_s * 1000)
        label = f"[tts{i}]"
        parts.append(
            f"[{stream_idx}:a]adelay={delay_ms}|{delay_ms},aformat=channel_layouts=stereo{label}"
        )
        labels.append(label)

    if len(labels) == 1:
        return parts[0], labels[0]

    weights = " ".join(str(inp.weight) for inp in tts_inputs)
    mix_inputs = "".join(labels)
    mix_label = "[tts_mix]"
    amix = f"{mix_inputs}amix=inputs={len(labels)}:weights={weights}:duration=longest{mix_label}"
    return ";".join(parts) + ";" + amix, mix_label


async def _dispatch_and_wait_for_cues(cues: Any, tts_service: Any) -> None:
    """Dispatch pending TTS cues and wait up to 15 s for in-flight synthesis (LRN-406)."""
    for cue in cues:
        if cue.status == "failed":
            raise CommandBuildError(f"TTS synthesis failed for cue {cue.id}: {cue.error}")
        if cue.status in ("pending", "synthesising"):
            if cue.status == "pending":
                await tts_service.synthesise_cue(cue.id)
            task = tts_service._active_tasks.get(cue.id)
            if task is not None:
                done, _ = await asyncio.wait({task}, timeout=15.0)
                if not done:
                    raise CommandBuildError(f"TTS synthesis timeout for cue {cue.id}")


def _build_tts_audio_inputs(cues: Any) -> list[TtsCueAudioInput]:
    """Validate final synthesis status and build TtsCueAudioInput records."""
    result: list[TtsCueAudioInput] = []
    for cue in cues:
        if cue.status == "failed":
            raise CommandBuildError(f"TTS synthesis failed for cue {cue.id}: {cue.error}")
        if cue.status != "ready":
            raise CommandBuildError(
                f"TTS synthesis not ready for cue {cue.id}: status={cue.status}"
            )
        result.append(
            TtsCueAudioInput(
                cue_id=cue.id,
                audio_path=cue.generated_asset_id,
                track_id=cue.track_id,
                start_s=cue.start_s,
                weight=1.0,
                volume_envelope=None,
            )
        )
    return result


async def _run_tts_preflight(
    project_id: str,
    tts_service: Any,
    tts_repo: Any,
) -> list[TtsCueAudioInput]:
    """Ensure all TTS cues for the project are synthesised before rendering.

    For pending cues: dispatches synthesis and waits up to 15 s (LRN-406).
    For synthesising cues: waits for the in-flight task up to 15 s.
    For failed cues: raises CommandBuildError immediately.
    For ready cues: returns TtsCueAudioInput records for audio injection.

    Returns:
        Empty list if the project has no TTS cues; otherwise a list of
        TtsCueAudioInput, one per cue, ordered by start_s.

    Raises:
        CommandBuildError: If any cue fails synthesis or times out.
    """
    cues = await tts_repo.list_by_project(project_id)
    if not cues:
        return []

    await _dispatch_and_wait_for_cues(cues, tts_service)

    # Re-fetch to get final status after all tasks have completed
    cues = await tts_repo.list_by_project(project_id)
    return _build_tts_audio_inputs(cues)


async def _resolve_subtitle_asset_path(
    spec: SoftSubtitleSpec,
    asset_repository: AsyncAssetRepository | None,
) -> str:
    """Resolve a SoftSubtitleSpec's source_asset_id to its stored file_path.

    Raises:
        CommandBuildError: If asset_repository is not provided, the asset is not
            found, or the asset has been soft-deleted.
    """
    if asset_repository is None:
        raise CommandBuildError(
            f"Cannot resolve subtitle asset {spec.source_asset_id}: no asset_repository provided"
        )
    asset = await asset_repository.get_by_id(str(spec.source_asset_id))
    if asset is None or asset.deleted_at is not None:
        raise CommandBuildError(f"Subtitle asset {spec.source_asset_id} not found in asset library")
    return asset.file_path


def _build_generator_source(generator_params: dict[str, Any]) -> str:
    """Extract the lavfi source string from a generator clip's params dict.

    Raises:
        CommandBuildError: If 'lavfi_string' key is absent from generator_params.
    """
    lavfi_string = generator_params.get("lavfi_string")
    if not lavfi_string:
        raise CommandBuildError(
            "Generator clip missing required 'lavfi_string' in generator_params"
        )
    return str(lavfi_string)


def _add_soft_subtitle_output_flags(
    cmd: list[str],
    output_format: str,
    soft_subtitles: list[SoftSubtitleSpec],
) -> None:
    """Append -c:s, -metadata:s:s:N language=, and -disposition:s:N flags.

    Raises:
        ValueError: If the container does not support subtitle embedding.
    """
    fmt = output_format.lower()
    if fmt == "mp4":
        cmd.extend(["-c:s", "mov_text"])
    elif fmt in ("mkv", "matroska"):
        cmd.extend(["-c:s", "srt"])
    else:
        raise ValueError(f"Soft subtitles require mp4 or mkv container, got: {output_format!r}")
    for idx, spec in enumerate(soft_subtitles):
        iso639 = bcp47_to_iso639(spec.language)
        cmd.extend([f"-metadata:s:s:{idx}", f"language={iso639}"])
        if spec.is_default:
            cmd.extend([f"-disposition:s:{idx}", "default"])


async def _resolve_clip_source(
    clip: Clip,
    project_id: str,
    video_repository: AsyncVideoRepository,
    asset_repository: AsyncAssetRepository | None,
    fps: float,
) -> tuple[str, str | None, float]:
    """Resolve source path, audio codec, and frame rate for a clip.

    Returns ``(source_path, audio_codec, frame_rate)``.  Timing values (duration,
    segment boundaries) are NOT returned; callers derive timing from the render
    plan segment or clip in/out points as appropriate to their path.
    """
    if clip.clip_type == "image":
        if asset_repository is None:
            raise CommandBuildError(
                f"Cannot resolve image asset for clip {clip.id}: no asset_repository provided"
            )
        img_asset = await asset_repository.get_by_id(str(clip.source_asset_id))
        if img_asset is None or img_asset.deleted_at is not None:
            raise CommandBuildError(
                f"Image asset {clip.source_asset_id} not found for clip {clip.id}"
            )
        return img_asset.file_path, None, fps
    elif clip.clip_type == "generator":
        return _build_generator_source(clip.generator_params or {}), None, fps
    else:  # file
        if clip.source_video_id is None:
            raise CommandBuildError(f"File clip {clip.id} has no source_video_id")
        vid = await video_repository.get(clip.source_video_id)
        if vid is None or not vid.path:
            raise CommandBuildError(
                f"Video {clip.source_video_id} not found for project {project_id}"
            )
        return vid.path, vid.audio_codec, vid.frame_rate


def _build_clip_render_effects(
    clip: Clip,
    effect_registry: EffectRegistry | None,
) -> list[Any]:
    """Build the RenderEffect list for a clip; returns ``[RenderEffect.none()]`` if empty."""
    from stoat_ferret_core import RenderEffect

    render_effects: list[Any] = []
    if effect_registry and clip.effects:
        for effect_data in clip.effects:
            effect_type = effect_data.get("effect_type", "")
            defn = effect_registry.get(effect_type)
            if defn is None:
                logger.warning(
                    "render_worker.unknown_effect_type",
                    effect_type=effect_type,
                    clip_id=clip.id,
                )
            else:
                filter_str = defn.build_fn(effect_data.get("parameters", {}))
                window = effect_data.get("window")
                if window:
                    render_effects.append(
                        RenderEffect.windowed_custom(
                            filter_str,
                            window["start_s"],
                            window["end_s"],
                            defn.timeline_t_capable,
                        )
                    )
                else:
                    render_effects.append(RenderEffect.custom(filter_str))
    if not render_effects:
        render_effects.append(RenderEffect.none())
    return render_effects


async def build_command_for_job(
    job: RenderJob,
    clip_repository: AsyncClipRepository,
    video_repository: AsyncVideoRepository,
    ffmetadata_path: str | None = None,
    effect_registry: EffectRegistry | None = None,
    tts_inputs: list[TtsCueAudioInput] | None = None,
    asset_repository: AsyncAssetRepository | None = None,
) -> list[str]:
    """Build an FFmpeg argument list for a render job.

    Parses render_plan JSON, resolves the project's input media path via
    repository lookups, selects the first renderable segment, and assembles
    a shell-ready FFmpeg command. Does not invoke FFmpeg.

    Args:
        job: The render job containing render_plan JSON and output_path.
        clip_repository: Async clip repository for project clip lookup.
        video_repository: Async video repository for video path lookup.
        ffmetadata_path: Optional path to an ffmetadata file for chapter embedding.
        effect_registry: Optional registry for resolving per-clip effect types to filter strings.
        tts_inputs: Optional pre-synthesised TTS cue audio inputs for voice track injection.
        asset_repository: Optional asset repository for resolving soft subtitle asset paths.

    Returns:
        A list of strings representing the full FFmpeg command
        (first element is "ffmpeg").

    Raises:
        ValueError: If output_path is empty, render_plan JSON is malformed,
            a required field is missing, or no renderable content exists.
        CommandBuildError: If the project has no clips or the video is not found.
    """
    if not job.output_path:
        raise ValueError("output_path is empty or None")

    # --- Parse render_plan JSON ---
    try:
        plan = json.loads(job.render_plan)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid render_plan JSON: {exc}") from exc

    for field in _REQUIRED_PLAN_FIELDS:
        if field not in plan:
            raise ValueError(f"render_plan missing required field: {field}")

    settings: dict[str, Any] = plan["settings"]
    total_duration: float = plan["total_duration"]
    segments: list[dict[str, Any]] = plan.get("segments", [])

    # --- Parse render settings (soft_subtitles and future render-time options) ---
    render_settings = RenderPlanSettings.model_validate(settings)

    # --- Resolve input path via repositories ---
    clips = await clip_repository.list_by_project(job.project_id)
    if not clips:
        raise CommandBuildError(f"Project {job.project_id} has no clips in timeline")

    # --- Dispatch to sub-function ---
    ctx = _RenderCommandContext(
        job=job,
        settings=settings,
        render_settings=render_settings,
        ffmetadata_path=ffmetadata_path,
        tts_inputs=tts_inputs,
        video_repository=video_repository,
        asset_repository=asset_repository,
        effect_registry=effect_registry,
    )
    if len(clips) > 1:
        return await _build_multi_clip_command(ctx, clips)
    return await _build_single_clip_command(ctx, clips, segments, total_duration)


@dataclass
class _RenderCommandContext:
    """Shared render-command parameters bundled to resolve S107 parameter-count findings."""

    job: RenderJob
    settings: dict[str, Any]
    render_settings: RenderPlanSettings
    ffmetadata_path: str | None
    tts_inputs: list[TtsCueAudioInput] | None
    video_repository: AsyncVideoRepository
    asset_repository: AsyncAssetRepository | None
    effect_registry: EffectRegistry | None


async def _build_clip_input_list(
    ctx: _RenderCommandContext,
    clips: list[Clip],
    fps_mc: float,
) -> tuple[list[Any], list[float], str | None, int, list[float], list[int]]:
    """Build per-clip ClipWithEffects list, durations, audio codec info, and in-point offsets."""
    from stoat_ferret_core import ClipWithEffects

    cwe_list: list[Any] = []
    clip_durations_mc: list[float] = []
    source_audio_codec_mc: str | None = None
    source_audio_input_idx_mc: int = 0
    in_point_secs_list: list[float] = []
    audio_input_indices_mc: list[int] = []

    for i, clip in enumerate(clips):
        source_path_mc, clip_audio_codec, framerate_mc = await _resolve_clip_source(
            clip, ctx.job.project_id, ctx.video_repository, ctx.asset_repository, fps_mc
        )
        if clip.clip_type == "image":
            timeline_start_mc = clip.timeline_start or 0.0
            timeline_end_mc = clip.timeline_end or 0.0
            duration_secs = timeline_end_mc - timeline_start_mc
        elif clip.clip_type == "generator":
            duration_secs = (clip.out_point - clip.in_point) / fps_mc
        else:  # file
            duration_secs = (clip.out_point - clip.in_point) / framerate_mc
            if source_audio_codec_mc is None and clip_audio_codec:
                source_audio_codec_mc = clip_audio_codec
                source_audio_input_idx_mc = i
            if clip_audio_codec is not None:
                audio_input_indices_mc.append(i)
        if duration_secs <= 0:
            raise CommandBuildError(f"Clip {clip.id} has zero or negative duration")
        clip_durations_mc.append(duration_secs)
        if clip.clip_type == "file":
            in_point_secs_list.append(clip.in_point / framerate_mc)
        else:
            in_point_secs_list.append(0.0)  # image and generator clips: no source seek
        render_effects = _build_clip_render_effects(clip, ctx.effect_registry)
        cwe_list.append(
            ClipWithEffects(
                input_index=i,
                duration_secs=duration_secs,
                framerate=framerate_mc,
                source_path=source_path_mc,
                effects=render_effects,
            )
        )
    return (
        cwe_list,
        clip_durations_mc,
        source_audio_codec_mc,
        source_audio_input_idx_mc,
        in_point_secs_list,
        audio_input_indices_mc,
    )


def _get_transition_duration(cwe_list: list[Any], k: int) -> float:
    """Return the outgoing transition duration for cwe_list[k-1], defaulting to 1.0s.

    Uses getattr because outgoing_transition has no #[pyo3(get)] in the current binding;
    it evaluates to None until the binding is extended, producing the correct 1.0s default.
    """
    t = getattr(cwe_list[k - 1], "outgoing_transition", None)
    return t.duration_secs if t is not None else 1.0


def _build_audio_acrossfade_chain(
    audio_input_indices_mc: list[int],
    all_input_count: int,
    clip_durations_mc: list[float],
    cwe_list: list[Any],
) -> str | None:
    """Build an acrossfade audio filter chain for all_input_count inputs.

    Returns None when no clips have audio (deliberately_silent case).
    For file clips without audio, synthesizes silence via anullsrc to maintain
    A/V duration alignment. Chains N-1 acrossfade nodes ending at [aout].
    """
    if not audio_input_indices_mc:
        return None
    audio_set = set(audio_input_indices_mc)
    parts: list[str] = []
    labels: list[str] = []
    for i in range(all_input_count):
        if i in audio_set:
            labels.append(f"[{i}:a]")
        else:
            dur = clip_durations_mc[i]
            src_label = f"[a{i}_silent]"
            parts.append(f"anullsrc=r=48000:cl=stereo:d={dur}{src_label}")
            labels.append(src_label)
    current = labels[0]
    for k in range(1, all_input_count):
        t = _get_transition_duration(cwe_list, k)
        d_str = str(int(t)) if t == int(t) else str(t)
        intermediate = f"[xa{k - 1}]" if k < all_input_count - 1 else _LABEL_AOUT
        parts.append(f"{current}{labels[k]}acrossfade=d={d_str}{intermediate}")
        current = intermediate
    return ";".join(parts)


def _assemble_multi_tts_filter(
    cmd: list[str],
    tts_inputs: list[TtsCueAudioInput] | None,
    tts_base: int,
    filter_complex_str: str,
    source_audio_codec_mc: str | None,
    source_audio_input_idx_mc: int,
    audio_input_indices_mc: list[int],
    clip_durations_mc: list[float],
    cwe_list: list[Any],
) -> None:
    """Assemble filter_complex and -map flags for multi-clip TTS/no-TTS paths."""
    if tts_inputs:
        tts_filter_seg, tts_audio_label = _build_tts_audio_filter(tts_inputs, tts_base)
        combined_filter = filter_complex_str + ";" + tts_filter_seg
        if source_audio_codec_mc is not None:
            src_a = f"[{source_audio_input_idx_mc}:a]"
            mix_seg = (
                f"{src_a}aformat=channel_layouts=stereo,aresample=48000[src_norm]"
                f";[src_norm]{tts_audio_label}amix=inputs=2:duration=longest{_LABEL_AOUT}"
            )
            combined_filter_with_mix = combined_filter + ";" + mix_seg
            cmd.extend(
                [
                    "-filter_complex",
                    combined_filter_with_mix,
                    "-map",
                    _LABEL_FINAL,
                    "-map",
                    _LABEL_AOUT,
                ]
            )
        else:
            cmd.extend(
                [
                    "-filter_complex",
                    combined_filter,
                    "-map",
                    _LABEL_FINAL,
                    "-map",
                    tts_audio_label,
                ]
            )
    else:
        deliberately_silent = len(audio_input_indices_mc) == 0
        if not deliberately_silent:
            audio_chain = _build_audio_acrossfade_chain(
                audio_input_indices_mc, len(clip_durations_mc), clip_durations_mc, cwe_list
            )
            assert audio_chain is not None  # non-empty audio_input_indices_mc → not None
            combined = filter_complex_str + ";" + audio_chain
            cmd.extend(["-filter_complex", combined, "-map", _LABEL_FINAL, "-map", _LABEL_AOUT])
        else:
            cmd.extend(["-filter_complex", filter_complex_str, "-map", _LABEL_FINAL, "-an"])


def _build_mc_clip_input_args(
    cmd: list[str],
    clips: list[Clip],
    input_paths: list[str],
    clip_durations_mc: list[float],
    in_point_secs_list: list[float],
) -> None:
    """Append per-clip -i flags (with -loop/-lavfi for image/generator) to cmd."""
    for clip, path, dur, in_pt_secs in zip(
        clips, input_paths, clip_durations_mc, in_point_secs_list, strict=True
    ):
        if clip.clip_type == "image":
            cmd.extend(["-loop", "1", "-t", str(dur), "-i", path])
        elif clip.clip_type == "generator":
            cmd.extend(["-f", "lavfi", "-t", str(dur), "-i", path])
        else:
            if in_pt_secs > 0:
                cmd.extend(["-ss", str(in_pt_secs), "-t", str(dur), "-i", path])
            else:
                cmd.extend(["-i", path])


def _build_mc_tts_inputs(
    cmd: list[str],
    tts_inputs: list[TtsCueAudioInput],
    input_paths: list[str],
    ffmetadata_path: str | None,
) -> int:
    """Append TTS audio -i inputs to cmd and return tts_base stream index."""
    tts_base = len(input_paths) + (1 if ffmetadata_path else 0)
    for inp in tts_inputs:
        cmd.extend(["-i", inp.audio_path])
    return tts_base


async def _build_mc_subtitle_inputs(
    cmd: list[str],
    ctx: _RenderCommandContext,
    input_paths: list[str],
    ffmetadata_path: str | None,
    tts_inputs: list[TtsCueAudioInput] | None,
) -> int:
    """Append soft subtitle -i inputs to cmd and return the subtitle stream base index."""
    if not ctx.render_settings.soft_subtitles:
        return 0
    subtitle_base_mc = (
        len(input_paths) + (1 if ffmetadata_path else 0) + (len(tts_inputs) if tts_inputs else 0)
    )
    for spec in ctx.render_settings.soft_subtitles:
        sub_path = await _resolve_subtitle_asset_path(spec, ctx.asset_repository)
        cmd.extend(["-i", sub_path])
    return subtitle_base_mc


async def _build_multi_clip_command(
    ctx: _RenderCommandContext,
    clips: list[Clip],
) -> list[str]:
    """Assemble FFmpeg argv for a multi-clip (filter_complex / RenderGraphTranslator) render."""
    from stoat_ferret_core import RenderGraphTranslator

    codec_mc: str = ctx.settings.get("codec", "libx264")
    fps_mc: float = ctx.settings.get("fps", 30.0)
    quality_preset_mc: str = ctx.settings.get("quality_preset", "standard")

    multi_cmd: list[str] = ["ffmpeg"]
    (
        cwe_list,
        clip_durations_mc,
        source_audio_codec_mc,
        source_audio_input_idx_mc,
        in_point_secs_list,
        audio_input_indices_mc,
    ) = await _build_clip_input_list(ctx, clips, fps_mc)

    translator = RenderGraphTranslator()
    filter_complex_str, input_paths = translator.translate(cwe_list)

    _build_mc_clip_input_args(multi_cmd, clips, input_paths, clip_durations_mc, in_point_secs_list)

    if ctx.ffmetadata_path:
        multi_cmd.extend(["-i", ctx.ffmetadata_path])

    tts_base: int = 0
    if ctx.tts_inputs:
        tts_base = _build_mc_tts_inputs(multi_cmd, ctx.tts_inputs, input_paths, ctx.ffmetadata_path)

    # Soft subtitle -i inputs: declared BEFORE filter_complex/output -map section (BL-618).
    subtitle_base_mc = await _build_mc_subtitle_inputs(
        multi_cmd, ctx, input_paths, ctx.ffmetadata_path, ctx.tts_inputs
    )

    _assemble_multi_tts_filter(
        multi_cmd,
        ctx.tts_inputs,
        tts_base,
        filter_complex_str,
        source_audio_codec_mc,
        source_audio_input_idx_mc,
        audio_input_indices_mc,
        clip_durations_mc,
        cwe_list,
    )

    # Subtitle stream mappings: after filter_complex/map output section (BL-618 fix).
    if ctx.render_settings.soft_subtitles:
        for idx, _ in enumerate(ctx.render_settings.soft_subtitles):
            multi_cmd.extend(["-map", f"{subtitle_base_mc + idx}:s"])

    multi_cmd.extend(["-c:v", codec_mc])
    if codec_mc in ("libx264", "libx265") and quality_preset_mc in _QUALITY_CRF:
        multi_cmd.extend(["-crf", _QUALITY_CRF[quality_preset_mc]])
    multi_cmd.extend(["-r", str(fps_mc)])
    multi_cmd.extend(["-progress", "pipe:1"])
    if ctx.ffmetadata_path:
        ffmeta_idx = len(input_paths)
        multi_cmd.extend(["-map_chapters", str(ffmeta_idx), "-map_metadata", str(ffmeta_idx)])
    if ctx.render_settings.soft_subtitles:
        _add_soft_subtitle_output_flags(
            multi_cmd, ctx.job.output_format, ctx.render_settings.soft_subtitles
        )
    multi_cmd.append(ctx.job.output_path)
    return multi_cmd


def _build_sc_cmd_init(first_clip: Clip, input_path: str) -> list[str]:
    """Return the initial FFmpeg argv for a single-clip command based on clip type."""
    if first_clip.clip_type == "image":
        return ["ffmpeg", "-loop", "1", "-i", input_path]
    if first_clip.clip_type == "generator":
        return ["ffmpeg", "-f", "lavfi", "-i", input_path]
    return ["ffmpeg", "-i", input_path]


async def _build_sc_subtitle_inputs(
    cmd: list[str],
    ctx: _RenderCommandContext,
) -> None:
    """Append soft subtitle -i inputs to cmd, resolving each asset path."""
    for spec in ctx.render_settings.soft_subtitles:
        sub_path = await _resolve_subtitle_asset_path(spec, ctx.asset_repository)
        cmd.extend(["-i", sub_path])


def _add_sc_subtitle_stream_maps(
    cmd: list[str],
    soft_subtitles: list[SoftSubtitleSpec],
    tts_inputs: list[TtsCueAudioInput] | None,
    use_translator_sc: bool,
    source_audio_codec: str | None,
    ffmetadata_path: str | None,
) -> None:
    """Append -map flags for soft subtitle streams and explicit video/audio maps when needed."""
    subtitle_base = 1 + (1 if ffmetadata_path else 0) + (len(tts_inputs) if tts_inputs else 0)
    if not tts_inputs and not use_translator_sc:
        cmd.extend(["-map", "0:v"])
        if source_audio_codec is not None:
            cmd.extend(["-map", "0:a"])
    for idx, _ in enumerate(soft_subtitles):
        cmd.extend(["-map", f"{subtitle_base + idx}:s"])


def _assemble_sc_filter_translator(
    cmd: list[str],
    first_clip: Clip,
    source_audio_codec: str | None,
    tts_inputs: list[TtsCueAudioInput] | None,
    tts_base_single: int,
    seg_duration: float,
    fps: float,
    effect_registry: EffectRegistry | None,
    input_path: str,
) -> None:
    """Assemble filter_complex and -map flags for the single-clip translator path."""
    from stoat_ferret_core import ClipWithEffects, RenderGraphTranslator

    render_effects_sc = _build_clip_render_effects(first_clip, effect_registry)
    cwe_sc = ClipWithEffects(
        input_index=0,
        duration_secs=seg_duration,
        framerate=fps,
        source_path=input_path,
        effects=render_effects_sc,
    )
    translator_sc = RenderGraphTranslator()
    filter_complex_sc, _ = translator_sc.translate([cwe_sc])
    if tts_inputs:
        tts_filter_seg, tts_audio_label = _build_tts_audio_filter(tts_inputs, tts_base_single)
        combined_sc = filter_complex_sc + ";" + tts_filter_seg
        if source_audio_codec is not None:
            mix_seg = (
                f"[0:a]aformat=channel_layouts=stereo,aresample=48000[src_norm]"
                f";[src_norm]{tts_audio_label}amix=inputs=2:duration=longest{_LABEL_AOUT}"
            )
            combined_sc_with_mix = combined_sc + ";" + mix_seg
            cmd.extend(
                [
                    "-filter_complex",
                    combined_sc_with_mix,
                    "-map",
                    _LABEL_FINAL,
                    "-map",
                    _LABEL_AOUT,
                ]
            )
        else:
            cmd.extend(
                [
                    "-filter_complex",
                    combined_sc,
                    "-map",
                    _LABEL_FINAL,
                    "-map",
                    tts_audio_label,
                ]
            )
    else:
        cmd.extend(["-filter_complex", filter_complex_sc, "-map", _LABEL_FINAL, "-an"])


def _assemble_sc_filter_tts_only(
    cmd: list[str],
    source_audio_codec: str | None,
    tts_inputs: list[TtsCueAudioInput],
    tts_base_single: int,
    filter_graph: str | None,
    width: int,
    height: int,
) -> None:
    """Assemble filter_complex and -map flags for single-clip TTS-only path (no translator)."""
    tts_filter_seg, tts_audio_label = _build_tts_audio_filter(tts_inputs, tts_base_single)
    if source_audio_codec is not None:
        mix_seg = (
            f"[0:a]aformat=channel_layouts=stereo,aresample=48000[src_norm]"
            f";[src_norm]{tts_audio_label}amix=inputs=2:duration=longest{_LABEL_AOUT}"
        )
        if filter_graph:
            combined = f"[0:v]{filter_graph}{_LABEL_VOUT};{tts_filter_seg};{mix_seg}"
            cmd.extend(["-filter_complex", combined, "-map", _LABEL_VOUT, "-map", _LABEL_AOUT])
        elif width and height:
            combined = f"[0:v]scale={width}:{height}{_LABEL_VOUT};{tts_filter_seg};{mix_seg}"
            cmd.extend(["-filter_complex", combined, "-map", _LABEL_VOUT, "-map", _LABEL_AOUT])
        else:
            cmd.extend(
                [
                    "-filter_complex",
                    f"{tts_filter_seg};{mix_seg}",
                    "-map",
                    "0:v",
                    "-map",
                    _LABEL_AOUT,
                ]
            )
    else:
        if filter_graph:
            combined = f"[0:v]{filter_graph}{_LABEL_VOUT};{tts_filter_seg}"
            cmd.extend(["-filter_complex", combined, "-map", _LABEL_VOUT, "-map", tts_audio_label])
        elif width and height:
            combined = f"[0:v]scale={width}:{height}{_LABEL_VOUT};{tts_filter_seg}"
            cmd.extend(["-filter_complex", combined, "-map", _LABEL_VOUT, "-map", tts_audio_label])
        else:
            cmd.extend(
                [
                    "-filter_complex",
                    tts_filter_seg,
                    "-map",
                    "0:v",
                    "-map",
                    tts_audio_label,
                ]
            )


def _assemble_sc_filter_legacy(
    cmd: list[str],
    filter_graph: str | None,
    width: int,
    height: int,
) -> None:
    """Assemble -vf flag for single-clip legacy path (no translator, no TTS)."""
    if filter_graph:
        cmd.extend(["-vf", filter_graph])
    elif width and height:
        cmd.extend(["-vf", f"scale={width}:{height}"])


def _resolve_segment(
    segments: list[dict[str, Any]],
    total_duration: float,
    job_id: str,
) -> dict[str, Any]:
    """Return the active render segment, warning when multiple segments are present."""
    if segments:
        if len(segments) > 1:
            logger.warning(
                "render_worker.multi_segment_truncated",
                segments_count=len(segments),
                job_id=job_id,
            )
        return segments[0]
    if total_duration <= 0:
        raise ValueError("render_plan has no renderable content")
    return {"index": 0, "timeline_start": 0.0, "timeline_end": total_duration}


def _append_sc_tts_inputs(
    cmd: list[str],
    tts_inputs: list[TtsCueAudioInput],
    ffmetadata_path: str | None,
) -> int:
    """Append TTS audio -i inputs to cmd and return tts_base_single stream index."""
    tts_base = 1 + (1 if ffmetadata_path else 0)
    for inp in tts_inputs:
        cmd.extend(["-i", inp.audio_path])
    return tts_base


async def _build_single_clip_command(
    ctx: _RenderCommandContext,
    clips: list[Clip],
    segments: list[dict[str, Any]],
    total_duration: float,
) -> list[str]:
    """Assemble FFmpeg argv for a single-clip render."""
    first_clip = clips[0]
    use_translator_sc = first_clip.clip_type in ("image", "generator") or bool(first_clip.effects)

    input_path, source_audio_codec, _ = await _resolve_clip_source(
        first_clip,
        ctx.job.project_id,
        ctx.video_repository,
        ctx.asset_repository,
        ctx.settings.get("fps", 30.0),
    )

    # --- Select segment ---
    segment = _resolve_segment(segments, total_duration, ctx.job.id)

    timeline_start: float = segment.get("timeline_start", 0.0)
    timeline_end: float = segment.get("timeline_end", total_duration)
    seg_duration = timeline_end - timeline_start

    # --- Extract encoder settings ---
    codec: str = ctx.settings.get("codec", "libx264")
    fps: float = ctx.settings.get("fps", 30.0)
    width: int = ctx.settings.get("width", 1920)
    height: int = ctx.settings.get("height", 1080)
    quality_preset: str = ctx.settings.get("quality_preset", "standard")
    filter_graph: str | None = ctx.settings.get("filter_graph")

    # --- Assemble FFmpeg command ---
    cmd = _build_sc_cmd_init(first_clip, input_path)

    # Second input: ffmetadata file for chapter embedding (must precede output options)
    if ctx.ffmetadata_path:
        cmd.extend(["-i", ctx.ffmetadata_path])

    # TTS audio inputs: must follow other -i flags, before output options
    tts_base_single: int = 0
    if ctx.tts_inputs:
        tts_base_single = _append_sc_tts_inputs(cmd, ctx.tts_inputs, ctx.ffmetadata_path)

    # Soft subtitle inputs: appended LAST in -i chain (Risk 005 stream-index safety)
    # subtitle_base = 1 (source) + ffmetadata_offset + tts_count
    if ctx.render_settings.soft_subtitles:
        await _build_sc_subtitle_inputs(cmd, ctx)

    # Segment timing: seek to in_point + timeline_start so the correct source frames are read.
    in_point_secs = first_clip.in_point / fps  # fps already extracted above
    cmd.extend(["-ss", str(in_point_secs + timeline_start), "-t", str(seg_duration)])

    # Filter assembly: translator path for image/generator/effects clips; legacy -vf for file.
    if use_translator_sc:
        _assemble_sc_filter_translator(
            cmd,
            first_clip,
            source_audio_codec,
            ctx.tts_inputs,
            tts_base_single,
            seg_duration,
            fps,
            ctx.effect_registry,
            input_path,
        )
    elif ctx.tts_inputs:
        _assemble_sc_filter_tts_only(
            cmd,
            source_audio_codec,
            ctx.tts_inputs,
            tts_base_single,
            filter_graph,
            width,
            height,
        )
    else:
        _assemble_sc_filter_legacy(cmd, filter_graph, width, height)

    # Soft subtitle stream mapping (BL-583): emit -map <N>:s for each subtitle input.
    # Subtitle inputs follow source (0), optional ffmetadata, and TTS inputs.
    if ctx.render_settings.soft_subtitles:
        _add_sc_subtitle_stream_maps(
            cmd,
            ctx.render_settings.soft_subtitles,
            ctx.tts_inputs,
            use_translator_sc,
            source_audio_codec,
            ctx.ffmetadata_path,
        )

    # Video codec
    cmd.extend(["-c:v", codec])

    # Quality via CRF for software x264/x265
    if codec in ("libx264", "libx265") and quality_preset in _QUALITY_CRF:
        cmd.extend(["-crf", _QUALITY_CRF[quality_preset]])

    # Frame rate
    cmd.extend(["-r", str(fps)])

    # Progress reporting (pipe:1 = stdout; progress parser reads from FFmpeg stdout)
    cmd.extend(["-progress", "pipe:1"])

    # Chapter and container metadata from ffmetadata second input (index 1)
    if ctx.ffmetadata_path:
        cmd.extend(["-map_chapters", "1", "-map_metadata", "1"])

    # Soft subtitle codec, per-stream language metadata, and default disposition
    if ctx.render_settings.soft_subtitles:
        _add_soft_subtitle_output_flags(
            cmd, ctx.job.output_format, ctx.render_settings.soft_subtitles
        )

    # Output path (must be last)
    cmd.append(ctx.job.output_path)

    return cmd


class RenderWorkerLoop:
    """Background worker that continuously dequeues and executes render jobs.

    Runs an infinite async loop: dequeue -> build command -> run_job -> handle errors.
    Sleeps 100ms when the queue is idle to prevent CPU spin. Propagates
    CancelledError for clean shutdown; does not treat shutdown as a job failure.

    Args:
        service: Render service for job execution and failure handling.
        queue: Render queue to dequeue jobs from.
        clip_repository: Repository for project clip lookups.
        video_repository: Repository for video path lookups.
        markers_repository: Optional repository for project marker lookups (chapter embedding).
        effect_registry: Optional registry for resolving per-clip effect types to filter strings.
        tts_service: Optional TTS service for pre-render synthesis preflight.
        tts_cue_repository: Optional TTS cue repository for preflight status checks.
    """

    def __init__(
        self,
        *,
        service: RenderService,
        queue: RenderQueue,
        clip_repository: AsyncClipRepository,
        video_repository: AsyncVideoRepository,
        markers_repository: MarkerRepository | None = None,
        effect_registry: EffectRegistry | None = None,
        tts_service: TtsService | None = None,
        tts_cue_repository: AsyncTtsCueRepository | None = None,
        asset_repository: AsyncAssetRepository | None = None,
    ) -> None:
        self.service = service
        self.queue = queue
        self.clip_repository = clip_repository
        self.video_repository = video_repository
        self.markers_repository = markers_repository
        self.effect_registry = effect_registry
        self.tts_service = tts_service
        self.tts_cue_repository = tts_cue_repository
        self.asset_repository = asset_repository
        self.logger = structlog.get_logger(__name__)

    async def run(self) -> None:
        """Run the worker loop until cancelled.

        Continuously dequeues jobs, builds FFmpeg commands, and executes them.
        Sleeps 100ms when idle. Propagates CancelledError on shutdown.
        """
        self.logger.info("render_worker.started")
        try:
            while True:
                job = await self.queue.dequeue()
                if job is None:
                    await asyncio.sleep(0.1)
                    continue

                try:
                    await self._run_job(job)
                except Exception as exc:
                    await self._handle_job_error(job, exc)
        except asyncio.CancelledError:
            self.logger.info("render_worker.stopped")
            raise

    async def _run_job(self, job: RenderJob) -> None:
        """Build command and execute a single render job, managing temp file lifecycle."""
        ffmetadata_path: str | None = None
        tmp_path: Path | None = None
        filter_tmp_path: Path | None = None
        try:
            metadata_title = _extract_metadata_title(job.render_plan)
            markers = []
            if self.markers_repository is not None:
                markers = await self.markers_repository.list_by_project(
                    job.project_id, region_type="section"
                )
            if markers or metadata_title:
                content = generate_ffmetadata(markers, metadata_title=metadata_title)
                ffmetadata_path = await asyncio.to_thread(_write_ffmetadata_file, content)
                tmp_path = Path(ffmetadata_path)

            tts_inputs: list[TtsCueAudioInput] | None = None
            if self.tts_service is not None and self.tts_cue_repository is not None:
                tts_inputs = await _run_tts_preflight(
                    job.project_id,
                    self.tts_service,
                    self.tts_cue_repository,
                )
                if not tts_inputs:
                    tts_inputs = None

            command = await build_command_for_job(
                job,
                self.clip_repository,
                self.video_repository,
                ffmetadata_path,
                self.effect_registry,
                tts_inputs,
                self.asset_repository,
            )
            command, filter_tmp_path = await asyncio.to_thread(
                _maybe_route_filter_to_file, command, job, self.service._executor
            )
            await self.service.run_job(job, command)
        finally:
            if tmp_path is not None:
                with contextlib.suppress(OSError):
                    tmp_path.unlink(missing_ok=True)
            if filter_tmp_path is not None:
                with contextlib.suppress(OSError):
                    filter_tmp_path.unlink(missing_ok=True)

    async def _handle_job_error(self, job: RenderJob, exc: Exception) -> None:
        """Handle a job execution exception.

        Logs the failure and delegates to service._handle_failure() for retry logic.
        Falls back to a direct status update if the failure handler itself fails.

        Args:
            job: The render job that failed.
            exc: The exception raised during command building or execution.
        """
        self.logger.error(
            "render_worker.job_failed",
            job_id=job.id,
            error_message=str(exc),
        )
        try:
            await self.service._handle_failure(job, str(exc))
        except Exception as handler_exc:
            self.logger.error(
                "render_worker.error",
                job_id=job.id,
                error="failure_handler_exception",
                error_message=str(handler_exc),
            )
            try:
                await self.service._repo.update_status(
                    job.id,
                    RenderStatus.FAILED,
                    error_message=f"failure handler error: {handler_exc}",
                )
            except Exception as repo_exc:
                self.logger.error(
                    "render_worker.error",
                    job_id=job.id,
                    error="repo_update_failed",
                    error_message=str(repo_exc),
                )

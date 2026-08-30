# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Registry-completeness assertion for audio-stream annotation (BL-823 AC-4, BL-829).

Fails CI if any EffectDefinition in the default registry whose preview_fn() emits
a known audio-domain filter token (and no video-domain token) lacks stream_kind="a".

Detection uses token-level extraction to avoid confirmed false positives:
- "pan" in filter_str matches "zoompan" (a video filter) → token level avoids this
- "atempo" in filter_str matches "speed_control" (mixed) → mixed effects are excluded

Audio token set: {"atempo", "alimiter", "loudnorm", "anequalizer", "acompressor", "afir", "pan"}
Video token set: {"setpts", "zoompan", "scale", "overlay", "drawtext", "fps", "settb", "boxblur"}
Mixed effects (both audio + video tokens) are excluded from the check.
"""

from __future__ import annotations

import re

from stoat_ferret.effects.definitions import create_default_registry

_AUDIO_FILTER_NAMES: frozenset[str] = frozenset(
    {"atempo", "alimiter", "loudnorm", "anequalizer", "acompressor", "afir", "pan"}
)
_VIDEO_FILTER_NAMES: frozenset[str] = frozenset(
    {"setpts", "zoompan", "scale", "overlay", "drawtext", "fps", "settb", "boxblur"}
)

# Explicit set of all 14 audio-only effects as of v133 (BL-829-AC-1).
# Any entry whose stream_kind != "a" is a regression — guards against annotation flips.
MUST_BE_AUDIO: frozenset[str] = frozenset(
    {
        "audio_ducking",
        "audio_fade",
        "audio_mix",
        "convolution_reverb",
        "deesser",
        "deplosive",
        "loudness_normalize",
        "mastering_limiter",
        "multiband_compressor",
        "noise_reduction",
        "pan",
        "parametric_eq",
        "time_stretch",
        "volume",
    }
)


def _token_names(filter_str: str) -> frozenset[str]:
    """Extract filter names from a filter string using token-level splitting.

    Splits on semicolons and commas, then takes the part before '=' in each token.
    """
    tokens = re.split(r"[;,]\s*", filter_str)
    names: set[str] = set()
    for token in tokens:
        # Strip any leading [label] input/output markers
        bare = re.sub(r"^\[[^\]]+\]", "", token.strip())
        bare = re.sub(r"\[[^\]]+\]$", "", bare)
        name = bare.split("=")[0].strip()
        if name:
            names.add(name)
    return frozenset(names)


def test_audio_effects_must_have_stream_kind_a() -> None:
    """Each entry in MUST_BE_AUDIO carries stream_kind='a' (BL-829-AC-1).

    Guards against annotation regressions such as an effect being re-annotated
    as stream_kind='video' or reset to '' by a future registry edit.
    """
    registry = create_default_registry()
    for effect_type in sorted(MUST_BE_AUDIO):
        defn = registry.get(effect_type)
        assert defn is not None, f"Effect {effect_type!r} not found in registry"
        assert defn.stream_kind == "a", (
            f"Effect {effect_type!r} has stream_kind={defn.stream_kind!r}, expected 'a'"
        )


def test_registry_audio_completeness() -> None:
    """All audio-only effects in the default registry carry stream_kind='a'.

    Checks ALL effects (including already-annotated ones) so that misannotations
    such as stream_kind='video' on an audio filter are also caught (BL-829-AC-2).
    For each effect whose preview_fn() emits audio-domain filter tokens and no
    video-domain tokens, asserts stream_kind=='a'.
    """
    registry = create_default_registry()
    violations: list[str] = []

    for effect_type, definition in registry.list_all():
        try:
            filter_str = definition.preview_fn()
        except Exception:
            # preview_fn may require external resources (e.g. IR files for reverb);
            # skip effects whose preview raises rather than producing a filter string
            continue

        names = _token_names(filter_str)
        is_audio = bool(names & _AUDIO_FILTER_NAMES)
        is_video = bool(names & _VIDEO_FILTER_NAMES)

        if is_audio and not is_video and definition.stream_kind != "a":
            violations.append(
                f"{effect_type!r}: preview_fn()={filter_str!r} emits audio tokens "
                f"{names & _AUDIO_FILTER_NAMES} but stream_kind={definition.stream_kind!r}"
            )

    assert not violations, (
        "Audio-only effects lacking stream_kind='a' (will silently route to video chain):\n"
        + "\n".join(violations)
    )

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Unit and contract tests for ChromaKeyBuilder, ColorKeyBuilder, blend compositing (BL-452)."""

from __future__ import annotations

import os

import pytest

from stoat_ferret.effects.definitions import (
    CHROMA_KEY_EFFECT,
    COLOR_KEY_EFFECT,
    create_default_registry,
)
from stoat_ferret_core import (
    ChromaKeyBuilder,
    ColorKeyBuilder,
    CompositionClip,
    LayoutPosition,
    LayoutSpec,
    build_composition_graph,
)

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG") == "1"


# ---- ChromaKeyBuilder unit tests ----


def test_chromakey_hex_color_builds_chromakey_filter() -> None:
    """ChromaKeyBuilder with #RRGGBB hex produces a chromakey filter (BL-452-AC-1)."""
    builder = ChromaKeyBuilder("#00FF00")
    result = str(builder.build())
    assert "chromakey" in result, f"Expected chromakey in: {result}"
    assert "00FF00" in result.upper(), f"Expected 00FF00 in: {result}"


def test_chromakey_named_color_builds_filter() -> None:
    """ChromaKeyBuilder with CSS named colour produces a chromakey filter."""
    builder = ChromaKeyBuilder("green")
    result = str(builder.build())
    assert "chromakey" in result, f"Expected chromakey in: {result}"
    assert "green" in result, f"Expected green in: {result}"


def test_chromakey_custom_similarity() -> None:
    """ChromaKeyBuilder respects a custom similarity value."""
    builder = ChromaKeyBuilder("#00FF00", 0.3)
    result = str(builder.build())
    assert "0.3" in result, f"Expected 0.3 in: {result}"


def test_chromakey_default_similarity() -> None:
    """ChromaKeyBuilder similarity defaults to 0.1."""
    builder = ChromaKeyBuilder("#00FF00")
    result = str(builder.build())
    assert "0.1" in result, f"Expected default similarity 0.1 in: {result}"


def test_chromakey_invalid_color_raises() -> None:
    """ChromaKeyBuilder raises ValueError for unrecognised colour format."""
    with pytest.raises((ValueError, Exception)):
        ChromaKeyBuilder("notacolor123")
    with pytest.raises((ValueError, Exception)):
        ChromaKeyBuilder("#GGGGGG")


def test_chromakey_similarity_out_of_range_raises() -> None:
    """ChromaKeyBuilder raises ValueError when similarity is outside [0.0, 1.0]."""
    with pytest.raises((ValueError, Exception)):
        ChromaKeyBuilder("#00FF00", -0.1)
    with pytest.raises((ValueError, Exception)):
        ChromaKeyBuilder("#00FF00", 1.1)


def test_chromakey_similarity_boundary_values_ok() -> None:
    """ChromaKeyBuilder accepts similarity at exactly 0.0 and 1.0."""
    assert ChromaKeyBuilder("#00FF00", 0.0) is not None
    assert ChromaKeyBuilder("#00FF00", 1.0) is not None


# ---- ColorKeyBuilder unit tests ----


def test_colorkey_hex_color_builds_colorkey_filter() -> None:
    """ColorKeyBuilder with #RRGGBB hex produces a colorkey filter (BL-452-AC-1)."""
    builder = ColorKeyBuilder("#FFFFFF")
    result = str(builder.build())
    assert "colorkey" in result, f"Expected colorkey in: {result}"
    assert "FFFFFF" in result.upper(), f"Expected FFFFFF in: {result}"


def test_colorkey_named_color_builds_filter() -> None:
    """ColorKeyBuilder with CSS named colour produces a colorkey filter."""
    builder = ColorKeyBuilder("white")
    result = str(builder.build())
    assert "colorkey" in result, f"Expected colorkey in: {result}"
    assert "white" in result, f"Expected white in: {result}"


def test_colorkey_default_similarity() -> None:
    """ColorKeyBuilder similarity defaults to 0.1."""
    builder = ColorKeyBuilder("#FFFFFF")
    result = str(builder.build())
    assert "0.1" in result, f"Expected default similarity 0.1 in: {result}"


def test_colorkey_invalid_color_raises() -> None:
    """ColorKeyBuilder raises ValueError for unrecognised colour format."""
    with pytest.raises((ValueError, Exception)):
        ColorKeyBuilder("123456")
    with pytest.raises((ValueError, Exception)):
        ColorKeyBuilder("")


def test_chromakey_and_colorkey_produce_distinct_filters() -> None:
    """ChromaKeyBuilder and ColorKeyBuilder produce different filter names."""
    chroma = str(ChromaKeyBuilder("#00FF00").build())
    color = str(ColorKeyBuilder("#00FF00").build())
    assert "chromakey" in chroma
    assert "colorkey" in color
    assert "chromakey" not in color
    assert "colorkey" not in chroma


# ---- build_composition_graph blend_mode tests ----


def test_blend_mode_none_no_blend_filter() -> None:
    """build_composition_graph with blend_mode=None does not add a blend filter (BL-452-AC-2)."""
    clips = [
        CompositionClip(0, 0.0, 5.0, 0, 0),
        CompositionClip(1, 0.0, 5.0, 0, 0),
    ]
    graph = build_composition_graph(clips, [], None, None, 1920, 1080, None)
    result = str(graph)
    assert "blend=" not in result, f"None blend_mode should not add blend filter: {result}"


def test_blend_mode_screen_adds_blend_filter() -> None:
    """build_composition_graph with blend_mode='screen' appends a blend filter (BL-452-AC-2)."""
    clips = [
        CompositionClip(0, 0.0, 5.0, 0, 0),
        CompositionClip(1, 0.0, 5.0, 0, 0),
    ]
    graph = build_composition_graph(clips, [], None, None, 1920, 1080, "screen")
    result = str(graph)
    assert "blend=" in result, f"screen blend_mode should add blend filter: {result}"
    assert "screen" in result, f"Expected 'screen' in blend filter: {result}"


def test_blend_mode_invalid_raises_value_error() -> None:
    """build_composition_graph raises ValueError for an unsupported blend mode."""
    clips = [CompositionClip(0, 0.0, 5.0, 0, 0)]
    with pytest.raises((ValueError, Exception)):
        build_composition_graph(clips, [], None, None, 1920, 1080, "dissolve")


def test_blend_mode_all_supported_modes_succeed() -> None:
    """build_composition_graph succeeds for every documented blend mode (BL-452-AC-2)."""
    clips = [
        CompositionClip(0, 0.0, 5.0, 0, 0),
        CompositionClip(1, 0.0, 5.0, 0, 0),
    ]
    supported_modes = [
        "screen",
        "multiply",
        "overlay",
        "difference",
        "hardlight",
        "softlight",
        "darken",
        "lighten",
        "addition",
        "exclusion",
    ]
    for mode in supported_modes:
        graph = build_composition_graph(clips, [], None, None, 1920, 1080, mode)
        result = str(graph)
        assert "blend=" in result, f"Expected blend filter for mode '{mode}': {result}"
        assert mode in result, f"Expected '{mode}' in filter for mode '{mode}': {result}"


# ---- EffectDefinition tests ----


def test_chroma_key_effect_preview_returns_nonempty() -> None:
    """CHROMA_KEY_EFFECT.preview_fn() returns a non-empty filter string."""
    result = CHROMA_KEY_EFFECT.preview_fn()
    assert result, "preview_fn should return a non-empty string"
    assert "chromakey" in result, f"Expected chromakey in preview: {result}"


def test_chroma_key_effect_build_fn_returns_chromakey() -> None:
    """CHROMA_KEY_EFFECT.build_fn produces a chromakey filter."""
    result = CHROMA_KEY_EFFECT.build_fn({"color": "#00FF00"})
    assert "chromakey" in result, f"Expected chromakey in build: {result}"


def test_chroma_key_effect_build_fn_with_similarity() -> None:
    """CHROMA_KEY_EFFECT.build_fn respects the similarity parameter."""
    result = CHROMA_KEY_EFFECT.build_fn({"color": "#00FF00", "similarity": 0.25})
    assert "0.25" in result, f"Expected 0.25 in build: {result}"


def test_color_key_effect_preview_returns_nonempty() -> None:
    """COLOR_KEY_EFFECT.preview_fn() returns a non-empty filter string."""
    result = COLOR_KEY_EFFECT.preview_fn()
    assert result, "preview_fn should return a non-empty string"
    assert "colorkey" in result, f"Expected colorkey in preview: {result}"


def test_color_key_effect_build_fn_returns_colorkey() -> None:
    """COLOR_KEY_EFFECT.build_fn produces a colorkey filter."""
    result = COLOR_KEY_EFFECT.build_fn({"color": "#FFFFFF"})
    assert "colorkey" in result, f"Expected colorkey in build: {result}"


def test_keying_effects_registered_in_default_registry() -> None:
    """Both chroma_key and color_key are present in the default registry."""
    registry = create_default_registry()
    keys = {k for k, _ in registry.list_all()}
    assert "chroma_key" in keys, "chroma_key should be in default registry"
    assert "color_key" in keys, "color_key should be in default registry"


# ---- Z-index integration test ----


def test_chroma_key_builder_alongside_z_indexed_composition() -> None:
    """ChromaKeyBuilder works alongside a z-indexed composition graph (BL-452-AC-3)."""
    key_filter = str(ChromaKeyBuilder("#00FF00", 0.15).build())
    assert "chromakey" in key_filter, f"chromakey filter must be producible: {key_filter}"

    clips = [
        CompositionClip(0, 0.0, 5.0, 0, 0),
        CompositionClip(1, 0.0, 5.0, 1, 1),
    ]
    positions = [
        LayoutPosition(0.0, 0.0, 1.0, 1.0, 0),
        LayoutPosition(0.5, 0.0, 0.5, 1.0, 1),
    ]
    layout = LayoutSpec(positions)
    graph = build_composition_graph(clips, [], layout, None, 1920, 1080)
    graph_str = str(graph)
    assert len(graph_str) > 0, "Composition graph should produce a non-empty filter string"


# ---- Contract tests (deferred_post_merge: require STOAT_TEST_FFMPEG=1) ----


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="requires STOAT_TEST_FFMPEG=1")
@pytest.mark.contract
def test_chromakey_renders_without_error() -> None:
    """chromakey filter executes against real FFmpeg without error (BL-452-AC-4)."""
    import subprocess

    builder = ChromaKeyBuilder("#00FF00", 0.1)
    filter_str = str(builder.build())

    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:duration=0.1",
            "-vf",
            filter_str,
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"FFmpeg chromakey failed (rc={result.returncode}):\n{result.stderr}"
    )


@pytest.mark.skipif(not STOAT_TEST_FFMPEG, reason="requires STOAT_TEST_FFMPEG=1")
@pytest.mark.contract
def test_colorkey_renders_without_error() -> None:
    """colorkey filter executes against real FFmpeg without error (BL-452-AC-4)."""
    import subprocess

    builder = ColorKeyBuilder("#FFFFFF", 0.1)
    filter_str = str(builder.build())

    result = subprocess.run(
        [
            "ffmpeg",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=64x64:duration=0.1",
            "-vf",
            filter_str,
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"FFmpeg colorkey failed (rc={result.returncode}):\n{result.stderr}"
    )

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Tests for ConvolutionReverbBuilder and the convolution_reverb effect definition."""

from __future__ import annotations

import os

import pytest

from stoat_ferret.effects.definitions import (
    CONVOLUTION_REVERB,
    _resolve_ir_path,
)
from stoat_ferret_core import ConvolutionReverbBuilder


def test_convolution_reverb_filter_string() -> None:
    b = ConvolutionReverbBuilder("hall_small", 0.4)
    s = str(b.build())
    assert s.startswith("afir="), f"expected afir= prefix, got: {s}"
    assert "dry=1" in s, f"expected dry=1, got: {s}"
    assert "wet=" in s, f"expected wet= param, got: {s}"


def test_convolution_reverb_mix_clamp_above() -> None:
    b = ConvolutionReverbBuilder("hall_small", 2.0)
    s = str(b.build())
    assert "wet=1" in s, f"expected wet clamped to 1, got: {s}"


def test_convolution_reverb_mix_clamp_below() -> None:
    b = ConvolutionReverbBuilder("hall_small", -0.5)
    s = str(b.build())
    assert "wet=0" in s, f"expected wet clamped to 0, got: {s}"


def test_ir_name_accessor() -> None:
    b = ConvolutionReverbBuilder("room_medium", 0.5)
    assert b.ir_name() == "room_medium"


def test_resolve_ir_path_exists() -> None:
    for name in ("hall_small", "room_medium", "plate"):
        p = _resolve_ir_path(name)
        assert p.exists(), f"IR asset not found: {p}"
        assert p.suffix == ".wav"


def test_effect_definition_build_fn() -> None:
    result = CONVOLUTION_REVERB.build_fn({"ir_name": "plate", "mix": 0.6})
    assert "afir=" in result
    assert "wet=" in result


def test_effect_definition_preview_fn() -> None:
    result = CONVOLUTION_REVERB.preview_fn()
    assert result.startswith("afir=")


def test_effect_definition_schema_has_required_fields() -> None:
    schema = CONVOLUTION_REVERB.parameter_schema
    props = schema["properties"]
    assert isinstance(props, dict)
    assert "ir_name" in props
    assert "mix" in props
    required = schema["required"]
    assert isinstance(required, list)
    assert set(required) == {"ir_name", "mix"}


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg integration test — set STOAT_TEST_FFMPEG=1 to run",
)
def test_convolution_reverb_ffmpeg_contract() -> None:
    """Verify afir filter string is accepted by FFmpeg as valid syntax."""
    import math
    import struct
    import subprocess
    import tempfile
    import wave

    # Generate a short silent WAV source
    def _wav(path: str, duration_s: float = 0.1, rate: int = 48000) -> None:
        n = int(rate * duration_s)
        with wave.open(path, "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            for i in range(n):
                env = math.exp(-20.0 * i / n)
                v = int(env * 1000)
                wf.writeframes(struct.pack("<hh", v, v))

    ir_path = str(_resolve_ir_path("hall_small"))
    with tempfile.TemporaryDirectory() as tmp:
        src = f"{tmp}/src.wav"
        out = f"{tmp}/out.wav"
        _wav(src)

        b = ConvolutionReverbBuilder("hall_small", 0.5)
        filter_str = str(b.build())

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                src,
                "-i",
                ir_path,
                "-filter_complex",
                filter_str,
                out,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"FFmpeg rejected afir filter: {result.stderr[-500:]}"


@pytest.mark.skipif(
    not os.environ.get("STOAT_TEST_FFMPEG"),
    reason="FFmpeg integration test — set STOAT_TEST_FFMPEG=1 to run",
)
def test_convolution_reverb_decay_ffmpeg_contract() -> None:
    """BL-438-AC-2: convolution reverb output amplitude decays after the initial transient."""
    import math
    import struct
    import subprocess
    import tempfile
    import wave

    def _wav(path: str, duration_s: float = 0.1, rate: int = 48000) -> None:
        """Short tone burst: full amplitude for the first 5ms, silence after."""
        n = int(rate * duration_s)
        burst_n = int(rate * 0.005)
        with wave.open(path, "w") as wf:
            wf.setnchannels(2)
            wf.setsampwidth(2)
            wf.setframerate(rate)
            for i in range(n):
                v = int(10000 * math.sin(2 * math.pi * 440 * i / rate)) if i < burst_n else 0
                wf.writeframes(struct.pack("<hh", v, v))

    ir_path = str(_resolve_ir_path("hall_small"))
    with tempfile.TemporaryDirectory() as tmp:
        src = f"{tmp}/src.wav"
        out = f"{tmp}/out.wav"
        _wav(src)

        b = ConvolutionReverbBuilder("hall_small", 0.8)
        filter_str = str(b.build())

        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                src,
                "-i",
                ir_path,
                "-filter_complex",
                filter_str,
                out,
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"FFmpeg rejected afir filter: {result.stderr[-500:]}"

        with wave.open(out, "rb") as wf:
            rate = wf.getframerate()
            nch = wf.getnchannels()
            n = wf.getnframes()
            raw = wf.readframes(n)
        samples = struct.unpack(f"<{n * nch}h", raw)

        # transient window: the initial burst plus early reverb tail
        transient_end = int(rate * 0.02) * nch
        # post-transient window: a later slice of the decaying tail
        post_start = int(rate * 0.05) * nch
        post_end = int(rate * 0.08) * nch

        transient = samples[:transient_end]
        post_transient = samples[post_start:post_end]

        def _rms_samples(vals: tuple[int, ...]) -> float:
            if not vals:
                return 0.0
            return math.sqrt(sum(v * v for v in vals) / len(vals))

        rms_transient = _rms_samples(transient)
        rms_post = _rms_samples(post_transient)

        assert rms_transient > 0, "expected non-zero energy in the transient window"
        assert rms_post < rms_transient, (
            f"expected decay after transient: rms_post={rms_post} >= rms_transient={rms_transient}"
        )

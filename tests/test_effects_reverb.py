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
def test_convolution_reverb_contract_ffmpeg() -> None:
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

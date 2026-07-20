# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Behavioral wellness contract tests for multi-track audio mixing (BL-517).

Unit tests (no FFmpeg) verify the assembled filter string structure.
FFmpeg tests (marked requires_ffmpeg) run the filter and assert audio properties.
"""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import pytest

from stoat_ferret.api.services.audio_service import assemble_multi_track_mixer
from stoat_ferret.db.models import DuckingPair, Track
from tests.conftest import requires_ffmpeg
from tests.helpers.audio_helpers import _measure_band_db_windowed

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------


def _track(
    track_id: str,
    kind: str,
    *,
    weight: float = 1.0,
    volume_envelope: str | None = None,
    track_type: str = "audio",
) -> Track:
    return Track(
        id=track_id,
        project_id="proj-test",
        track_type=track_type,
        label=kind,
        kind=kind if track_type == "audio" else None,
        weight=weight,
        volume_envelope=volume_envelope,
    )


def _pair(
    pair_id: str,
    ducked_id: str,
    sidechain_id: str,
    *,
    threshold: float = 0.02,
    ratio: float = 8.0,
    attack_ms: float = 20.0,
    release_ms: float = 300.0,
    apply_pre_volume: bool = False,
) -> DuckingPair:
    return DuckingPair(
        id=pair_id,
        project_id="proj-test",
        ducked_track_id=ducked_id,
        sidechain_track_id=sidechain_id,
        threshold=threshold,
        ratio=ratio,
        attack_ms=attack_ms,
        release_ms=release_ms,
        apply_pre_volume=apply_pre_volume,
        created_at=_NOW,
        updated_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Unit tests (no FFmpeg)
# ---------------------------------------------------------------------------


class TestAssembleMultiTrackMixerUnit:
    """Filter-string contract tests — no FFmpeg required."""

    def test_single_track_emits_aformat_and_amix(self) -> None:
        result = assemble_multi_track_mixer([_track("t1", "voice")], [])
        assert "aformat=channel_layouts=stereo" in result
        assert "amix=inputs=1" in result

    def test_non_audio_tracks_skipped(self) -> None:
        tracks = [
            _track("v1", "video", track_type="video"),
            _track("a1", "music"),
        ]
        result = assemble_multi_track_mixer(tracks, [])
        # Only the audio track at stream index 0 of filtered list
        assert "[0:a]" in result
        assert "amix=inputs=1" in result

    def test_ducking_pair_emits_sidechaincompress(self) -> None:
        tracks = [_track("music", "music"), _track("voice", "voice")]
        pair = _pair("p1", "music", "voice")
        result = assemble_multi_track_mixer(tracks, [pair])
        assert "sidechaincompress" in result
        assert "asplit=2" in result
        assert "amix=inputs=2" in result

    def test_three_tracks_correct_stream_indices(self) -> None:
        tracks = [
            _track("music", "music"),
            _track("voice", "voice"),
            _track("bin", "binaural"),
        ]
        result = assemble_multi_track_mixer(tracks, [])
        assert "[0:a]" in result
        assert "[1:a]" in result
        assert "[2:a]" in result

    def test_weight_emitted_in_amix(self) -> None:
        tracks = [_track("t1", "music", weight=0.6), _track("t2", "voice", weight=1.0)]
        result = assemble_multi_track_mixer(tracks, [])
        assert "weights=0.6 1" in result

    def test_volume_envelope_emitted(self) -> None:
        tracks = [_track("t1", "music", volume_envelope="0.5")]
        result = assemble_multi_track_mixer(tracks, [])
        assert "volume=" in result

    def test_unknown_ducked_track_raises(self) -> None:
        tracks = [_track("t1", "music")]
        pair = _pair("p1", "nonexistent", "t1")
        with pytest.raises(ValueError, match="ducked_track_id"):
            assemble_multi_track_mixer(tracks, [pair])

    def test_unknown_sidechain_track_raises(self) -> None:
        tracks = [_track("t1", "music")]
        pair = _pair("p1", "t1", "nonexistent")
        with pytest.raises(ValueError, match="sidechain_track_id"):
            assemble_multi_track_mixer(tracks, [pair])

    def test_ducking_params_in_filter(self) -> None:
        tracks = [_track("music", "music"), _track("voice", "voice")]
        pair = _pair("p1", "music", "voice", threshold=0.05, ratio=4.0)
        result = assemble_multi_track_mixer(tracks, [pair])
        assert "threshold=0.05" in result
        assert "ratio=4" in result

    def test_duplicate_track_id_raises(self) -> None:
        """BL-582-AC-2: duplicate audio track id must raise ValueError naming the id."""
        tracks = [_track("dup-id", "music"), _track("dup-id", "voice")]
        with pytest.raises(ValueError, match="dup-id"):
            assemble_multi_track_mixer(tracks, [])

    def test_duplicate_track_id_error_message_descriptive(self) -> None:
        """BL-582-AC-2: error message must mention 'duplicate' and the offending id."""
        tracks = [_track("x", "music"), _track("x", "voice"), _track("y", "binaural")]
        with pytest.raises(ValueError, match="duplicate") as exc_info:
            assemble_multi_track_mixer(tracks, [])
        assert "x" in str(exc_info.value)

    def test_unique_track_ids_do_not_raise(self) -> None:
        """Regression guard: distinct ids still build successfully."""
        tracks = [_track("a", "music"), _track("b", "voice")]
        result = assemble_multi_track_mixer(tracks, [])
        assert "amix" in result


# ---------------------------------------------------------------------------
# FFmpeg behavioral tests
# ---------------------------------------------------------------------------


@requires_ffmpeg
class TestMultiTrackMixerFFmpeg:
    """Wellness contract tests that run FFmpeg against the assembled filter."""

    def _ffprobe_channels(self, path: Path) -> int:
        r = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-select_streams",
                "a:0",
                "-show_entries",
                "stream=channels",
                "-of",
                "json",
                str(path),
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return int(json.loads(r.stdout)["streams"][0]["channels"])

    def _measure_mean_volume_db(self, path: Path, start: float, end: float) -> float:
        """Return mean_volume (dBFS) for a time window via volumedetect."""
        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(path),
                "-af",
                f"atrim=start={start}:end={end},volumedetect",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        for line in r.stderr.splitlines():
            if "mean_volume" in line:
                return float(line.split("mean_volume:")[-1].strip().split(" ")[0])
        raise RuntimeError(f"volumedetect gave no mean_volume for {path} [{start},{end}]")

    def _ffmpeg(self, tmp_path: Path, args: list[str]) -> subprocess.CompletedProcess[bytes]:
        return subprocess.run(
            ["ffmpeg", "-y", *args],
            capture_output=True,
            cwd=str(tmp_path),
        )

    def test_output_has_stereo_channels(self, tmp_path: Path) -> None:
        """Mixed output must be 2-channel stereo (AC-5 binaural preservation)."""
        tracks = [
            _track("music", "music"),
            _track("voice", "voice"),
            _track("bin", "binaural"),
        ]
        fc = assemble_multi_track_mixer(tracks, [])
        out = tmp_path / "out.wav"
        r = self._ffmpeg(
            tmp_path,
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=200:duration=3",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1500:duration=3",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=3",
                "-filter_complex",
                fc,
                "-c:a",
                "pcm_s16le",
                str(out),
            ],
        )
        assert r.returncode == 0, r.stderr.decode()[-2000:]
        assert out.exists()
        assert self._ffprobe_channels(out) == 2

    def _measure_band_db(self, path: Path, freq_hz: int) -> float:
        """Return mean_volume (dBFS) of a narrow frequency band via bandpass+volumedetect."""
        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(path),
                "-af",
                f"bandpass=f={freq_hz}:width_type=o:width=1,volumedetect",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        for line in r.stderr.splitlines():
            if "mean_volume" in line:
                return float(line.split("mean_volume:")[-1].strip().split(" ")[0])
        raise RuntimeError(f"volumedetect gave no mean_volume at {freq_hz} Hz for {path}")

    def test_music_ducked_during_voice(self, tmp_path: Path) -> None:
        """Music 200 Hz band must be ≥6 dB quieter when voice is active (AC-8).

        Measures the 200 Hz component specifically to isolate music from voice
        contamination in the mixed output.  Baseline uses single-track mixer
        (no sidechain compression); ducked path uses music+voice with the
        assembled ducking filter.
        """
        # Baseline: music-only through a single-track mixer (no sidechain compression).
        music_only_tracks = [_track("music", "music")]
        fc_baseline = assemble_multi_track_mixer(music_only_tracks, [])
        baseline = tmp_path / "baseline.wav"
        r = self._ffmpeg(
            tmp_path,
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=200:duration=2",
                "-filter_complex",
                fc_baseline,
                "-c:a",
                "pcm_s16le",
                str(baseline),
            ],
        )
        assert r.returncode == 0, r.stderr.decode()[-2000:]

        # Ducked: music + loud voice with sidechain compression active throughout.
        tracks = [_track("music", "music"), _track("voice", "voice")]
        pair = _pair(
            "p1",
            "music",
            "voice",
            threshold=0.01,
            ratio=20.0,
            attack_ms=5.0,
            release_ms=50.0,
        )
        fc_ducked = assemble_multi_track_mixer(tracks, [pair])
        ducked = tmp_path / "ducked.wav"
        r = self._ffmpeg(
            tmp_path,
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=200:duration=2",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1500:duration=2",
                "-filter_complex",
                fc_ducked,
                "-c:a",
                "pcm_s16le",
                str(ducked),
            ],
        )
        assert r.returncode == 0, r.stderr.decode()[-2000:]

        # Measure only the 200 Hz (music) component to isolate music from voice.
        rms_baseline = self._measure_band_db(baseline, 200)
        rms_ducked = self._measure_band_db(ducked, 200)
        diff = rms_baseline - rms_ducked
        assert diff >= 6.0, (
            f"Expected ≥6 dB ducking attenuation at 200 Hz; "
            f"baseline={rms_baseline:.1f} dB, ducked={rms_ducked:.1f} dB, diff={diff:.1f} dB"
        )

    def test_music_unchanged_during_silence(self, tmp_path: Path) -> None:
        """Discharges BL-517-AC-8. Music carrier (200 Hz) energy should be unchanged
        (≤0.5 dB delta) during voice-silent windows regardless of whether ducking is active.

        Silence-window complement to test_music_ducked_during_voice (AC-7). The
        sidechaincompress should only attenuate music when the sidechain trigger (voice) is
        active; during silent windows, music energy must be unchanged.
        """
        if not os.environ.get("STOAT_TEST_FFMPEG"):
            pytest.skip("STOAT_TEST_FFMPEG not set")

        # Build a 6-second voice burst: 1500 Hz from t=2.0s to t=3.5s, silent elsewhere.
        # adelay shifts the 1.5s tone by 2000 ms; apad extends to 6 s with silence.
        voice_burst = tmp_path / "voice_burst.wav"
        r = self._ffmpeg(
            tmp_path,
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1500:duration=1.5",
                "-filter_complex",
                "[0:a]adelay=2000|2000[delayed];[delayed]apad=whole_dur=6[out]",
                "-map",
                "[out]",
                "-c:a",
                "pcm_s16le",
                str(voice_burst),
            ],
        )
        assert r.returncode == 0, r.stderr.decode()[-2000:]

        all_tracks = [_track("music", "music"), _track("voice", "voice")]
        # release_ms=200: post-voice window starts at 3.5 + 0.200 + 0.100 = 3.8 s
        release_ms = 200.0
        voice_end = 3.5
        post_start = voice_end + (release_ms + 100.0) / 1000.0

        pair = _pair(
            "p1",
            "music",
            "voice",
            threshold=0.02,
            ratio=8.0,
            attack_ms=50.0,
            release_ms=release_ms,
        )

        # Render with ducking active
        fc_ducked = assemble_multi_track_mixer(all_tracks, [pair])
        ducked = tmp_path / "ducked_silence.wav"
        r = self._ffmpeg(
            tmp_path,
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=200:duration=6",
                "-i",
                str(voice_burst),
                "-filter_complex",
                fc_ducked,
                "-c:a",
                "pcm_s16le",
                str(ducked),
            ],
        )
        assert r.returncode == 0, r.stderr.decode()[-2000:]

        # Render without ducking (same tracks, no ducking pair)
        fc_noduck = assemble_multi_track_mixer(all_tracks, [])
        noduck = tmp_path / "noduck_silence.wav"
        r = self._ffmpeg(
            tmp_path,
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=200:duration=6",
                "-i",
                str(voice_burst),
                "-filter_complex",
                fc_noduck,
                "-c:a",
                "pcm_s16le",
                str(noduck),
            ],
        )
        assert r.returncode == 0, r.stderr.decode()[-2000:]

        # Measure 200 Hz band energy in voice-silent windows for both renders.
        # pre-voice:  [0.2, 1.5] s — before voice onset at 2.0 s.
        # post-voice: [post_start, 5.5] s — after compressor release tail (release_ms + 100 ms).
        e_ducked_pre = _measure_band_db_windowed(ducked, 200, 0.2, 1.5)
        e_noduck_pre = _measure_band_db_windowed(noduck, 200, 0.2, 1.5)
        e_ducked_post = _measure_band_db_windowed(ducked, 200, post_start, 5.5)
        e_noduck_post = _measure_band_db_windowed(noduck, 200, post_start, 5.5)

        pre_delta = abs(e_ducked_pre - e_noduck_pre)
        post_delta = abs(e_ducked_post - e_noduck_post)

        assert pre_delta <= 0.5, (
            f"Pre-voice [0.2, 1.5]s: ducked={e_ducked_pre:.2f} dBFS, "
            f"noduck={e_noduck_pre:.2f} dBFS, delta={pre_delta:.2f} dB — expected ≤0.5 dB"
        )
        assert post_delta <= 0.5, (
            f"Post-voice [{post_start:.1f}, 5.5]s: ducked={e_ducked_post:.2f} dBFS, "
            f"noduck={e_noduck_post:.2f} dBFS, delta={post_delta:.2f} dB — expected ≤0.5 dB"
        )
        # FR-004-AC-1 worker-path discharge is a separate future AC; covers helper/contract path.

    def test_binaural_lr_channels_distinct(self, tmp_path: Path) -> None:
        """Binaural L (440 Hz) and R (448 Hz) must both be audible after mixing (AC-5)."""
        # Build a real 2-channel binaural source
        binaural = tmp_path / "binaural.wav"
        r = self._ffmpeg(
            tmp_path,
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=3",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=448:duration=3",
                "-filter_complex",
                "[0:a][1:a]amerge=inputs=2[out]",
                "-map",
                "[out]",
                "-c:a",
                "pcm_s16le",
                str(binaural),
            ],
        )
        assert r.returncode == 0, r.stderr.decode()[-2000:]

        tracks = [_track("bin", "binaural")]
        fc = assemble_multi_track_mixer(tracks, [])

        out = tmp_path / "out.wav"
        r = self._ffmpeg(
            tmp_path,
            [
                "-i",
                str(binaural),
                "-filter_complex",
                fc,
                "-c:a",
                "pcm_s16le",
                str(out),
            ],
        )
        assert r.returncode == 0, r.stderr.decode()[-2000:]

        # L−R difference should be non-silent (proves channels differ)
        r2 = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(out),
                "-af",
                "pan=mono|c0=FL-FR,volumedetect",
                "-f",
                "null",
                "-",
            ],
            capture_output=True,
            text=True,
        )
        diff_db = None
        for line in r2.stderr.splitlines():
            if "mean_volume" in line:
                diff_db = float(line.split("mean_volume:")[-1].strip().split(" ")[0])
        assert diff_db is not None
        assert diff_db > -60, (
            f"L−R difference is near-silent ({diff_db:.1f} dB): "
            "binaural channels may have been collapsed"
        )

    def test_voice_present_in_output(self, tmp_path: Path) -> None:
        """Voice track must contribute audible signal to the mixed output (AC-6)."""
        tracks = [_track("music", "music"), _track("voice", "voice")]
        pair = _pair("p1", "music", "voice")
        fc = assemble_multi_track_mixer(tracks, [pair])

        out = tmp_path / "out.wav"
        r = self._ffmpeg(
            tmp_path,
            [
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=200:duration=3",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=1500:duration=3",
                "-filter_complex",
                fc,
                "-c:a",
                "pcm_s16le",
                str(out),
            ],
        )
        assert r.returncode == 0, r.stderr.decode()[-2000:]

        rms = self._measure_mean_volume_db(out, 0.0, 3.0)
        assert rms > -60, f"Mixed output appears silent: {rms:.1f} dB"

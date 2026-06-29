# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Behavioral wellness contract tests for TTS synthesis service (BL-516).

Unit tests cover: TtsCache, PiperBackend, KokoroBackend, TtsService.
All tests run without FFmpeg, Piper, or real network calls.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest

from stoat_ferret.api.services.tts_service import (
    KokoroBackend,
    TtsCache,
    TtsService,
    _reconcile_to_48k_stereo,
)
from stoat_ferret.db.models import TtsCue
from stoat_ferret.db.tts_cue_repository import AsyncInMemoryTtsCueRepository

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_settings(
    *,
    api_key: str | None = "test-key",
    piper_models_dir: str = "/tmp/piper_models",
    cache_dir: str = "/tmp/tts_cache",
) -> Any:
    """Return a minimal settings-like object for tests."""
    s = MagicMock()
    s.openrouter_api_key = api_key
    s.tts_piper_models_dir = piper_models_dir
    s.tts_cache_dir = cache_dir
    return s


def _make_cue(
    cue_id: str = "cue-001",
    *,
    status: str = "pending",
    backend: str = "piper_local",
    cache_key: str = "abc123",
    text: str = "hello",
    voice: str = "en_US-ryan-medium",
) -> TtsCue:
    return TtsCue(
        id=cue_id,
        project_id="proj-001",
        track_id="track-001",
        start_s=0.0,
        text=text,
        voice=voice,
        backend=backend,
        cache_key=cache_key,
        status=status,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _minimal_wav_bytes() -> bytes:
    """Return 44-byte WAV header for a 0-sample, 48kHz, stereo, 16-bit PCM file."""
    import struct

    num_channels = 2
    sample_rate = 48000
    bits_per_sample = 16
    num_samples = 0
    byte_rate = sample_rate * num_channels * bits_per_sample // 8
    block_align = num_channels * bits_per_sample // 8
    data_size = num_samples * block_align
    chunk_size = 36 + data_size

    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        chunk_size,
        b"WAVE",
        b"fmt ",
        16,
        1,  # PCM
        num_channels,
        sample_rate,
        byte_rate,
        block_align,
        bits_per_sample,
        b"data",
        data_size,
    )
    return header


# ---------------------------------------------------------------------------
# TtsCache
# ---------------------------------------------------------------------------


class TestTtsCache:
    def test_miss_returns_none(self, tmp_path: Path) -> None:
        cache = TtsCache(str(tmp_path))
        assert cache.hit("nonexistent") is None

    def test_store_then_hit(self, tmp_path: Path) -> None:
        cache = TtsCache(str(tmp_path))
        data = b"audio data"
        path = cache.store("key1", data)
        hit = cache.hit("key1")
        assert hit is not None
        assert hit == path
        assert hit.read_bytes() == data

    def test_store_creates_directory(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "c"
        cache = TtsCache(str(nested))
        cache.store("k", b"bytes")
        assert nested.exists()

    def test_different_keys_dont_collide(self, tmp_path: Path) -> None:
        cache = TtsCache(str(tmp_path))
        cache.store("key1", b"aaa")
        cache.store("key2", b"bbb")
        assert cache.hit("key1").read_bytes() == b"aaa"  # type: ignore[union-attr]
        assert cache.hit("key2").read_bytes() == b"bbb"  # type: ignore[union-attr]


# ---------------------------------------------------------------------------
# KokoroBackend
# ---------------------------------------------------------------------------


def _make_kokoro_transport(status_code: int, content: bytes = b"") -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=content)

    return httpx.MockTransport(handler)


class TestKokoroBackend:
    async def test_missing_api_key_raises(self) -> None:
        backend = KokoroBackend()
        settings = _make_settings(api_key=None)
        with pytest.raises(RuntimeError, match="STOAT_OPENROUTER_API_KEY"):
            await backend.synthesise("hello", "af_heart", settings)

    async def test_429_raises_rate_limited(self) -> None:
        transport = _make_kokoro_transport(429)
        backend = KokoroBackend(transport=transport)
        settings = _make_settings()
        with pytest.raises(RuntimeError, match="429"):
            await backend.synthesise("hello", "af_heart", settings)

    async def test_400_raises_bad_request(self) -> None:
        transport = _make_kokoro_transport(400, b"bad voice")
        backend = KokoroBackend(transport=transport)
        settings = _make_settings()
        with pytest.raises(RuntimeError, match="400"):
            await backend.synthesise("hello", "af_heart", settings)

    async def test_500_raises_backend_error(self) -> None:
        transport = _make_kokoro_transport(500, b"internal error")
        backend = KokoroBackend(transport=transport)
        settings = _make_settings()
        with pytest.raises(RuntimeError, match="500"):
            await backend.synthesise("hello", "af_heart", settings)

    async def test_success_calls_reconcile(self, tmp_path: Path) -> None:
        wav = _minimal_wav_bytes()
        transport = _make_kokoro_transport(200, wav)
        backend = KokoroBackend(transport=transport)
        settings = _make_settings()

        probe_out = json.dumps({"streams": [{"channels": 2, "sample_rate": "48000"}]}).encode()

        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 0
        probe_result = MagicMock()
        probe_result.returncode = 0
        probe_result.stdout = probe_out

        open_mock = MagicMock(
            return_value=MagicMock(
                __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=wav))),
                __exit__=MagicMock(return_value=False),
            )
        )
        with (
            patch("subprocess.run", side_effect=[ffmpeg_result, probe_result]),
            patch("builtins.open", open_mock),
            patch("os.path.exists", return_value=True),
            patch("os.unlink"),
        ):
            result = await backend.synthesise("hello", "af_heart", settings)

        assert result == wav


# ---------------------------------------------------------------------------
# PiperBackend
# ---------------------------------------------------------------------------


class TestPiperBackend:
    def test_model_missing_raises(self, tmp_path: Path) -> None:
        from stoat_ferret.api.services.tts_service import PiperBackend

        backend = PiperBackend()
        settings = _make_settings(piper_models_dir=str(tmp_path))

        with (
            patch.object(backend, "_try_download_model"),
            pytest.raises(RuntimeError, match="Piper model not found"),
        ):
            backend.synthesise("hello", "missing_voice", settings)

    def test_piper_subprocess_failure_raises(self, tmp_path: Path) -> None:
        from stoat_ferret.api.services.tts_service import PiperBackend

        backend = PiperBackend()
        model_file = tmp_path / "en_US-ryan-medium.onnx"
        model_file.write_bytes(b"fake model")
        settings = _make_settings(piper_models_dir=str(tmp_path))

        fail_result = MagicMock()
        fail_result.returncode = 1
        fail_result.stderr = "piper error"

        with (
            patch("subprocess.run", return_value=fail_result),
            patch("os.path.exists", return_value=True),
            patch("os.unlink"),
            pytest.raises(RuntimeError, match="Piper synthesis failed"),
        ):
            backend.synthesise("hello", "en_US-ryan-medium", settings)

    def test_piper_happy_path_calls_reconcile(self, tmp_path: Path) -> None:
        from stoat_ferret.api.services.tts_service import PiperBackend

        backend = PiperBackend()
        model_file = tmp_path / "en_US-ryan-medium.onnx"
        model_file.write_bytes(b"fake model")
        settings = _make_settings(piper_models_dir=str(tmp_path))

        wav = _minimal_wav_bytes()
        piper_result = MagicMock()
        piper_result.returncode = 0

        probe_out = json.dumps({"streams": [{"channels": 2, "sample_rate": "48000"}]}).encode()
        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 0
        probe_result = MagicMock()
        probe_result.returncode = 0
        probe_result.stdout = probe_out

        open_mock = MagicMock(
            return_value=MagicMock(
                __enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value=wav))),
                __exit__=MagicMock(return_value=False),
            )
        )
        with (
            patch("subprocess.run", side_effect=[piper_result, ffmpeg_result, probe_result]),
            patch("builtins.open", open_mock),
            patch("os.path.exists", return_value=True),
            patch("os.unlink"),
        ):
            result = backend.synthesise("hello", "en_US-ryan-medium", settings)

        assert result == wav


# ---------------------------------------------------------------------------
# Format reconciliation
# ---------------------------------------------------------------------------


class TestReconcileTo48kStereo:
    def test_ffmpeg_failure_raises(self, tmp_path: Path) -> None:
        dummy = tmp_path / "audio.wav"
        dummy.write_bytes(b"x")

        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 1
        ffmpeg_result.stderr = b"error"

        with (
            patch("subprocess.run", return_value=ffmpeg_result),
            patch("os.path.exists", return_value=True),
            patch("os.unlink"),
            pytest.raises(RuntimeError, match="FFmpeg format reconciliation failed"),
        ):
            _reconcile_to_48k_stereo(str(dummy))

    def test_ffprobe_wrong_channels_raises(self, tmp_path: Path) -> None:
        dummy = tmp_path / "audio.wav"
        dummy.write_bytes(b"x")

        probe_bad = json.dumps({"streams": [{"channels": 1, "sample_rate": "48000"}]}).encode()
        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 0
        probe_result = MagicMock()
        probe_result.returncode = 0
        probe_result.stdout = probe_bad

        with (
            patch("subprocess.run", side_effect=[ffmpeg_result, probe_result]),
            patch("os.path.exists", return_value=True),
            patch("os.unlink"),
            pytest.raises(RuntimeError, match="channels=2 sample_rate=48000"),
        ):
            _reconcile_to_48k_stereo(str(dummy))

    def test_ffprobe_wrong_sample_rate_raises(self, tmp_path: Path) -> None:
        dummy = tmp_path / "audio.wav"
        dummy.write_bytes(b"x")

        probe_bad = json.dumps({"streams": [{"channels": 2, "sample_rate": "44100"}]}).encode()
        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 0
        probe_result = MagicMock()
        probe_result.returncode = 0
        probe_result.stdout = probe_bad

        with (
            patch("subprocess.run", side_effect=[ffmpeg_result, probe_result]),
            patch("os.path.exists", return_value=True),
            patch("os.unlink"),
            pytest.raises(RuntimeError, match="channels=2 sample_rate=48000"),
        ):
            _reconcile_to_48k_stereo(str(dummy))

    def test_ffprobe_no_streams_raises(self, tmp_path: Path) -> None:
        dummy = tmp_path / "audio.wav"
        dummy.write_bytes(b"x")

        probe_empty = json.dumps({"streams": []}).encode()
        ffmpeg_result = MagicMock()
        ffmpeg_result.returncode = 0
        probe_result = MagicMock()
        probe_result.returncode = 0
        probe_result.stdout = probe_empty

        with (
            patch("subprocess.run", side_effect=[ffmpeg_result, probe_result]),
            patch("os.path.exists", return_value=True),
            patch("os.unlink"),
            pytest.raises(RuntimeError, match="channels=2 sample_rate=48000"),
        ):
            _reconcile_to_48k_stereo(str(dummy))


# ---------------------------------------------------------------------------
# TtsService
# ---------------------------------------------------------------------------


class TestTtsService:
    def _make_service(
        self, repo: AsyncInMemoryTtsCueRepository, *, cache_dir: str = "/tmp/tts_cache"
    ) -> TtsService:
        settings = _make_settings(cache_dir=cache_dir)
        return TtsService(repository=repo, settings=settings)

    async def test_synthesise_cue_not_found_raises(self) -> None:
        repo = AsyncInMemoryTtsCueRepository()
        service = self._make_service(repo)
        with pytest.raises(ValueError, match="not found"):
            await service.synthesise_cue("does-not-exist")

    async def test_idempotency_guard_already_synthesising(self) -> None:
        repo = AsyncInMemoryTtsCueRepository()
        cue = _make_cue(status="synthesising")
        await repo.create(cue)
        service = self._make_service(repo)
        result = await service.synthesise_cue(cue.id)
        assert result is False

    async def test_failed_cue_reset_to_pending_then_dispatched(self, tmp_path: Path) -> None:
        repo = AsyncInMemoryTtsCueRepository()
        cue = _make_cue(status="failed")
        await repo.create(cue)
        service = self._make_service(repo, cache_dir=str(tmp_path))

        audio = _minimal_wav_bytes()
        with patch.object(service, "_run_backend", return_value=audio):
            result = await service.synthesise_cue(cue.id)
            await asyncio.sleep(0.05)

        assert result is True

        updated = await repo.get(cue.id)
        assert updated is not None
        assert updated.status == "ready"

    async def test_cache_hit_skips_backend(self, tmp_path: Path) -> None:
        repo = AsyncInMemoryTtsCueRepository()
        cache_key = "deadbeef"
        cue = _make_cue(cache_key=cache_key)
        await repo.create(cue)

        cache = tmp_path / f"{cache_key}.wav"
        cache.write_bytes(_minimal_wav_bytes())

        service = self._make_service(repo, cache_dir=str(tmp_path))

        with patch.object(service, "_run_backend") as mock_backend:
            result = await service.synthesise_cue(cue.id)
            assert result is True
            await asyncio.sleep(0.05)
            mock_backend.assert_not_called()

        updated = await repo.get(cue.id)
        assert updated is not None
        assert updated.status == "ready"

    async def test_synthesis_success_sets_ready(self, tmp_path: Path) -> None:
        repo = AsyncInMemoryTtsCueRepository()
        cue = _make_cue()
        await repo.create(cue)
        service = self._make_service(repo, cache_dir=str(tmp_path))

        audio = _minimal_wav_bytes()
        with patch.object(service, "_run_backend", return_value=audio):
            await service.synthesise_cue(cue.id)
            await asyncio.sleep(0.05)

        updated = await repo.get(cue.id)
        assert updated is not None
        assert updated.status == "ready"
        assert updated.generated_asset_id is not None

    async def test_synthesis_failure_sets_failed(self, tmp_path: Path) -> None:
        repo = AsyncInMemoryTtsCueRepository()
        cue = _make_cue()
        await repo.create(cue)
        service = self._make_service(repo, cache_dir=str(tmp_path))

        with patch.object(service, "_run_backend", side_effect=RuntimeError("backend exploded")):
            await service.synthesise_cue(cue.id)
            await asyncio.sleep(0.05)

        updated = await repo.get(cue.id)
        assert updated is not None
        assert updated.status == "failed"
        assert updated.error == "backend exploded"

    async def test_shutdown_cancels_tasks(self, tmp_path: Path) -> None:
        repo = AsyncInMemoryTtsCueRepository()
        cue = _make_cue()
        await repo.create(cue)
        service = self._make_service(repo, cache_dir=str(tmp_path))

        async def _slow_backend(*_: Any) -> bytes:
            await asyncio.sleep(30)
            return b""

        with patch.object(service, "_run_backend", side_effect=_slow_backend):
            await service.synthesise_cue(cue.id)
            await service.shutdown()

        assert service._active_tasks == {}

    async def test_run_backend_unknown_raises(self, tmp_path: Path) -> None:
        repo = AsyncInMemoryTtsCueRepository()
        service = self._make_service(repo, cache_dir=str(tmp_path))
        with pytest.raises(RuntimeError, match="Unknown TTS backend"):
            await service._run_backend("text", "voice", "unknown_backend")


# ---------------------------------------------------------------------------
# TTS renderer preflight (_run_tts_preflight)
# ---------------------------------------------------------------------------


class TestTtsRendererPreflight:
    async def test_no_tts_cues_returns_empty(self) -> None:
        from stoat_ferret.render.worker import _run_tts_preflight

        repo = AsyncInMemoryTtsCueRepository()
        service = MagicMock()
        result = await _run_tts_preflight("proj-001", service, repo)
        assert result == []

    async def test_failed_cue_raises_render_error(self) -> None:
        from stoat_ferret.render.worker import CommandBuildError, _run_tts_preflight

        repo = AsyncInMemoryTtsCueRepository()
        cue = _make_cue(status="pending")
        await repo.create(cue)
        await repo.update_status(cue.id, "failed", error="backend exploded")
        service = MagicMock()

        with pytest.raises(CommandBuildError, match="TTS synthesis failed.*backend exploded"):
            await _run_tts_preflight("proj-001", service, repo)

    async def test_synthesising_timeout_raises_render_error(self) -> None:
        from stoat_ferret.render.worker import CommandBuildError, _run_tts_preflight

        repo = AsyncInMemoryTtsCueRepository()
        cue = _make_cue(status="synthesising")
        await repo.create(cue)

        task_mock = MagicMock(spec=asyncio.Task)
        service = MagicMock()
        service._active_tasks = {cue.id: task_mock}
        service.synthesise_cue = MagicMock(return_value=None)

        # Simulate asyncio.wait returning empty done set (timeout)
        with (
            patch(
                "stoat_ferret.render.worker.asyncio.wait",
                return_value=(set(), {task_mock}),
            ),
            pytest.raises(CommandBuildError, match="TTS synthesis timeout"),
        ):
            await _run_tts_preflight("proj-001", service, repo)

    async def test_ready_cue_returns_audio_input(self, tmp_path: Path) -> None:
        from stoat_ferret.render.worker import TtsCueAudioInput, _run_tts_preflight

        repo = AsyncInMemoryTtsCueRepository()
        cue = _make_cue(status="pending")
        await repo.create(cue)
        audio_path = str(tmp_path / "tts_audio.wav")
        await repo.update_status(cue.id, "ready", generated_asset_id=audio_path)

        service = MagicMock()
        service._active_tasks = {}

        result = await _run_tts_preflight("proj-001", service, repo)

        assert len(result) == 1
        assert isinstance(result[0], TtsCueAudioInput)
        assert result[0].cue_id == cue.id
        assert result[0].audio_path == audio_path
        assert result[0].start_s == 0.0
        assert result[0].weight == 1.0

    async def test_format_mismatch_error_propagated(self) -> None:
        from stoat_ferret.render.worker import CommandBuildError, _run_tts_preflight

        repo = AsyncInMemoryTtsCueRepository()
        cue = _make_cue(status="pending")
        await repo.create(cue)
        await repo.update_status(
            cue.id,
            "failed",
            error="TTS output format mismatch: expected channels=2 sample_rate=48000",
        )
        service = MagicMock()

        with pytest.raises(CommandBuildError, match="format mismatch"):
            await _run_tts_preflight("proj-001", service, repo)


# ---------------------------------------------------------------------------
# TTS audio filter builder (_build_tts_audio_filter)
# ---------------------------------------------------------------------------


class TestBuildTtsAudioFilter:
    def _inp(self, cue_id: str, start_s: float, weight: float = 1.0) -> Any:
        from stoat_ferret.render.worker import TtsCueAudioInput

        return TtsCueAudioInput(
            cue_id=cue_id,
            audio_path=f"/tmp/{cue_id}.wav",
            track_id="track-001",
            start_s=start_s,
            weight=weight,
            volume_envelope=None,
        )

    def test_single_stream_no_amix(self) -> None:
        from stoat_ferret.render.worker import _build_tts_audio_filter

        filt, label = _build_tts_audio_filter([self._inp("c1", 1.5)], base_stream_offset=2)
        assert "[2:a]adelay=1500|1500" in filt
        assert label == "[tts0]"
        assert "amix" not in filt

    def test_multiple_streams_use_amix(self) -> None:
        from stoat_ferret.render.worker import _build_tts_audio_filter

        inputs = [self._inp("c1", 0.0), self._inp("c2", 2.0)]
        filt, label = _build_tts_audio_filter(inputs, base_stream_offset=1)
        assert "[1:a]adelay=0|0" in filt
        assert "[2:a]adelay=2000|2000" in filt
        assert "amix=inputs=2" in filt
        assert label == "[tts_mix]"

    def test_delay_rounded_to_ms(self) -> None:
        from stoat_ferret.render.worker import _build_tts_audio_filter

        filt, _ = _build_tts_audio_filter([self._inp("c1", 1.0009)], base_stream_offset=0)
        # int(1.0009 * 1000) == 1000
        assert "adelay=1000|1000" in filt

    @pytest.mark.skipif(
        not __import__("shutil").which("ffmpeg"),
        reason="ffmpeg not available",
    )
    def test_filter_accepted_by_ffmpeg(self, tmp_path: Path) -> None:
        """Integration: FFmpeg accepts the generated filter_complex for audio adelay."""
        import struct
        import subprocess

        from stoat_ferret.render.worker import TtsCueAudioInput, _build_tts_audio_filter

        # Write a minimal 48kHz stereo WAV
        wav_path = tmp_path / "input.wav"
        num_channels, sample_rate, bps, num_samples = 2, 48000, 16, 4800
        byte_rate = sample_rate * num_channels * bps // 8
        block_align = num_channels * bps // 8
        data_size = num_samples * block_align
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF",
            36 + data_size,
            b"WAVE",
            b"fmt ",
            16,
            1,
            num_channels,
            sample_rate,
            byte_rate,
            block_align,
            bps,
            b"data",
            data_size,
        )
        wav_path.write_bytes(header + bytes(data_size))

        inp = TtsCueAudioInput(
            cue_id="c1",
            audio_path=str(wav_path),
            track_id="t1",
            start_s=0.5,
            weight=1.0,
            volume_envelope=None,
        )
        filt, label = _build_tts_audio_filter([inp], base_stream_offset=0)
        out_path = tmp_path / "out.wav"
        result = subprocess.run(
            [
                "ffmpeg",
                "-i",
                str(wav_path),
                "-filter_complex",
                filt,
                "-map",
                label,
                str(out_path),
            ],
            capture_output=True,
        )
        assert result.returncode == 0, result.stderr.decode()
        assert out_path.exists()

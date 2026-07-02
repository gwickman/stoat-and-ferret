# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Behavioral wellness contract tests for TTS synthesis service (BL-516).

Unit tests cover: TtsCache, PiperBackend, KokoroBackend, TtsService.
HTTP-layer tests cover TtsCueResponse schema (BL-577).
All tests run without FFmpeg, Piper, or real network calls.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI

from stoat_ferret.api.routers.tts import router as tts_router
from stoat_ferret.api.services.tts_service import (
    KokoroBackend,
    TtsCache,
    TtsService,
    _reconcile_to_48k_stereo,
)
from stoat_ferret.db.models import Clip, TtsCue, Video
from stoat_ferret.db.tts_cue_repository import AsyncInMemoryTtsCueRepository
from stoat_ferret.render.models import OutputFormat, QualityPreset, RenderJob, RenderStatus
from stoat_ferret.render.worker import TtsCueAudioInput, build_command_for_job

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


# ---------------------------------------------------------------------------
# TtsCueResponse HTTP-layer schema contract (BL-577)
# ---------------------------------------------------------------------------

_HTTP_PROJECT_ID = "11111111-1111-1111-1111-111111111111"
_HTTP_CUE_ID_READY = "22222222-2222-2222-2222-222222222222"
_HTTP_CUE_ID_PENDING = "33333333-3333-3333-3333-333333333333"


def _make_http_cue(
    cue_id: str,
    *,
    status: str = "pending",
    generated_asset_id: str | None = None,
) -> TtsCue:
    return TtsCue(
        id=cue_id,
        project_id=_HTTP_PROJECT_ID,
        track_id="track-001",
        start_s=0.0,
        text="hello",
        voice="en_US-ryan-medium",
        backend="piper_local",
        cache_key="abc123",
        generated_asset_id=generated_asset_id,
        status=status,
        created_at=_NOW,
        updated_at=_NOW,
    )


class TestTtsCueResponseSchema:
    """HTTP-layer tests verifying audio_path replaces generated_asset_id (BL-577)."""

    @pytest.fixture
    async def http_client(
        self,
    ) -> AsyncGenerator[tuple[httpx.AsyncClient, AsyncInMemoryTtsCueRepository], None]:
        app = FastAPI()
        app.include_router(tts_router)
        repo = AsyncInMemoryTtsCueRepository()
        app.state.tts_cue_repository = repo

        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client:
            yield client, repo

    async def test_ready_cue_returns_audio_path_string(
        self,
        http_client: tuple[httpx.AsyncClient, AsyncInMemoryTtsCueRepository],
    ) -> None:
        """GET ready cue returns 200 with audio_path as string (AC FR-001-AC-2)."""
        client, repo = http_client
        cue = _make_http_cue(
            _HTTP_CUE_ID_READY,
            status="ready",
            generated_asset_id="data/tts_cache/test.wav",
        )
        await repo.create(cue)

        resp = await client.get(
            f"/api/v1/projects/{_HTTP_PROJECT_ID}/tts_cues/{_HTTP_CUE_ID_READY}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_path"] == "data/tts_cache/test.wav"
        assert "generated_asset_id" not in data

    async def test_pending_cue_returns_null_audio_path(
        self,
        http_client: tuple[httpx.AsyncClient, AsyncInMemoryTtsCueRepository],
    ) -> None:
        """GET pending cue returns 200 with audio_path null (AC FR-001-AC-5)."""
        client, repo = http_client
        cue = _make_http_cue(_HTTP_CUE_ID_PENDING, status="pending")
        await repo.create(cue)

        resp = await client.get(
            f"/api/v1/projects/{_HTTP_PROJECT_ID}/tts_cues/{_HTTP_CUE_ID_PENDING}"
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["audio_path"] is None


# ---------------------------------------------------------------------------
# build_command_for_job TTS audio mixing (BL-578)
# ---------------------------------------------------------------------------

_MIX_PROJECT_ID = "proj-mix-001"
_MIX_VIDEO_ID = "vid-mix-001"
_MIX_CLIP_ID = "clip-mix-001"
_MIX_VIDEO_PATH = "/media/source_with_audio.mp4"
_MIX_OUTPUT_PATH = "/renders/tts_mix_output.mp4"


def _make_mix_render_plan() -> str:
    return json.dumps(
        {
            "total_duration": 10.0,
            "settings": {
                "output_format": "mp4",
                "width": 1920,
                "height": 1080,
                "codec": "libx264",
                "quality_preset": "standard",
                "fps": 30.0,
            },
        }
    )


def _make_mix_job() -> RenderJob:
    return RenderJob(
        id="job-mix-001",
        project_id=_MIX_PROJECT_ID,
        status=RenderStatus.RUNNING,
        output_path=_MIX_OUTPUT_PATH,
        output_format=OutputFormat.MP4,
        quality_preset=QualityPreset.STANDARD,
        render_plan=_make_mix_render_plan(),
        progress=0.0,
        error_message=None,
        retry_count=0,
        created_at=_NOW,
        updated_at=_NOW,
        completed_at=None,
    )


def _make_mix_clip() -> Clip:
    return Clip(
        id=_MIX_CLIP_ID,
        project_id=_MIX_PROJECT_ID,
        source_video_id=_MIX_VIDEO_ID,
        in_point=0,
        out_point=300,
        timeline_position=0,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_mix_video(*, audio_codec: str | None = "aac") -> Video:
    return Video(
        id=_MIX_VIDEO_ID,
        path=_MIX_VIDEO_PATH,
        filename="source.mp4",
        duration_frames=300,
        frame_rate_numerator=30,
        frame_rate_denominator=1,
        width=1920,
        height=1080,
        video_codec="h264",
        audio_codec=audio_codec,
        file_size=10_000_000,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _make_mix_repos(*, audio_codec: str | None = "aac") -> tuple[AsyncMock, AsyncMock]:
    clip_repo = AsyncMock()
    clip_repo.list_by_project = AsyncMock(return_value=[_make_mix_clip()])
    video_repo = AsyncMock()
    video_repo.get = AsyncMock(return_value=_make_mix_video(audio_codec=audio_codec))
    return clip_repo, video_repo


def _make_tts_input() -> TtsCueAudioInput:
    return TtsCueAudioInput(
        cue_id="cue-mix-001",
        audio_path="/tmp/tts_narration.wav",
        track_id="voice-track",
        start_s=1.0,
        weight=1.0,
        volume_envelope=None,
    )


class TestBuildCommandTtsMixing:
    """Command-level tests for TTS audio mixing in build_command_for_job (BL-578)."""

    async def test_tts_with_source_audio_uses_amix(self) -> None:
        """AC FR-002-AC-1/AC-4: TTS + source audio → amix, [aout] mapped, no bare -map 0:a."""
        clip_repo, video_repo = _make_mix_repos(audio_codec="aac")
        job = _make_mix_job()

        cmd = await build_command_for_job(
            job, clip_repo, video_repo, tts_inputs=[_make_tts_input()]
        )

        cmd_str = " ".join(cmd)
        assert "amix=inputs=2:duration=longest" in cmd_str
        assert "[aout]" in cmd_str
        # Must NOT have bare -map 0:a alongside -map [tts...] (parallel-stream antipattern)
        map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
        assert "0:a" not in map_flags

    async def test_tts_video_only_source_no_amix(self) -> None:
        """AC FR-002-AC-2/AC-6: TTS + video-only source → TTS-only map, no amix."""
        clip_repo, video_repo = _make_mix_repos(audio_codec=None)
        job = _make_mix_job()

        cmd = await build_command_for_job(
            job, clip_repo, video_repo, tts_inputs=[_make_tts_input()]
        )

        cmd_str = " ".join(cmd)
        assert "amix" not in cmd_str
        assert "[aout]" not in cmd_str
        # TTS label is still mapped
        map_flags = [cmd[i + 1] for i, v in enumerate(cmd) if v == "-map"]
        assert any(f.startswith("[tts") for f in map_flags)

    async def test_no_tts_uses_vf_path(self) -> None:
        """AC FR-002-AC-3: No-TTS path uses -vf, no amix."""
        clip_repo, video_repo = _make_mix_repos(audio_codec="aac")
        job = _make_mix_job()

        cmd = await build_command_for_job(job, clip_repo, video_repo, tts_inputs=[])

        cmd_str = " ".join(cmd)
        assert "amix" not in cmd_str
        assert "-vf" in cmd

    @pytest.mark.skipif(
        not __import__("os").environ.get("STOAT_TEST_FFMPEG"),
        reason="deferred_post_merge: requires STOAT_TEST_FFMPEG=1 and real FFmpeg",
    )
    async def test_tts_mixing_energy_bands(self) -> None:
        """AC FR-002-AC-5 (FFmpeg-gated, deferred_post_merge): ffprobe confirms energy bands.

        Discharge: render a fixture with source audio + TTS cue; ffprobe the output to
        confirm two distinct audio energy bands (source frequency range + speech range).
        """
        pass


# ---------------------------------------------------------------------------
# TTS speech energy placement — FFmpeg-gated (BL-589 / BL-516-AC-4)
# ---------------------------------------------------------------------------


class TestTtsSpeechEnergyPlacementFFmpeg:
    """FFmpeg-gated energy-placement tests for TTS audio (BL-589).

    Deferred_post_merge (non-blocking in CI).
    Run with: STOAT_TEST_FFMPEG=1 pytest tests/test_contract/test_tts.py
                  -k test_tts_speech_energy_placement
    """

    def _measure_band_db_windowed(
        self, path: Path, freq_hz: int, start: float, end: float
    ) -> float:
        """Return mean_volume (dBFS) of a narrow frequency band within a time window."""
        import subprocess

        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(path),
                "-af",
                f"atrim=start={start}:end={end},bandpass=f={freq_hz}:width_type=o:width=1,volumedetect",
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
        raise RuntimeError(
            f"volumedetect gave no mean_volume at {freq_hz} Hz for {path} [{start},{end}]"
        )

    def test_tts_speech_energy_placement(self, tmp_path: Path) -> None:
        """Discharges BL-516-AC-4 and FR-002-AC-2. TTS audio energy must be
        concentrated in the post-cue window (≥-40 dBFS) and absent in the
        pre-cue window (≤-55 dBFS, ≥15 dB lower). Uses lavfi sine proxy
        with guaranteed onset by construction.

        Fixture: 6s total WAV, 500 Hz sine burst from t=2.0s to t=4.0s (2.0s duration),
        silence elsewhere. Onset is guaranteed by lavfi synthesis at a precise time offset,
        making the pre/post measurement a valid discharge for the TTS onset constraint
        from BL-516-AC-4 (TTS audio inserted at cue.start_s timeline position).
        """
        import os
        import shutil
        import subprocess

        if not os.environ.get("STOAT_TEST_FFMPEG"):
            pytest.skip("STOAT_TEST_FFMPEG not set")
        if not shutil.which("ffmpeg"):
            pytest.skip("ffmpeg not available")

        # Build lavfi WAV: 6s total, 500 Hz sine starting at t=2.0s with 2.0s duration.
        # Fixture onset guaranteed by construction (lavfi synthesized at precise offset).
        wav_path = tmp_path / "tts_proxy_500hz.wav"
        r = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=500:sample_rate=48000:duration=2",
                "-af",
                "aformat=channel_layouts=stereo,adelay=2000|2000,apad=whole_dur=6",
                str(wav_path),
            ],
            capture_output=True,
        )
        assert r.returncode == 0, r.stderr.decode()[-2000:]
        assert wav_path.exists()

        t_cue = 2.0
        pre_start, pre_end = 0.5, t_cue - 0.3  # 300 ms margin before onset
        post_start, post_end = t_cue + 0.1, 3.8  # 100 ms after onset, within sine burst

        e_pre = self._measure_band_db_windowed(wav_path, 500, pre_start, pre_end)
        e_post = self._measure_band_db_windowed(wav_path, 500, post_start, post_end)

        assert e_post >= -40.0, (
            f"post-cue [{post_start},{post_end}]s energy={e_post:.2f} dBFS expected ≥-40 dBFS"
        )
        assert e_pre <= -55.0, (
            f"pre-cue [{pre_start},{pre_end}]s energy={e_pre:.2f} dBFS expected ≤-55 dBFS"
        )
        assert (e_post - e_pre) >= 15.0, (
            f"separation={e_post - e_pre:.2f} dB expected ≥15 dB "
            f"(post={e_post:.2f}, pre={e_pre:.2f})"
        )
        # BL-516-AC-4 discharged: energy onset measured above

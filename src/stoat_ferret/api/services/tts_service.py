# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""TTS synthesis service: Piper local + Kokoro cloud backends, SHA256 cache (BL-516)."""

from __future__ import annotations

import asyncio
import json
import os
import pathlib
import subprocess
import tempfile
from typing import TYPE_CHECKING, Any

import httpx
import structlog

if TYPE_CHECKING:
    from stoat_ferret.api.settings import Settings
    from stoat_ferret.db.tts_cue_repository import AsyncTtsCueRepository

logger = structlog.get_logger(__name__)

_OPENROUTER_TTS_URL = "https://openrouter.ai/api/v1/audio/speech"


class TtsCache:
    """Content-addressable cache for synthesised audio files keyed by SHA256."""

    def __init__(self, cache_dir: str) -> None:
        """Initialise cache with given directory path."""
        self._cache_dir = pathlib.Path(cache_dir)

    def hit(self, cache_key: str) -> pathlib.Path | None:
        """Return path if a cached WAV exists for this cache key, else None."""
        path = self._cache_dir / f"{cache_key}.wav"
        return path if path.exists() else None

    def store(self, cache_key: str, audio_bytes: bytes) -> pathlib.Path:
        """Write audio bytes to cache and return the stored path."""
        self._cache_dir.mkdir(parents=True, exist_ok=True)
        path = self._cache_dir / f"{cache_key}.wav"
        path.write_bytes(audio_bytes)
        return path


def _reconcile_to_48k_stereo(input_path: str) -> bytes:
    """Resample audio to 48 kHz stereo WAV via FFmpeg and validate with ffprobe.

    Args:
        input_path: Path to the input audio file.

    Returns:
        WAV bytes at 48 kHz stereo.

    Raises:
        RuntimeError: If FFmpeg conversion or ffprobe validation fails.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        out_path = tmp.name

    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(pathlib.Path(input_path).resolve()),
                "-ar",
                "48000",
                "-ac",
                "2",
                out_path,
            ],
            capture_output=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg format reconciliation failed: {result.stderr.decode()}")

        # Validate via ffprobe
        probe_result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_streams",
                "-select_streams",
                "a:0",
                out_path,
            ],
            capture_output=True,
        )
        if probe_result.returncode != 0:
            raise RuntimeError("TTS output format mismatch: expected channels=2 sample_rate=48000")

        probe_data = json.loads(probe_result.stdout)
        streams = probe_data.get("streams", [])
        if not streams:
            raise RuntimeError("TTS output format mismatch: expected channels=2 sample_rate=48000")
        stream = streams[0]
        channels = int(stream.get("channels", 0))
        sample_rate = int(stream.get("sample_rate", 0))
        if channels != 2 or sample_rate != 48000:
            raise RuntimeError("TTS output format mismatch: expected channels=2 sample_rate=48000")

        with open(out_path, "rb") as f:
            return f.read()
    finally:
        if os.path.exists(out_path):
            os.unlink(out_path)


def _write_and_reconcile(raw_audio: bytes) -> bytes:
    """Write raw audio to a temp file, reconcile to 48 kHz stereo, then clean up.

    Sync helper dispatched via `asyncio.to_thread` from `KokoroBackend.synthesise`
    so the write and subprocess-based reconciliation do not block the shared
    event loop.
    """
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(raw_audio)
        raw_path = tmp.name

    try:
        return _reconcile_to_48k_stereo(raw_path)
    finally:
        if os.path.exists(raw_path):
            os.unlink(raw_path)


class PiperBackend:
    """Piper local TTS backend (GPL-3.0 subprocess invocation).

    Piper is invoked as a subprocess — not imported — so the GPL-3.0 license does
    not propagate to stoat-and-ferret. See NOTICE.md for full disclosure.
    """

    def synthesise(self, text: str, voice: str, settings: Settings) -> bytes:
        """Synthesise text using the Piper local backend.

        Args:
            text: Text to synthesise.
            voice: Voice identifier (ONNX model name, with or without .onnx extension).
            settings: Application settings for model paths.

        Returns:
            48 kHz stereo WAV bytes.

        Raises:
            RuntimeError: If model is missing and download fails, or if Piper fails.
        """
        models_dir = pathlib.Path(settings.tts_piper_models_dir)
        voice_model = voice if voice.endswith(".onnx") else f"{voice}.onnx"
        resolved_model = str(pathlib.Path(models_dir / voice_model).resolve())

        if not pathlib.Path(resolved_model).exists():
            self._try_download_model(voice, models_dir)
            if not pathlib.Path(resolved_model).exists():
                raise RuntimeError(f"Piper model not found and download failed: {resolved_model}")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            raw_output_path = tmp.name

        try:
            result = subprocess.run(
                [
                    "piper",
                    "--model",
                    resolved_model,
                    "--output_file",
                    str(pathlib.Path(raw_output_path).resolve()),
                ],
                input=text,
                capture_output=True,
                text=True,
            )
            if result.returncode != 0:
                raise RuntimeError(f"Piper synthesis failed: {result.stderr}")

            return _reconcile_to_48k_stereo(raw_output_path)
        finally:
            if os.path.exists(raw_output_path):
                os.unlink(raw_output_path)

    def _try_download_model(self, voice: str, models_dir: pathlib.Path) -> None:
        """Attempt to download Piper ONNX model from HuggingFace.

        Args:
            voice: Voice identifier (without .onnx extension if provided).
            models_dir: Target directory for the downloaded model.
        """
        try:
            import urllib.request

            models_dir.mkdir(parents=True, exist_ok=True)
            base_name = voice.removesuffix(".onnx")
            hf_url = (
                f"https://huggingface.co/OHF-Voice/piper1-gpl/resolve/main/voices/{base_name}.onnx"
            )
            dest = models_dir / f"{base_name}.onnx"
            urllib.request.urlretrieve(hf_url, str(dest))  # noqa: S310
        except Exception as exc:
            logger.warning("tts.piper_model_download_failed", voice=voice, error=str(exc))


class KokoroBackend:
    """Kokoro cloud TTS backend via OpenRouter (Apache 2.0)."""

    def __init__(self, transport: httpx.AsyncBaseTransport | None = None) -> None:
        """Initialise backend with an optional custom transport (for testing)."""
        self._transport = transport

    async def synthesise(self, text: str, voice: str, settings: Settings) -> bytes:
        """Synthesise text using Kokoro via OpenRouter API.

        Args:
            text: Text to synthesise.
            voice: Kokoro voice identifier.
            settings: Application settings including the API key.

        Returns:
            48 kHz stereo WAV bytes.

        Raises:
            RuntimeError: If API key is missing, or HTTP 429/400/5xx occurs.
        """
        if settings.openrouter_api_key is None:
            raise RuntimeError("openrouter_kokoro requires STOAT_OPENROUTER_API_KEY")

        client_kwargs: dict[str, object] = {}
        if self._transport is not None:
            client_kwargs["transport"] = self._transport
            client_kwargs["base_url"] = "http://test"

        async with httpx.AsyncClient(**client_kwargs) as client:  # type: ignore[arg-type]
            response = await client.post(
                _OPENROUTER_TTS_URL if self._transport is None else "/tts",
                headers={
                    "Authorization": f"Bearer {settings.openrouter_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "kokoro",
                    "input": text,
                    "voice": voice,
                    "response_format": "wav",
                },
                timeout=60.0,
            )

        if response.status_code == 429:
            raise RuntimeError("TTS rate limited (429): Kokoro quota exceeded")
        if response.status_code == 400:
            raise RuntimeError(f"TTS bad request (400): {response.text}")
        if response.status_code >= 500:
            raise RuntimeError(f"TTS backend error ({response.status_code}): {response.text}")
        response.raise_for_status()

        raw_audio = response.content
        return await asyncio.to_thread(_write_and_reconcile, raw_audio)


_background_tasks: set[asyncio.Task[Any]] = set()


def _create_retained_task(coro: Any) -> asyncio.Task[Any]:
    """Create an asyncio task with strong reference retention."""
    task: asyncio.Task[Any] = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


class TtsService:
    """Orchestrates async TTS synthesis dispatch.

    Manages active synthesis tasks, idempotency guard, status transitions,
    and cache layer. Must be shut down gracefully via shutdown() on server stop.
    """

    def __init__(
        self,
        repository: AsyncTtsCueRepository,
        settings: Settings,
    ) -> None:
        """Initialise TtsService with repository and settings."""
        self._repo = repository
        self._settings = settings
        self._cache = TtsCache(settings.tts_cache_dir)
        self._piper = PiperBackend()
        self._kokoro = KokoroBackend()
        self._active_tasks: dict[str, asyncio.Task[Any]] = {}

    async def synthesise_cue(self, cue_id: str) -> bool:
        """Dispatch async synthesis for a TTS cue.

        Args:
            cue_id: The TTS cue UUID string.

        Returns:
            True if a new synthesis task was dispatched; False if already synthesising.

        Raises:
            ValueError: If cue_id is not found in the repository.
        """
        cue = await self._repo.get(cue_id)
        if cue is None:
            raise ValueError(f"TtsCue {cue_id} not found")

        # Idempotency guard: return without new task if already running
        if cue.status == "synthesising":
            return False

        # Reset status to pending if previously failed
        if cue.status == "failed":
            await self._repo.update_status(cue_id, "pending")

        # Transition to synthesising
        await self._repo.update_status(cue_id, "synthesising")

        task = _create_retained_task(self._do_synthesise(cue_id))
        self._active_tasks[cue_id] = task
        task.add_done_callback(lambda _: self._active_tasks.pop(cue_id, None))

        logger.info(
            "tts.synthesis_started",
            cue_id=cue_id,
            backend=cue.backend,
            voice=cue.voice,
        )
        return True

    async def _do_synthesise(self, cue_id: str) -> None:
        """Internal: perform the actual synthesis and update cue status."""
        cue = await self._repo.get(cue_id)
        if cue is None:
            logger.warning("tts.synthesis_cue_not_found", cue_id=cue_id)
            return

        # Check cache before synthesis
        cached_path = self._cache.hit(cue.cache_key)
        if cached_path is not None:
            # TODO(future-bl): Register TTS audio as a real asset-library entry (UUID,
            # content_hash, mime_type, kind, size_bytes) rather than storing the cache
            # path as a string here. Until then, audio_path in TtsCueResponse exposes
            # this as a plain string.
            await self._repo.update_status(cue_id, "ready", generated_asset_id=str(cached_path))
            logger.info(
                "tts.synthesis_complete",
                cue_id=cue_id,
                backend=cue.backend,
                cache_hit=True,
            )
            return

        try:
            audio_bytes = await self._run_backend(cue.text, cue.voice, cue.backend)
            cached_path = self._cache.store(cue.cache_key, audio_bytes)
            await self._repo.update_status(cue_id, "ready", generated_asset_id=str(cached_path))
            logger.info(
                "tts.synthesis_complete",
                cue_id=cue_id,
                backend=cue.backend,
                cache_hit=False,
            )
        except Exception as exc:
            error_text = str(exc)
            await self._repo.update_status(cue_id, "failed", error=error_text)
            logger.warning(
                "tts.synthesis_failed",
                cue_id=cue_id,
                backend=cue.backend,
                error=error_text,
            )

    async def _run_backend(self, text: str, voice: str, backend: str) -> bytes:
        """Dispatch synthesis to the appropriate backend.

        Args:
            text: Text to synthesise.
            voice: Voice identifier.
            backend: Backend name ('piper_local', 'openrouter_kokoro', 'openrouter_commercial').

        Returns:
            48 kHz stereo WAV bytes.
        """
        loop = asyncio.get_running_loop()
        if backend == "piper_local":
            settings = self._settings
            piper = self._piper
            return await loop.run_in_executor(None, piper.synthesise, text, voice, settings)
        if backend in ("openrouter_kokoro", "openrouter_commercial"):
            return await self._kokoro.synthesise(text, voice, self._settings)
        raise RuntimeError(f"Unknown TTS backend: {backend}")

    async def shutdown(self) -> None:
        """Cancel all active synthesis tasks and wait for them to finish."""
        tasks = list(self._active_tasks.values())
        if not tasks:
            return
        for task in tasks:
            task.cancel()
        # LRN-406: asyncio.wait() with timeout prevents stall on Python 3.10
        await asyncio.wait(set(tasks), timeout=15.0)
        self._active_tasks.clear()

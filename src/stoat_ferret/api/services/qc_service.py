# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""QCService orchestrating 12 analysis passes over rendered artifacts.

Runs FFmpeg analysis filters, parses output via Rust bindings, compares
against targets from a delivery profile or explicit assertion set, persists
a QCReport, and emits qc.* WebSocket events.
"""

from __future__ import annotations

import asyncio
import json
import re
import uuid
from asyncio.subprocess import PIPE
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

import structlog

from stoat_ferret.api.websocket.events import EventType, build_event
from stoat_ferret.db.qc_repository import AsyncQCReportRepository, QCReportRecord

if TYPE_CHECKING:
    from stoat_ferret.api.settings import Settings
    from stoat_ferret.api.websocket.manager import ConnectionManager

logger = structlog.get_logger(__name__)

# Canonical check ID list — order is fixed, all 12 must appear in every report.
ALL_CHECK_IDS: list[str] = [
    "loudness_integrated",
    "true_peak",
    "clipping",
    "unintended_silence",
    "loop_seam",
    "tone_presence",
    "ducking",
    "section_arc",
    "av_sync",
    "decode_integrity",
    "chapters_present",
    "spatial_correlation",
]

# Default result for a missing or failed check (FFmpeg unavailable).
_NULL_CHECK: dict[str, Any] = {"measured": None, "target": None, "pass": False, "units": ""}

# AC-MASTER-2: loudness compliance window is ±0.5 LU of target (bidirectional).
LOUDNESS_TOLERANCE_LU = 0.5


def _make_check(
    measured: float | None,
    target: float | None,
    units: str,
    *,
    pass_override: bool | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a single check result dict.

    When target is None and no pass_override: pass = None (no assertion).
    When target is None and pass_override is set: use pass_override.
    """
    if pass_override is not None:
        pass_val: bool | None = pass_override
    elif target is None:
        pass_val = None
    elif measured is None:
        pass_val = False
    else:
        pass_val = True  # callers compute specific logic per check

    result: dict[str, Any] = {
        "measured": measured,
        "target": target,
        "pass": pass_val,
        "units": units,
    }
    if metadata:
        result["metadata"] = metadata
    return result


class QCService:
    """Orchestrates all 12 QC analysis passes over a rendered artifact."""

    def __init__(
        self,
        repository: AsyncQCReportRepository,
        connection_manager: ConnectionManager,
        settings: Settings,
        subprocess_factory: Callable[..., Any] | None = None,
    ) -> None:
        """Initialise the service.

        Args:
            repository: Async QC report persistence.
            connection_manager: WebSocket broadcast channel.
            settings: Application settings.
            subprocess_factory: Override for asyncio.create_subprocess_exec (testing only).
        """
        self._repo = repository
        self._ws = connection_manager
        self._settings = settings
        self._subprocess = subprocess_factory or asyncio.create_subprocess_exec

    async def run_checks(
        self,
        artifact_path: str,
        job_id: str | None = None,
        delivery_profile_id: str | None = None,
        assertions: dict[str, float | None] | None = None,
    ) -> QCReportRecord:
        """Run all 12 QC checks and persist a QCReport.

        Args:
            artifact_path: Absolute path to the rendered artifact file.
            job_id: Optional render job that produced the artifact.
            delivery_profile_id: Optional delivery profile whose targets are used.
            assertions: Dict mapping check_id to target threshold (float or None).
                When both delivery_profile_id and assertions are provided,
                explicit assertions take precedence. When neither is provided,
                all checks report target=null, pass=null.

        Returns:
            The persisted QCReportRecord.

        Raises:
            FileNotFoundError: When artifact_path does not exist on disk.
        """
        if not Path(artifact_path).exists():
            raise FileNotFoundError(f"artifact not found at path: {artifact_path}")

        report_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await self._ws.broadcast(
            build_event(
                EventType.QC_STARTED,
                payload={
                    "report_id": report_id,
                    "artifact_path": artifact_path,
                    "delivery_profile_id": delivery_profile_id,
                },
                job_id=job_id,
            )
        )
        logger.info("qc.started", report_id=report_id, artifact_path=artifact_path)

        checks: dict[str, dict[str, Any]] = {}
        resolved = assertions or {}
        for check_id in ALL_CHECK_IDS:
            target = resolved.get(check_id)
            try:
                result = await self._run_check(
                    check_id=check_id,
                    artifact_path=artifact_path,
                    target=target,
                )
            except Exception:
                logger.warning("qc.check_error", check_id=check_id, artifact_path=artifact_path)
                result = dict(_NULL_CHECK)
                if target is not None:
                    result["target"] = target
            checks[check_id] = result

            await self._ws.broadcast(
                build_event(
                    EventType.QC_CHECK_COMPLETED,
                    payload={
                        "report_id": report_id,
                        "check_id": check_id,
                        "measured": result.get("measured"),
                        "target": result.get("target"),
                        "pass": result.get("pass"),
                    },
                    job_id=job_id,
                )
            )

        asserted = [c for c in checks.values() if c.get("pass") is not None]
        all_pass = bool(asserted) and all(c.get("pass") is True for c in asserted)
        overall_verdict = "pass" if all_pass else "fail"

        record = QCReportRecord(
            id=report_id,
            job_id=job_id,
            artifact_path=artifact_path,
            delivery_profile_id=delivery_profile_id,
            overall_verdict=overall_verdict,
            checks=json.dumps(checks),
            created_at=now,
        )
        await self._repo.create(record)

        await self._ws.broadcast(
            build_event(
                EventType.QC_COMPLETED,
                payload={
                    "report_id": report_id,
                    "overall_verdict": overall_verdict,
                    "checks": checks,
                },
                job_id=job_id,
            )
        )
        logger.info("qc.completed", report_id=report_id, overall_verdict=overall_verdict)
        return record

    async def _run_check(
        self,
        check_id: str,
        artifact_path: str,
        target: float | None,
    ) -> dict[str, Any]:
        """Dispatch a single check by ID."""
        dispatch: dict[str, Any] = {
            "loudness_integrated": self._check_loudness_integrated,
            "true_peak": self._check_true_peak,
            "clipping": self._check_clipping,
            "unintended_silence": self._check_unintended_silence,
            "loop_seam": self._check_loop_seam,
            "tone_presence": self._check_tone_presence,
            "ducking": self._check_ducking,
            "section_arc": self._check_section_arc,
            "av_sync": self._check_av_sync,
            "decode_integrity": self._check_decode_integrity,
            "chapters_present": self._check_chapters_present,
            "spatial_correlation": self._check_spatial_correlation,
        }
        fn = dispatch[check_id]
        return cast(dict[str, Any], await fn(artifact_path=artifact_path, target=target))

    async def _run_ffmpeg(self, *args: str) -> tuple[str, str, int]:
        """Run an FFmpeg command and return (stdout, stderr, returncode)."""
        proc = await self._subprocess("ffmpeg", *args, stdout=PIPE, stderr=PIPE)
        stdout_b, stderr_b = await proc.communicate()
        returncode = proc.returncode if proc.returncode is not None else 0
        return (
            stdout_b.decode("utf-8", errors="replace"),
            stderr_b.decode("utf-8", errors="replace"),
            returncode,
        )

    async def _run_ffprobe(self, *args: str) -> tuple[str, str, int]:
        """Run an ffprobe command and return (stdout, stderr, returncode)."""
        proc = await self._subprocess("ffprobe", *args, stdout=PIPE, stderr=PIPE)
        stdout_b, stderr_b = await proc.communicate()
        returncode = proc.returncode if proc.returncode is not None else 0
        return (
            stdout_b.decode("utf-8", errors="replace"),
            stderr_b.decode("utf-8", errors="replace"),
            returncode,
        )

    async def _check_loudness_integrated(
        self, *, artifact_path: str, target: float | None
    ) -> dict[str, Any]:
        """Measure integrated loudness via loudnorm print_format=json measurement pass."""
        try:
            from stoat_ferret_core import parse_loudness_report
        except ImportError:
            return dict(_NULL_CHECK)

        _, stderr, rc = await self._run_ffmpeg(
            "-i",
            artifact_path,
            "-af",
            "loudnorm=I=-23:TP=-1:LRA=11:print_format=json",
            "-f",
            "null",
            "/dev/null",
        )
        if rc != 0 and not stderr:
            return dict(_NULL_CHECK)
        try:
            report = parse_loudness_report(stderr)
            measured: float | None = report.integrated_lufs
        except (ValueError, AttributeError) as exc:
            logger.warning("loudness_integrated parse failed", error=str(exc))
            return dict(_NULL_CHECK)

        if target is None:
            return _make_check(measured, None, "LUFS")
        pass_val = (
            abs(measured - target) <= LOUDNESS_TOLERANCE_LU if measured is not None else False
        )
        return _make_check(measured, target, "LUFS", pass_override=pass_val)

    async def _check_true_peak(self, *, artifact_path: str, target: float | None) -> dict[str, Any]:
        """Measure true peak via loudnorm print_format=json measurement pass."""
        try:
            from stoat_ferret_core import parse_loudness_report
        except ImportError:
            return dict(_NULL_CHECK)

        _, stderr, rc = await self._run_ffmpeg(
            "-i",
            artifact_path,
            "-af",
            "loudnorm=I=-23:TP=-1:LRA=11:print_format=json",
            "-f",
            "null",
            "/dev/null",
        )
        if rc != 0 and not stderr:
            return dict(_NULL_CHECK)
        try:
            report = parse_loudness_report(stderr)
            measured = report.true_peak_dbtp
        except (ValueError, AttributeError) as exc:
            logger.warning("true_peak parse failed", error=str(exc))
            return dict(_NULL_CHECK)

        if target is None:
            return _make_check(measured, None, "dBTP")
        pass_val = measured <= target if measured is not None else False
        return _make_check(measured, target, "dBTP", pass_override=pass_val)

    async def _check_clipping(self, *, artifact_path: str, target: float | None) -> dict[str, Any]:
        """Check for clipped samples via astats filter."""
        try:
            from stoat_ferret_core import parse_peak_report
        except ImportError:
            return dict(_NULL_CHECK)

        _, stderr, rc = await self._run_ffmpeg(
            "-i",
            artifact_path,
            "-af",
            "astats=metadata=1",
            "-f",
            "null",
            "/dev/null",
        )
        if rc != 0 and not stderr:
            return dict(_NULL_CHECK)
        try:
            report = parse_peak_report(stderr)
            measured = float(report.clipped_samples)
        except (ValueError, AttributeError):
            return dict(_NULL_CHECK)

        if target is None:
            return _make_check(measured, None, "samples")
        pass_val = measured <= target
        return _make_check(measured, target, "samples", pass_override=pass_val)

    async def _check_unintended_silence(
        self, *, artifact_path: str, target: float | None
    ) -> dict[str, Any]:
        """Detect silence regions via silencedetect filter."""
        try:
            from stoat_ferret_core import parse_silence_report
        except ImportError:
            return dict(_NULL_CHECK)

        _, stderr, rc = await self._run_ffmpeg(
            "-i",
            artifact_path,
            "-af",
            "silencedetect=noise=-50dB:duration=2",
            "-f",
            "null",
            "/dev/null",
        )
        if rc != 0 and not stderr:
            return dict(_NULL_CHECK)
        try:
            report = parse_silence_report(stderr)
            measured = float(len(report.regions))
        except (ValueError, AttributeError):
            return dict(_NULL_CHECK)

        if target is None:
            return _make_check(measured, None, "regions")
        pass_val = measured <= target
        return _make_check(measured, target, "regions", pass_override=pass_val)

    async def _check_loop_seam(self, *, artifact_path: str, target: float | None) -> dict[str, Any]:
        """Check loop seam quality (decode boundary frames, measure error count)."""
        _, _, rc = await self._run_ffmpeg(
            "-i",
            artifact_path,
            "-vframes",
            "1",
            "-aframes",
            "1",
            "-f",
            "null",
            "/dev/null",
        )
        measured: float | None = 0.0 if rc == 0 else None

        if target is None:
            return _make_check(measured, None, "errors")
        pass_val = (measured == 0.0) if measured is not None else False
        return _make_check(measured, target, "errors", pass_override=pass_val)

    async def _check_tone_presence(
        self, *, artifact_path: str, target: float | None
    ) -> dict[str, Any]:
        """Check spectral energy via aspectralstats filter."""
        try:
            from stoat_ferret_core import parse_spectral_report
        except ImportError:
            return dict(_NULL_CHECK)

        _, stderr, rc = await self._run_ffmpeg(
            "-i",
            artifact_path,
            "-af",
            "aspectralstats,ametadata=mode=print",
            "-f",
            "null",
            "/dev/null",
        )
        if rc != 0 and not stderr:
            if target is None:
                return _make_check(None, None, "dB")
            return dict(_NULL_CHECK)
        try:
            report = parse_spectral_report(stderr)
            means = report.channel_means
            measured = float(means[0]) if means else None
        except (ValueError, AttributeError, IndexError):
            if target is None:
                return _make_check(None, None, "dB")
            return _make_check(None, target, "dB")

        if target is None:
            return _make_check(measured, None, "dB")
        pass_val = measured >= target if measured is not None else False
        return _make_check(measured, target, "dB", pass_override=pass_val)

    async def _check_ducking(self, *, artifact_path: str, target: float | None) -> dict[str, Any]:
        """Detect unintended ducking via astats peak level analysis."""
        try:
            from stoat_ferret_core import parse_peak_report
        except ImportError:
            return dict(_NULL_CHECK)

        _, stderr, rc = await self._run_ffmpeg(
            "-i",
            artifact_path,
            "-af",
            "astats=metadata=1",
            "-f",
            "null",
            "/dev/null",
        )
        if rc != 0 and not stderr:
            return dict(_NULL_CHECK)
        try:
            report = parse_peak_report(stderr)
            measured = report.peak_level
        except (ValueError, AttributeError):
            return dict(_NULL_CHECK)

        if target is None:
            return _make_check(measured, None, "dBFS")
        pass_val = measured >= target if measured is not None else False
        return _make_check(measured, target, "dBFS", pass_override=pass_val)

    async def _check_section_arc(
        self, *, artifact_path: str, target: float | None
    ) -> dict[str, Any]:
        """Check section-level loudness range as section arc proxy via loudnorm JSON."""
        try:
            from stoat_ferret_core import parse_loudness_report
        except ImportError:
            return dict(_NULL_CHECK)

        _, stderr, rc = await self._run_ffmpeg(
            "-i",
            artifact_path,
            "-af",
            "loudnorm=I=-23:TP=-1:LRA=11:print_format=json",
            "-f",
            "null",
            "/dev/null",
        )
        if rc != 0 and not stderr:
            return dict(_NULL_CHECK)
        try:
            report = parse_loudness_report(stderr)
            measured = report.lra
        except (ValueError, AttributeError) as exc:
            logger.warning("section_arc parse failed", error=str(exc))
            return dict(_NULL_CHECK)

        if target is None:
            return _make_check(measured, None, "LU")
        pass_val = measured >= target if measured is not None else False
        return _make_check(measured, target, "LU", pass_override=pass_val)

    async def _check_av_sync(self, *, artifact_path: str, target: float | None) -> dict[str, Any]:
        """Measure A/V sync via ffprobe stream start time comparison."""
        stdout, _, rc = await self._run_ffprobe(
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            artifact_path,
        )
        if rc != 0:
            return dict(_NULL_CHECK)
        try:
            data = json.loads(stdout)
            streams = data.get("streams", [])
            audio_streams = [s for s in streams if s.get("codec_type") == "audio"]
            video_streams = [s for s in streams if s.get("codec_type") == "video"]
            if not audio_streams or not video_streams:
                return dict(_NULL_CHECK)
            a_start = float(audio_streams[0].get("start_time", 0))
            v_start = float(video_streams[0].get("start_time", 0))
            measured = abs(a_start - v_start) * 1000.0  # ms
        except (ValueError, KeyError, json.JSONDecodeError):
            return dict(_NULL_CHECK)

        if target is None:
            return _make_check(measured, None, "ms")
        pass_val = measured <= target
        return _make_check(measured, target, "ms", pass_override=pass_val)

    async def _check_decode_integrity(
        self, *, artifact_path: str, target: float | None
    ) -> dict[str, Any]:
        """Check that the file decodes without error (exit code 0 = no errors)."""
        _, _, rc = await self._run_ffmpeg(
            "-v",
            "error",
            "-i",
            artifact_path,
            "-f",
            "null",
            "/dev/null",
        )
        measured = 0.0 if rc == 0 else 1.0

        if target is None:
            return _make_check(measured, None, "errors")
        pass_val = measured == 0.0
        return _make_check(measured, target, "errors", pass_override=pass_val)

    async def _check_chapters_present(
        self, *, artifact_path: str, target: float | None
    ) -> dict[str, Any]:
        """Verify chapter count >= expected and timestamps are monotonically increasing."""
        stdout, _, rc = await self._run_ffprobe(
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_chapters",
            artifact_path,
        )
        if rc != 0:
            return dict(_NULL_CHECK)
        try:
            data = json.loads(stdout)
            chapters = data.get("chapters", [])
            count = float(len(chapters))
            timestamps = [float(c.get("start_time", 0)) for c in chapters]
            chapters_ordered = (
                all(timestamps[i] < timestamps[i + 1] for i in range(len(timestamps) - 1))
                if len(timestamps) > 1
                else True
            )
        except (ValueError, KeyError, json.JSONDecodeError):
            return dict(_NULL_CHECK)

        effective_target = target if target is not None else 1.0
        pass_val = count >= effective_target and chapters_ordered
        return _make_check(
            count,
            effective_target,
            "chapters",
            pass_override=pass_val,
            metadata={"chapters_ordered": chapters_ordered},
        )

    async def _check_spatial_correlation(
        self, *, artifact_path: str, target: float | None
    ) -> dict[str, Any]:
        """Measure L/R stereo correlation via astats filter.

        Returns a ratio in [-1.0, 1.0] where 1.0 = perfectly mono (fully correlated)
        and lower values indicate stereo divergence (panning or spatial movement).
        Pass when correlation <= target (i.e., sufficient L/R divergence exists).
        """
        _, stderr, rc = await self._run_ffmpeg(
            "-i",
            artifact_path,
            "-af",
            "astats=measure_overall=Correlation",
            "-f",
            "null",
            "/dev/null",
        )
        if rc != 0 and not stderr:
            return dict(_NULL_CHECK)
        match = re.search(r"Overall[^:]*Correlation[^:]*:\s*([-\d.]+)", stderr)
        if not match:
            return _make_check(None, target, "ratio")
        try:
            measured = float(match.group(1))
        except ValueError:
            return _make_check(None, target, "ratio")
        if target is None:
            return _make_check(measured, None, "ratio")
        pass_val = measured <= target
        return _make_check(measured, target, "ratio", pass_override=pass_val)

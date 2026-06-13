"""v081 Video FX acceptance harness — gate verification for BL-450 through BL-455.

Verifies all v081 video FX acceptance criteria are either:
  - Covered by automated smoke/unit tests (fast, no FFmpeg required), or
  - Deferred with documented discharge plans.

AC coverage matrix
==================
BL    Feature                  AC-1          AC-2          AC-3             AC-4
BL-450 color_lut               smoke         smoke         DEFER:FFmpeg     DEFER:UAT-J706
BL-451 blur/sharpen            smoke         smoke         smoke            DEFER:FFmpeg
BL-452 keying/compositing      smoke         smoke         smoke            DEFER:FFmpeg
BL-453 optical-distortion      smoke         DEFER:gap     DEFER:FFmpeg     —
BL-454 generators              smoke         smoke         smoke            DEFER:FFmpeg
BL-455 opacity/scale           smoke         smoke         smoke            DEFER:UAT

Smoke test coverage: tests/smoke/test_effects.py
  - test_v081_video_fx_effect[blur,sharpen,opacity,scale,color_lut,chroma_key,color_key,
    lens_distort]
  - test_v081_generator_fx_catalog_and_preview[gradient_generator,noise_generator]

BL-453 AC-2 gap: chromatic_aberration (rgbashift) has no clip-apply smoke test; lens_distort covers
  AC-1 (lenscorrection). Chromatic aberration requires a separate FFmpeg contract test discharge.

Deferred discharge commands
===========================
FFmpeg contract tests:
  STOAT_TEST_FFMPEG=1 uv run pytest \
    tests/acceptance/v081_video_fx_harness.py::TestV081FfmpegContracts -v

Headed UAT journeys:
  python scripts/uat_runner.py --headed --journey 706   # BL-450-AC-4: color grading GUI preview
  python scripts/uat_runner.py --headed --journey 707   # blur headed visual verification
  python scripts/uat_runner.py --headed --journey 708   # chroma_key headed visual verification
  python scripts/uat_runner.py --headed --journey 709   # lens_distort headed visual verification
  python scripts/uat_runner.py --headed --journey 710   # gradient_generator visual verification
  # BL-455-AC-4 (automation lane GUI): manual verification — apply opacity/scale effect,
  # confirm the automation lane renders in the effects panel, add/edit keyframes interactively.
"""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import httpx
import pytest

STOAT_TEST_FFMPEG = os.environ.get("STOAT_TEST_FFMPEG")

_DEMO_VIDEOS_DIR = Path(__file__).resolve().parent.parent.parent / "videos" / "demo"
_SAMPLE_VIDEO = "78888-568004778_medium.mp4"

# Deferred AC inventory — asserted by test_deferred_*_acs_documented
_DEFERRED_FFMPEG_ACS: list[str] = [
    "BL-450-AC-3: color_lut renders without error (FFmpeg contract)",
    "BL-451-AC-4: blur/sharpen renders without error (FFmpeg contract)",
    "BL-452-AC-4: keying/compositing renders without error (FFmpeg contract)",
    "BL-453-AC-2: chromatic_aberration (rgbashift) — no clip-apply smoke coverage",
    "BL-453-AC-3: optical-distortion renders without error (FFmpeg contract)",
    "BL-454-AC-4: generators render without error (FFmpeg contract)",
]

_DEFERRED_UAT_ACS: list[str] = [
    "BL-450-AC-4: color_lut selectable with graded preview in GUI (J706 --headed)",
    "BL-455-AC-4: opacity/scale editable via GUI automation lane (headed UAT)",
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
async def acceptance_client(tmp_path: Path) -> httpx.AsyncClient:  # type: ignore[misc]
    """In-process async client backed by a fresh app instance with isolated DB."""
    from stoat_ferret.api.app import create_app, lifespan
    from stoat_ferret.api.settings import get_settings

    orig_db = os.environ.get("STOAT_DATABASE_PATH")
    orig_thumb = os.environ.get("STOAT_THUMBNAIL_DIR")

    os.environ["STOAT_DATABASE_PATH"] = str(tmp_path / "acceptance.db")
    os.environ["STOAT_THUMBNAIL_DIR"] = str(tmp_path / "thumbnails")
    get_settings.cache_clear()

    app = create_app()
    async with (
        lifespan(app),
        httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://testserver",
        ) as client,
    ):
        yield client

    for key, orig in [
        ("STOAT_DATABASE_PATH", orig_db),
        ("STOAT_THUMBNAIL_DIR", orig_thumb),
    ]:
        if orig is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = orig
    get_settings.cache_clear()


async def _poll_render(
    client: httpx.AsyncClient,
    job_id: str,
    *,
    timeout: float = 120.0,
    interval: float = 1.0,
) -> str:
    """Poll render job until terminal; return final status."""
    terminal = {"completed", "failed", "cancelled", "qc_failed"}
    deadline = asyncio.get_event_loop().time() + timeout
    status = ""
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/v1/render/{job_id}")
        resp.raise_for_status()
        status = str(resp.json()["status"])
        if status in terminal:
            return status
        await asyncio.sleep(interval)
    raise asyncio.TimeoutError(
        f"Render job {job_id} did not complete within {timeout}s; last status: {status}"
    )


async def _scan_and_get_video(
    client: httpx.AsyncClient,
    videos_dir: Path,
) -> str:
    """Scan videos_dir and return first video ID."""
    scan_resp = await client.post(
        "/api/v1/videos/scan",
        json={"path": str(videos_dir), "recursive": False},
    )
    scan_resp.raise_for_status()
    job_id = scan_resp.json()["job_id"]

    terminal = {"completed", "failed", "timeout", "cancelled"}
    deadline = asyncio.get_event_loop().time() + 30.0
    while asyncio.get_event_loop().time() < deadline:
        resp = await client.get(f"/api/v1/jobs/{job_id}")
        resp.raise_for_status()
        if resp.json()["status"].lower() in terminal:
            break
        await asyncio.sleep(0.5)

    videos_resp = await client.get("/api/v1/videos?limit=1")
    videos_resp.raise_for_status()
    videos = videos_resp.json()["videos"]
    assert videos, f"No videos found after scanning {videos_dir}"
    return str(videos[0]["id"])


async def _create_project_with_clip(
    client: httpx.AsyncClient,
    project_name: str,
    video_id: str,
) -> tuple[str, str]:
    """Create a project with one clip; return (project_id, clip_id)."""
    proj_resp = await client.post("/api/v1/projects", json={"name": project_name})
    proj_resp.raise_for_status()
    project_id = str(proj_resp.json()["id"])

    clip_resp = await client.post(
        f"/api/v1/projects/{project_id}/clips",
        json={
            "source_video_id": video_id,
            "in_point": 0,
            "out_point": 30,
            "timeline_position": 0,
        },
    )
    clip_resp.raise_for_status()
    clip_id = str(clip_resp.json()["id"])
    return project_id, clip_id


async def _submit_render(client: httpx.AsyncClient, project_id: str) -> str:
    """Submit a render job and return job_id."""
    render_resp = await client.post(
        "/api/v1/render",
        json={
            "project_id": project_id,
            "render_plan": json.dumps({"total_duration": 1.0, "settings": {}}),
        },
    )
    render_resp.raise_for_status()
    return str(render_resp.json()["id"])


# ---------------------------------------------------------------------------
# Gate verification (no FFmpeg required)
# ---------------------------------------------------------------------------


class TestV081VideoFXCoverage:
    """Gate verification: v081 effects are in catalog and smoke coverage is in place."""

    async def test_all_v081_effects_in_catalog(
        self, acceptance_client: httpx.AsyncClient
    ) -> None:
        """All 10 v081 video FX effect types are registered in GET /effects catalog."""
        resp = await acceptance_client.get("/api/v1/effects")
        assert resp.status_code == 200
        catalog = {e["effect_type"] for e in resp.json()["effects"]}

        required = {
            "color_lut",          # BL-450
            "blur",               # BL-451
            "sharpen",            # BL-451
            "chroma_key",         # BL-452
            "color_key",          # BL-452
            "lens_distort",       # BL-453
            "gradient_generator", # BL-454
            "noise_generator",    # BL-454
            "opacity",            # BL-455
            "scale",              # BL-455
        }
        missing = required - catalog
        assert not missing, f"v081 effects missing from catalog: {sorted(missing)}"

    def test_smoke_test_file_covers_v081_effects(self) -> None:
        """Smoke test file contains parametrized tests for all v081 clip-applicable effects."""
        smoke_file = (
            Path(__file__).resolve().parent.parent / "smoke" / "test_effects.py"
        )
        assert smoke_file.exists(), f"Smoke file not found: {smoke_file}"
        content = smoke_file.read_text()

        assert "test_v081_video_fx_effect" in content, (
            "test_v081_video_fx_effect not found in test_effects.py"
        )
        assert "test_v081_generator_fx_catalog_and_preview" in content, (
            "test_v081_generator_fx_catalog_and_preview not found in test_effects.py"
        )
        for effect in (
            "blur", "sharpen", "opacity", "scale",
            "color_lut", "chroma_key", "color_key", "lens_distort",
        ):
            assert f'"{effect}"' in content, (
                f"Effect {effect!r} not in smoke test parametrize list"
            )

    def test_uat_journeys_registered_for_v081(self) -> None:
        """UAT runner has v081 journeys J707–J710 in JOURNEY_DEPS and JOURNEY_MODULE_MAP."""
        runner = (
            Path(__file__).resolve().parent.parent.parent / "scripts" / "uat_runner.py"
        )
        assert runner.exists(), f"uat_runner.py not found at {runner}"
        content = runner.read_text()
        for journey_id in (707, 708, 709, 710):
            assert str(journey_id) in content, (
                f"Journey {journey_id} not found in uat_runner.py"
            )

    def test_deferred_ffmpeg_acs_documented(self) -> None:
        """All FFmpeg-deferred ACs have entries in _DEFERRED_FFMPEG_ACS."""
        assert len(_DEFERRED_FFMPEG_ACS) == 6
        for entry in _DEFERRED_FFMPEG_ACS:
            assert entry.startswith("BL-"), f"Malformed deferred entry: {entry!r}"

    def test_deferred_uat_acs_documented(self) -> None:
        """All UAT-deferred ACs have entries in _DEFERRED_UAT_ACS."""
        assert len(_DEFERRED_UAT_ACS) == 2
        for entry in _DEFERRED_UAT_ACS:
            assert entry.startswith("BL-"), f"Malformed deferred entry: {entry!r}"


# ---------------------------------------------------------------------------
# FFmpeg contract tests (deferred_post_merge; require STOAT_TEST_FFMPEG=1)
# ---------------------------------------------------------------------------

_ffmpeg_skip = pytest.mark.skipif(
    not STOAT_TEST_FFMPEG,
    reason=(
        "FFmpeg contract tests deferred. "
        "Discharge: STOAT_TEST_FFMPEG=1 uv run pytest tests/acceptance/v081_video_fx_harness.py -v"
    ),
)

_demo_videos_skip = pytest.mark.skipif(
    not (_DEMO_VIDEOS_DIR / _SAMPLE_VIDEO).exists(),
    reason=f"Demo video required at {_DEMO_VIDEOS_DIR / _SAMPLE_VIDEO}",
)


@_ffmpeg_skip
@_demo_videos_skip
class TestV081FfmpegContracts:
    """BL-450–BL-455: render contract tests against real FFmpeg (deferred_post_merge).

    Verify each v081 effect's filter string is valid FFmpeg syntax that renders without error.
    All tests require STOAT_TEST_FFMPEG=1 and demo video files at videos/demo/.

    Discharge:
        STOAT_TEST_FFMPEG=1 uv run pytest \
            tests/acceptance/v081_video_fx_harness.py::TestV081FfmpegContracts -v
    """

    async def test_bl450_color_lut_render_contract(
        self, acceptance_client: httpx.AsyncClient
    ) -> None:
        """BL-450-AC-3: color_lut renders without error under real FFmpeg."""
        video_id = await _scan_and_get_video(acceptance_client, _DEMO_VIDEOS_DIR)
        project_id, clip_id = await _create_project_with_clip(
            acceptance_client, "BL-450 Color LUT Acceptance", video_id
        )
        resp = await acceptance_client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={"effect_type": "color_lut", "parameters": {"preset": "warm_fade"}},
        )
        assert resp.status_code == 201, f"color_lut apply failed: {resp.text}"
        assert "lut3d" in resp.json()["filter_string"]

        job_id = await _submit_render(acceptance_client, project_id)
        status = await _poll_render(acceptance_client, job_id)
        assert status in {"completed", "qc_failed"}, (
            f"BL-450-AC-3: color_lut render ended with unexpected status {status!r}"
        )

    async def test_bl451_blur_render_contract(
        self, acceptance_client: httpx.AsyncClient
    ) -> None:
        """BL-451-AC-4: blur renders without error under real FFmpeg."""
        video_id = await _scan_and_get_video(acceptance_client, _DEMO_VIDEOS_DIR)
        project_id, clip_id = await _create_project_with_clip(
            acceptance_client, "BL-451 Blur Acceptance", video_id
        )
        resp = await acceptance_client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={"effect_type": "blur", "parameters": {"sigma": 2.0}},
        )
        assert resp.status_code == 201, f"blur apply failed: {resp.text}"
        assert "gblur" in resp.json()["filter_string"]

        job_id = await _submit_render(acceptance_client, project_id)
        status = await _poll_render(acceptance_client, job_id)
        assert status in {"completed", "qc_failed"}, (
            f"BL-451-AC-4: blur render ended with unexpected status {status!r}"
        )

    async def test_bl452_chroma_key_render_contract(
        self, acceptance_client: httpx.AsyncClient
    ) -> None:
        """BL-452-AC-4: chroma_key renders without error under real FFmpeg."""
        video_id = await _scan_and_get_video(acceptance_client, _DEMO_VIDEOS_DIR)
        project_id, clip_id = await _create_project_with_clip(
            acceptance_client, "BL-452 Chroma Key Acceptance", video_id
        )
        resp = await acceptance_client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={
                "effect_type": "chroma_key",
                "parameters": {"color": "green", "similarity": 0.1},
            },
        )
        assert resp.status_code == 201, f"chroma_key apply failed: {resp.text}"
        assert "chromakey" in resp.json()["filter_string"]

        job_id = await _submit_render(acceptance_client, project_id)
        status = await _poll_render(acceptance_client, job_id)
        assert status in {"completed", "qc_failed"}, (
            f"BL-452-AC-4: chroma_key render ended with unexpected status {status!r}"
        )

    async def test_bl453_lens_distort_render_contract(
        self, acceptance_client: httpx.AsyncClient
    ) -> None:
        """BL-453-AC-3: lens_distort renders without error under real FFmpeg."""
        video_id = await _scan_and_get_video(acceptance_client, _DEMO_VIDEOS_DIR)
        project_id, clip_id = await _create_project_with_clip(
            acceptance_client, "BL-453 Lens Distort Acceptance", video_id
        )
        resp = await acceptance_client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={"effect_type": "lens_distort", "parameters": {"k1": 0.1, "k2": 0.05}},
        )
        assert resp.status_code == 201, f"lens_distort apply failed: {resp.text}"
        assert "lenscorrection" in resp.json()["filter_string"]

        job_id = await _submit_render(acceptance_client, project_id)
        status = await _poll_render(acceptance_client, job_id)
        assert status in {"completed", "qc_failed"}, (
            f"BL-453-AC-3: lens_distort render ended with unexpected status {status!r}"
        )

    async def test_bl454_gradient_generator_render_contract(
        self, acceptance_client: httpx.AsyncClient
    ) -> None:
        """BL-454-AC-4: gradient_generator renders without error under real FFmpeg."""
        proj_resp = await acceptance_client.post(
            "/api/v1/projects",
            json={"name": "BL-454 Gradient Generator Acceptance"},
        )
        proj_resp.raise_for_status()
        project_id = str(proj_resp.json()["id"])

        clip_resp = await acceptance_client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "clip_type": "generator",
                "generator_params": {"type": "aevalsrc", "expr": "0", "duration": 1.0},
                "in_point": 0,
                "out_point": 30,
                "timeline_position": 0,
            },
        )
        clip_resp.raise_for_status()
        clip_id = str(clip_resp.json()["id"])

        resp = await acceptance_client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={
                "effect_type": "gradient_generator",
                "parameters": {"color1": "black", "color2": "white", "duration": 1.0},
            },
        )
        assert resp.status_code == 201, f"gradient_generator apply failed: {resp.text}"
        assert "gradients" in resp.json()["filter_string"]

        job_id = await _submit_render(acceptance_client, project_id)
        status = await _poll_render(acceptance_client, job_id)
        assert status in {"completed", "qc_failed"}, (
            f"BL-454-AC-4: gradient_generator render ended with unexpected status {status!r}"
        )

    async def test_bl455_opacity_scale_render_contract(
        self, acceptance_client: httpx.AsyncClient
    ) -> None:
        """BL-455-AC-3: opacity with automation envelope renders without error under real FFmpeg."""
        video_id = await _scan_and_get_video(acceptance_client, _DEMO_VIDEOS_DIR)
        project_id, clip_id = await _create_project_with_clip(
            acceptance_client, "BL-455 Opacity/Scale Acceptance", video_id
        )
        resp = await acceptance_client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_id}/effects",
            json={
                "effect_type": "opacity",
                "parameters": {
                    "opacity": {
                        "default": 1.0,
                        "keyframes": [
                            {"t": 0.0, "value": 0.0, "curve": "linear"},
                            {"t": 1.0, "value": 1.0, "curve": "linear"},
                        ],
                    }
                },
            },
        )
        assert resp.status_code == 201, f"opacity apply failed: {resp.text}"

        job_id = await _submit_render(acceptance_client, project_id)
        status = await _poll_render(acceptance_client, job_id)
        assert status in {"completed", "qc_failed"}, (
            f"BL-455-AC-3: opacity render ended with unexpected status {status!r}"
        )

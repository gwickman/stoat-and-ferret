# Example Workflow - Chatbot-Driven End-to-End Test

## Summary

This example shows how a local chatbot operator could test Stoat and Ferret without a custom MCP server. The chatbot uses the existing API and WebSocket surfaces, with optional browser validation at the end.

This is an example of a realistic internal testing session, not a productized end-user flow.

## Scenario

Goal:

- verify that Stoat and Ferret can ingest media, build a simple project, preview it, render it, and expose enough state for a chatbot to summarize the outcome

Assumptions:

- backend is running locally
- frontend is available under `/gui`
- FFmpeg is installed
- sample media exists in a known folder

## High-Level Steps

### 1. Preflight

The chatbot begins by checking:

- `GET /health/live`
- `GET /health/ready`
- available render encoders and formats
- whether a sample project already exists

Expected result:

- system is healthy
- required subsystems are available
- no obvious blockers before mutation begins

### 2. Scan Source Media

The chatbot submits a scan request for a test media directory, then monitors job progress.

Likely flow:

- `POST /api/v1/videos/scan`
- `GET /api/v1/jobs/{job_id}` or WebSocket monitoring
- `GET /api/v1/videos`

Expected result:

- videos appear in library
- metadata is available
- thumbnails or proxy generation may begin

### 3. Create a Project

The chatbot creates a new project with standard output settings and selects a few source videos.

Likely flow:

- `POST /api/v1/projects`
- `POST /api/v1/projects/{id}/clips`
- `GET /api/v1/projects/{id}/clips`

Expected result:

- project exists
- clips are attached in the intended order

### 4. Discover and Apply Effects

The chatbot queries effect discovery and chooses one or two simple effects that are easy to validate, such as:

- text overlay
- fade
- speed change

Likely flow:

- `GET /api/v1/effects`
- `POST /api/v1/effects/preview`
- `POST /api/v1/projects/{project_id}/clips/{clip_id}/effects`

Expected result:

- chatbot can explain which effect it chose and why
- filter preview strings match the requested operation
- effect application succeeds with valid parameters

### 5. Preview the Project

The chatbot starts a preview session and watches for readiness and progress.

Likely flow:

- `POST /api/v1/projects/{id}/preview/start`
- `GET /api/v1/projects/{id}/preview/status` or WebSocket monitoring
- optional thumbnail strip and waveform fetches

Expected result:

- preview reaches ready state
- manifest/segment URLs are available
- player-visible state is consistent with backend state

### 6. Optional GUI Validation

The chatbot opens the GUI and verifies that the frontend reflects the same state:

- project visible
- preview page available
- Theater Mode can show current progress
- render page is reachable

This step is optional and should be used for:

- end-to-end confidence
- visual verification
- regression detection on user-facing surfaces

### 7. Start a Render

The chatbot submits a render with known-good settings and monitors progress.

Likely flow:

- `POST /api/v1/render/preview` to inspect the generated command before submitting a render
- `POST /api/v1/render`
- WebSocket monitoring of queue and progress
- `GET /api/v1/render/{job_id}` or render list endpoints

> **Note:** `POST /api/v1/render/preview` is stateless and project-blind. It returns a
> placeholder FFmpeg command using hardcoded 1920×1080@30fps segments — not derived from the
> project's actual timeline or resolution. Its required fields (`output_format`,
> `quality_preset`, `encoder`) differ from those of `POST /render` (`project_id`); these two
> endpoints do not share a request body. A project-aware preview is not currently supported.

Expected result:

- job enters queue
- job transitions to running
- progress/ETA events arrive
- job reaches a terminal state — one of `completed`, `failed`, or `qc_failed`

> **Note on terminal states:** when the render is submitted with a `delivery_profile`,
> a QC pass runs after encode. If any QC check fails (loudness, true-peak, chapters,
> tone, etc.) the job lands in `qc_failed` rather than `completed`. This is a third
> terminal state — `progress=1.0`, `completed_at` is populated, and the encoded file
> is on disk. A poller that watches only `{completed, failed}` will hang. Treat
> `qc_failed` as terminal-with-quality-fail and fetch `/render/{job_id}/qc` for the
> per-check report.

### 8. Validate Output

If render succeeds, the chatbot verifies output quality across five categories.
If render fails, the chatbot verifies that failure is visible through API/UI, the error message
is captured, and whether a retry path is appropriate.

#### 8.1 File Integrity

Check that the output file exists, is non-zero in size, and contains a valid codec:

```bash
# File exists and is non-empty
test -s output.mp4 && echo "OK" || echo "MISSING OR EMPTY"

# Validate container and codec via ffprobe
ffprobe -v error -select_streams v:0 \
  -show_entries stream=codec_name,width,height,r_frame_rate \
  -of default=noprint_wrappers=1 output.mp4
```

Expected: `codec_name=h264` (or the requested encoder), valid dimensions, non-zero frame rate.
A zero-byte file or `Invalid data found` from ffprobe indicates an FFmpeg failure even if the
job status shows `completed`.

#### 8.2 SSIM Analysis

Compute the Structural Similarity Index (SSIM) between expected and actual frames. The threshold
for pixel-accurate effects is ≥ 0.99.

```python
import subprocess, tempfile, os
from pathlib import Path
from skimage import io as skio
from skimage.metrics import structural_similarity

def extract_frame(video_path: str, timestamp_s: float, out_path: str) -> None:
    subprocess.run(
        ["ffmpeg", "-ss", str(timestamp_s), "-i", video_path,
         "-frames:v", "1", "-y", out_path],
        check=True, capture_output=True,
    )

def compute_ssim(img_a: str, img_b: str) -> float:
    a = skio.imread(img_a, as_gray=True)
    b = skio.imread(img_b, as_gray=True)
    score, _ = structural_similarity(a, b, full=True)
    return score

ssim = compute_ssim("expected_frame.png", "actual_frame.png")
assert ssim >= 0.99, f"SSIM too low: {ssim:.4f} — effect may not be applied"
```

#### 8.3 Effect Detection

Use edge magnitude (Sobel filter) or mean luminance to verify that effects are applied.

**Opacity gradient detection** (luminance-based):

```python
import numpy as np
from skimage import io as skio, color

img = skio.imread("actual_frame.png")
gray = color.rgb2gray(img)
mean_luminance = float(np.mean(gray))
# For a fade-to-black effect at 50% opacity, mean luminance should be ~0.5× the source
assert mean_luminance < 0.6, f"Unexpected mean luminance {mean_luminance:.3f}: fade may not be applied"
```

**Edge detection** (Sobel filter, verifies sharpening/blur contrast):

```python
from skimage.filters import sobel

edges = sobel(gray)
edge_magnitude = float(np.mean(edges))
# Sharpening increases edge magnitude; blur decreases it
assert edge_magnitude > 0.01, f"Low edge magnitude {edge_magnitude:.4f}: sobel response too weak"
```

#### 8.4 Command Logging

Check the render evidence API for the FFmpeg command args, exit code, and stderr tail:

```python
import httpx

resp = httpx.get(f"http://localhost:8765/api/v1/render/{job_id}/evidence")
resp.raise_for_status()
evidence = resp.json()

# Verify the FFmpeg command was captured
assert evidence["ffmpeg_command"], "No FFmpeg command recorded"
assert evidence["exit_code"] == 0, f"FFmpeg exit code {evidence['exit_code']}: {evidence['stderr_tail']}"

# Inspect the actual filter chain that was used
ffmpeg_args = evidence["ffmpeg_command"]
assert "yuv420p" in " ".join(ffmpeg_args), "Missing yuv420p — output may be incompatible with Windows players"
```

The evidence endpoint (`GET /render/{id}/evidence`) is populated by the render worker after
FFmpeg execution and is persisted alongside the job record. It is the authoritative source for
post-render diagnostics.

#### 8.5 Workspace Hygiene

Use `tempfile.mkdtemp` for test artifacts and clean up after verification. Never write temp
files to `working/` without a `.gitignore` guard, and never commit temp files.

```python
import tempfile, shutil, os

tmpdir = tempfile.mkdtemp(prefix="stoat-test-")
try:
    output_path = os.path.join(tmpdir, "output.mp4")
    # ... render and verify using output_path ...
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
```

In CI environments, `tempfile.mkdtemp` resolves to `/tmp` on Linux/macOS and
`%TEMP%` on Windows — both outside the repository tree. Never write test outputs
to `working/` unless `working/.gitignore` explicitly excludes the file pattern.

### 8a. Worked Example — 2-Clip SSIM Matrix

This example tests a 2-clip render by extracting frames at 2 s and 4 s and computing pairwise
SSIM against reference frames. It covers both the passing case and the failing case.

```python
import tempfile, shutil, os, subprocess
import numpy as np
from pathlib import Path
from skimage import io as skio
from skimage.metrics import structural_similarity

TIMESTAMPS = [2.0, 4.0]  # seconds — one per clip

def extract_frame(video: str, t: float, dest: str) -> None:
    subprocess.run(
        ["ffmpeg", "-ss", str(t), "-i", video, "-frames:v", "1", "-y", dest],
        check=True, capture_output=True,
    )

def ssim_pair(a: str, b: str) -> float:
    ia = skio.imread(a, as_gray=True)
    ib = skio.imread(b, as_gray=True)
    score, _ = structural_similarity(ia, ib, full=True)
    return score

tmpdir = tempfile.mkdtemp(prefix="stoat-test-")
try:
    actual = "render_output.mp4"
    expected = "reference_output.mp4"

    results = {}
    for t in TIMESTAMPS:
        a_frame = os.path.join(tmpdir, f"actual_{t}.png")
        e_frame = os.path.join(tmpdir, f"expected_{t}.png")
        extract_frame(actual, t, a_frame)
        extract_frame(expected, t, e_frame)
        results[t] = ssim_pair(e_frame, a_frame)

    # Passing case: all SSIM scores at or above threshold
    for t, score in results.items():
        print(f"t={t}s SSIM={score:.4f} {'PASS' if score >= 0.99 else 'FAIL'}")
        # PASS example:  t=2.0s SSIM=0.9972 PASS
        # PASS example:  t=4.0s SSIM=0.9983 PASS

    # Failing case: effect not applied (e.g. opacity gradient missing)
    # t=2.0s SSIM=0.7431 FAIL  ← large difference: clip 1 effect absent
    # t=4.0s SSIM=0.6892 FAIL  ← large difference: clip 2 effect absent

    for t, score in results.items():
        assert score >= 0.99, (
            f"SSIM at t={t}s is {score:.4f} < 0.99 — "
            "effect may not be applied or render is incorrect"
        )
finally:
    shutil.rmtree(tmpdir, ignore_errors=True)
```

### Known Platform Behaviors

These findings apply to all chatbot-driven or automated test sessions.

#### Windows Media Foundation Compatibility

The render pipeline appends `format=yuv420p` to every output filter chain. This ensures
Windows Media Player, Edge, and other Windows Media Foundation consumers can decode the
output. A file rendered without this conversion (e.g. `yuv444p`) plays correctly on
Linux/macOS but fails silently or shows a blank frame on Windows.

When validating output: check the evidence API for `yuv420p` in the FFmpeg command args.
If the token is absent, the render pipeline has regressed.

#### xfade Timebase Normalization

Multi-clip renders with xfade transitions require all input clips to share the same timebase.
The render pipeline normalizes this via `fps=30,settb=1/30` applied to every input stream
before the xfade filter. Without this step, xfade may produce a 0-byte output or corrupt
the duration of the transition.

Symptom: output file exists but is 0 bytes or shorter than expected. Check the FFmpeg
stderr tail in the evidence API for `[Parsed_xfade]` warnings.

#### fontconfig on CI

The ASS/subtitle filter requires a fontconfig database to resolve font names. On headless
CI runners (Docker, GitHub Actions), fontconfig may not be initialized, causing the filter
to fall back to a missing font or to fail entirely.

Warning signs: `Cannot load font` in FFmpeg stderr, or subtitles rendered in a fallback
monospace font instead of the requested typeface.

Mitigation: set `FONTCONFIG_PATH` to a directory containing a valid `fonts.conf`, or
pre-seed the fontconfig cache with `fc-cache -fv` during CI setup.

### 9. Summarize

The chatbot produces a test summary:

- what it attempted
- which endpoints and surfaces were exercised
- whether preview and render completed
- any failures or degraded behavior
- recommended next debugging step

## Why This Workflow Fits The Current Architecture

This workflow works because Stoat and Ferret already provides:

- structured API mutation points
- discovery endpoints
- progress/event channels
- observable GUI surfaces
- render and preview infrastructure

The chatbot does not need a custom tool server to execute this scenario. It needs only:

- access to the local app
- a stable workflow reference
- enough reliability in the event and persistence layers

## What Would Make This Easier

Three small additions would improve this workflow significantly without adding MCP:

1. An agent operator guide listing canonical call sequences.
2. A helper script for "wait until preview/render completes."
3. A compact event reference for WebSocket payloads and terminal states.

## Bottom Line

This example shows that chatbot-driven testing is already a natural extension of the current architecture. The remaining work is mainly about making the workflow more reliable and easier to repeat, not about inventing a new integration model.

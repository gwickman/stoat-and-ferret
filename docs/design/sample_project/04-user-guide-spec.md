# User Guide Specification

This document specifies the contents of the user-facing guide at `docs/setup/guides/sample-project.md`. The guide itself is a separate deliverable for a future implementation task. This specification defines what the guide should contain, its structure, tone, and audience.

## Target File

`docs/setup/guides/sample-project.md`

## Document Structure

### 1. Title and Overview

**Heading:** `# Sample Project: Running Montage`

Contents:
- What the sample project is: a pre-built editing project using the video files included in the repository
- Why it exists: development reference, testing anchor, onboarding aid
- What it demonstrates: clips with in/out points, video effects (fade, text overlay, speed control), crossfade transitions, timeline composition

### 2. Prerequisites

Contents:
- stoat-and-ferret server running locally (link to `docs/setup/02_development-setup.md`)
- Python 3.10+ (for the seed script)
- `httpx` installed (available via `uv sync` — no separate install needed)
- Video files present in the `/videos/` directory (included in the repository)

### 3. Quick Start

Commands to show:
```bash
# Seed the sample project
python scripts/seed_sample_project.py http://localhost:8765

# Open the GUI to see the result
# Navigate to: http://localhost:8765/gui/projects
```

Include sample terminal output showing the summary message (project ID, counts, output settings).

### 4. What Gets Created

#### Videos Imported

- Table of the 4 videos used: filename, duration, resolution
- Note that 2 additional videos are available in `/videos/` but not used in the sample project
- All 6 videos are scanned into the library; only 4 are used in clips

#### Project Structure

- Project name: "Running Montage"
- Output settings: 1280x720 @ 30fps
- 4 clips with their source videos, in/out points (frames), and timeline positions

#### ASCII Timeline Diagram

```
|--Clip 1--|------Clip 2------|---Clip 3---|---Clip 4---|
0s        8s               23s          34s           44s
fade-in    slow-mo          xfade                  fade-out
"Running                                "The End"
 Montage"
```

#### Effects Applied

- Clip 1: Fade-in from black (1 second), "Running Montage" title overlay (64pt white text)
- Clip 2: 0.75x speed (slow motion)
- Clip 4: "The End" title overlay (48pt white text), fade-out to black (2 seconds)

#### Transitions

- Crossfade between Clip 2 and Clip 3 (1 second duration)

### 5. Exploring the Project

How-to instructions for:
- Viewing the project in the GUI: navigate to Projects page, click "Running Montage"
- Inspecting clips via API:
  ```bash
  curl http://localhost:8765/api/v1/projects | python -m json.tool
  # Find the project ID, then:
  curl http://localhost:8765/api/v1/projects/{id}/clips | python -m json.tool
  ```
- Viewing effects on a clip: examine the `effects` array in the clip response
- Viewing the effect catalog: `curl http://localhost:8765/api/v1/effects`

### 6. Resetting the Sample Project

Commands to show:
```bash
# Delete and recreate
python scripts/seed_sample_project.py http://localhost:8765 --force

# Manual deletion via API
curl -X DELETE http://localhost:8765/api/v1/projects/{id}
```

Note: Scanned videos persist in the library after project deletion. Only the project, its clips, and their effects are removed.

### 7. For Developers

Contents:
- How to modify the sample project definition: edit `CLIP_DEFS`, `EFFECT_DEFS`, `TRANSITION_DEFS` constants in `scripts/seed_sample_project.py`
- How to add new effects or clips to the sample project
- Relationship to smoke tests: the `sample_project` fixture in `tests/smoke/conftest.py` uses the same definitions
- When updating the seed script, also update the fixture and this guide

#### Cross-References

- `docs/design/sample_project/` — Sample project design documents
- `docs/design/smoke_test/` — Smoke test design documents
- `docs/manual/04_effects-guide.md` — Effect types and parameters
- `docs/manual/02_api-overview.md` — API overview
- `scripts/seed_sample_project.py` — The seed script source code

## Key Facts to Include

- Project name: "Running Montage"
- 4 clips from 4 of the 6 available videos
- Output: 1280x720 @ 30fps
- Total duration: ~46 seconds (1380 frames)
- 5 effects: 2 fades, 2 text overlays, 1 speed control
- 1 transition: crossfade between Clip 2 and Clip 3

## Tone and Audience

- **Audience:** Developers onboarding to the project. Not end users.
- **Tone:** Technical and concise. Runnable commands, not prose explanations.
- **Assumptions:** Reader has the repo cloned, dependencies installed (`uv sync`), server running, and basic familiarity with REST APIs.
- **Voice:** Second person ("Run the following command...") or imperative ("Seed the project...").

## What NOT to Include

- **No screenshots.** Use ASCII diagrams and API curl examples instead. Screenshots go stale when the UI changes.
- **No detailed API documentation.** Link to the existing API docs (`docs/manual/03_api-reference.md`) rather than duplicating endpoint descriptions.
- **No installation instructions.** Link to the setup guide (`docs/setup/02_development-setup.md`) rather than repeating prerequisite setup steps.
- **No internal implementation details.** The guide is about using the sample project, not about how the seed script or smoke tests work internally.

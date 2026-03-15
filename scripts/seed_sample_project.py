#!/usr/bin/env python3
"""Seed the 'Running Montage' sample project against a running stoat-and-ferret instance.

Creates a complete sample project with 4 clips, 5 effects, and 1 transition
using the canonical project definition from docs/design/sample_project/.

Usage:
    python scripts/seed_sample_project.py http://localhost:8765
    python scripts/seed_sample_project.py http://localhost:8765 --videos-dir ./videos
    python scripts/seed_sample_project.py http://localhost:8765 --force
"""

from __future__ import annotations

import argparse
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx

PROJECT_NAME = "Running Montage"

# Ordered list of the 4 videos used (subset of 6 in /videos/)
SAMPLE_VIDEOS = [
    "78888-568004778_medium.mp4",
    "running1.mp4",
    "running2.mp4",
    "81872-577880797_medium.mp4",
]

# Clip definitions: (video_index, in_point_frames, out_point_frames, timeline_position_frames)
# All values are integer frame counts at the 30fps project output rate
CLIP_DEFS = [
    (0, 60, 300, 0),  # Clip 1: establishing shot, 2s-10s
    (1, 90, 540, 300),  # Clip 2: running 1, 3s-18s
    (2, 30, 360, 750),  # Clip 3: running 2, 1s-12s
    (3, 150, 450, 1080),  # Clip 4: outro, 5s-15s
]

# Effects: (clip_index, effect_type, parameters)
# Uses registered API effect names, not FFmpeg filter names
EFFECT_DEFS = [
    (0, "video_fade", {"fade_type": "in", "start_time": 0.0, "duration": 1.0}),
    (0, "text_overlay", {"text": "Running Montage", "fontsize": 64, "fontcolor": "white"}),
    (1, "speed_control", {"factor": 0.75}),
    (3, "text_overlay", {"text": "The End", "fontsize": 48, "fontcolor": "white"}),
    (3, "video_fade", {"fade_type": "out", "start_time": 8.0, "duration": 2.0}),
]

# Transitions: (source_clip_index, target_clip_index, transition_type, parameters)
TRANSITION_DEFS = [
    (1, 2, "xfade", {"transition": "fade", "duration": 1.0, "offset": 0.0}),
]


@dataclass
class SeedResult:
    """Result of seeding the sample project."""

    project_id: str
    video_ids: list[str]
    clip_ids: list[str]
    effects_applied: int
    transitions_applied: int


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Seed the 'Running Montage' sample project")
    parser.add_argument(
        "base_url",
        help="Base URL of the running stoat-and-ferret instance (e.g., http://localhost:8765)",
    )
    parser.add_argument(
        "--videos-dir",
        default="videos",
        help="Path to directory containing the video files (default: ./videos)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Delete existing sample project and recreate",
    )
    return parser.parse_args()


def find_existing_project(client: httpx.Client) -> str | None:
    """Search for an existing project named 'Running Montage'."""
    resp = client.get("/api/v1/projects", params={"limit": 100})
    resp.raise_for_status()
    for proj in resp.json()["projects"]:
        if proj["name"] == PROJECT_NAME:
            return str(proj["id"])
    return None


def delete_project(client: httpx.Client, project_id: str) -> None:
    """Delete an existing project."""
    resp = client.delete(f"/api/v1/projects/{project_id}")
    resp.raise_for_status()


def scan_and_wait(client: httpx.Client, videos_dir: str) -> None:
    """Submit a video scan job and poll until completion."""
    resp = client.post(
        "/api/v1/videos/scan",
        json={"path": videos_dir, "recursive": True},
    )
    resp.raise_for_status()
    job_id = resp.json()["job_id"]

    for _ in range(60):  # 30 seconds max (60 * 0.5s)
        status_resp = client.get(f"/api/v1/jobs/{job_id}")
        status_resp.raise_for_status()
        status = status_resp.json()["status"].lower()
        if status in ("complete", "failed", "timeout", "cancelled"):
            if status != "complete":
                print(f"ERROR: Scan failed with status: {status}", file=sys.stderr)
                sys.exit(1)
            return
        time.sleep(0.5)

    print("ERROR: Scan timed out after 30 seconds", file=sys.stderr)
    sys.exit(1)


def resolve_video_ids(client: httpx.Client, filenames: list[str]) -> list[str]:
    """Map sample video filenames to their database IDs."""
    resp = client.get("/api/v1/videos", params={"limit": 100})
    resp.raise_for_status()
    videos = resp.json()["videos"]
    name_to_id: dict[str, str] = {v["filename"]: v["id"] for v in videos}

    ids: list[str] = []
    for fn in filenames:
        if fn not in name_to_id:
            print(
                f"ERROR: Video '{fn}' not found in library. "
                "Ensure videos are in the specified directory.",
                file=sys.stderr,
            )
            sys.exit(1)
        ids.append(name_to_id[fn])
    return ids


def seed_project(client: httpx.Client, video_ids: list[str]) -> SeedResult:
    """Create the full sample project with clips, effects, and transitions."""
    # 1. Create project with output settings
    resp = client.post(
        "/api/v1/projects",
        json={
            "name": PROJECT_NAME,
            "output_width": 1280,
            "output_height": 720,
            "output_fps": 30,
        },
    )
    resp.raise_for_status()
    project_id = resp.json()["id"]

    # 2. Add clips
    clip_ids: list[str] = []
    for video_idx, in_pt, out_pt, tl_pos in CLIP_DEFS:
        resp = client.post(
            f"/api/v1/projects/{project_id}/clips",
            json={
                "source_video_id": video_ids[video_idx],
                "in_point": in_pt,
                "out_point": out_pt,
                "timeline_position": tl_pos,
            },
        )
        resp.raise_for_status()
        clip_ids.append(resp.json()["id"])

    # 3. Apply effects
    effects_applied = 0
    for clip_idx, effect_type, params in EFFECT_DEFS:
        resp = client.post(
            f"/api/v1/projects/{project_id}/clips/{clip_ids[clip_idx]}/effects",
            json={"effect_type": effect_type, "parameters": params},
        )
        resp.raise_for_status()
        effects_applied += 1

    # 4. Apply transitions
    transitions_applied = 0
    for src_idx, tgt_idx, trans_type, params in TRANSITION_DEFS:
        resp = client.post(
            f"/api/v1/projects/{project_id}/effects/transition",
            json={
                "source_clip_id": clip_ids[src_idx],
                "target_clip_id": clip_ids[tgt_idx],
                "transition_type": trans_type,
                "parameters": params,
            },
        )
        resp.raise_for_status()
        transitions_applied += 1

    return SeedResult(
        project_id=project_id,
        video_ids=video_ids,
        clip_ids=clip_ids,
        effects_applied=effects_applied,
        transitions_applied=transitions_applied,
    )


def verify_project(client: httpx.Client, result: SeedResult) -> None:
    """Verify the created project matches expectations."""
    # Check project settings
    resp = client.get(f"/api/v1/projects/{result.project_id}")
    resp.raise_for_status()
    proj = resp.json()
    assert proj["name"] == PROJECT_NAME, f"Name mismatch: {proj['name']}"
    assert proj["output_width"] == 1280, f"Width mismatch: {proj['output_width']}"
    assert proj["output_height"] == 720, f"Height mismatch: {proj['output_height']}"
    assert proj["output_fps"] == 30, f"FPS mismatch: {proj['output_fps']}"

    # Check clip count
    resp = client.get(f"/api/v1/projects/{result.project_id}/clips")
    resp.raise_for_status()
    clips_data = resp.json()
    assert clips_data["total"] == len(CLIP_DEFS), (
        f"Expected {len(CLIP_DEFS)} clips, got {clips_data['total']}"
    )


def print_summary(result: SeedResult) -> None:
    """Print a human-readable summary of the created project."""
    print(f"\n{'=' * 50}")
    print(f"Sample Project '{PROJECT_NAME}' created successfully!")
    print(f"{'=' * 50}")
    print(f"  Project ID:    {result.project_id}")
    print(f"  Videos used:   {len(result.video_ids)}")
    print(f"  Clips added:   {len(result.clip_ids)}")
    print(f"  Effects:       {result.effects_applied}")
    print(f"  Transitions:   {result.transitions_applied}")
    print("  Output:        1280x720 @ 30fps")
    print("  Duration:      ~46.0s (1380 frames)")
    print(f"{'=' * 50}\n")


def main() -> None:
    """Run the seed script."""
    args = parse_args()
    base_url = args.base_url.rstrip("/")
    videos_dir = str(Path(args.videos_dir).resolve())

    with httpx.Client(base_url=base_url, timeout=60.0) as client:
        # 1. Health check
        try:
            resp = client.get("/health/live")
            if resp.status_code != 200:
                print(f"ERROR: Server not reachable at {base_url}", file=sys.stderr)
                sys.exit(1)
        except httpx.ConnectError:
            print(f"ERROR: Cannot connect to server at {base_url}", file=sys.stderr)
            sys.exit(1)

        # 2. Check for existing project
        existing_id = find_existing_project(client)
        if existing_id:
            if args.force:
                print(f"Deleting existing sample project {existing_id}...")
                delete_project(client, existing_id)
            else:
                print(
                    f"Sample project already exists (ID: {existing_id}). Use --force to recreate."
                )
                sys.exit(0)

        # 3. Scan videos
        print(f"Scanning videos from {videos_dir}...")
        scan_and_wait(client, videos_dir)

        # 4. Resolve video IDs
        video_ids = resolve_video_ids(client, SAMPLE_VIDEOS)

        # 5. Seed the project
        print("Creating sample project...")
        result = seed_project(client, video_ids)

        # 6. Verify
        print("Verifying...")
        verify_project(client, result)

        # 7. Print summary
        print_summary(result)


if __name__ == "__main__":
    main()

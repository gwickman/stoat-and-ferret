# Sample Project Design: Running Montage

**Project:** stoat-and-ferret — AI-driven video editor with hybrid Python/Rust architecture

## Overview

The "Running Montage" is a canonical sample editing project that uses the real video files in `/videos/` to demonstrate stoat-and-ferret's core features: clips with in/out points, video effects (fade, text overlay, speed control), and crossfade transitions. It is a pre-defined, reproducible project that can be created programmatically via a seed script.

## Why It Exists

1. **Developer onboarding:** New developers can seed the project and immediately see a complete, working example of what stoat-and-ferret produces — clips, effects, transitions, and timeline composition all in one project.

2. **Regression anchor:** The seed script creates a deterministic project with known values. Automated tests can verify the API responses match expectations, catching regressions in project/clip/effect creation.

3. **Stakeholder demo:** The sample project provides a ready-made demonstration of the system's capabilities without requiring manual setup.

## Three Components

1. **The project definition** — A detailed specification of the sample project: which videos, which clips (in/out points, timeline positions), which effects and transitions, and output settings.

2. **The seed script** — `scripts/seed_sample_project.py` — A standalone Python script that creates the sample project by making HTTP requests to a running stoat-and-ferret instance. Supports `--force` to recreate.

3. **The user guide** — `docs/setup/guides/sample-project.md` — A developer-facing guide explaining how to use the seed script, what gets created, and how to explore the result. (Specified in this design; the guide itself is a future deliverable.)

## Current Status

**Designed, not yet built.** This document set contains the complete specification for implementation. No code has been written yet.

## Files in This Folder

| File | Contents |
|------|----------|
| [01-project-definition.md](./01-project-definition.md) | Video selection, clip definitions, effects, transitions, output settings, timeline diagram |
| [02-seed-script.md](./02-seed-script.md) | Seed script design: usage, constants, function signatures, error handling, pseudocode |
| [03-smoke-test-integration.md](./03-smoke-test-integration.md) | How the sample project integrates with the smoke test suite |
| [04-user-guide-spec.md](./04-user-guide-spec.md) | Specification for the user-facing guide document |

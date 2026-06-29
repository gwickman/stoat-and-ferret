# BL-517: Multi-Track Audio Data Model

**Version:** v091
**Status:** implemented

## Summary

Extends the `tracks` table with per-track audio fields (`kind`, `volume_envelope`, `weight`) and introduces the `ducking_pair` table for voice-triggered music ducking configuration.

## Acceptance criteria implemented

- Track table gains `kind` (TEXT nullable), `volume_envelope` (TEXT nullable), `weight` (REAL DEFAULT 1.0)
- `ducking_pair` table created with `ducked_track_id`, `sidechain_track_id`, compressor params, and CHECK constraint enforcing `ducked_track_id != sidechain_track_id`
- REST endpoints: POST/GET/PATCH/DELETE `/api/v1/projects/{project_id}/ducking_pairs`
- `DuckingPairCreate` Pydantic model enforces all parameter ranges and the ducked≠sidechain invariant

## Out of scope

- 5.1 / 7.1 surround audio channel layouts
- More than 4 tracks in the mixer schema
- Real-time ducking preview during editing
- DSP/renderer integration (Feature 002 in v091)

## Default parameters

Evidence-backed from PoC Track 3 retest (2026-06-15):

| Parameter | Default | Rationale |
|-----------|---------|-----------|
| threshold | 0.02 | 9.68 dB music attenuation measured at voice presence |
| ratio | 8 | Wellness-target ducking depth |
| attack_ms | 20 | Crisp onset, perceptually clean |
| release_ms | 300 | Natural music fade-in after voice |

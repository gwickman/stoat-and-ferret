# Rendering Guide

> **[Planned]** -- Rendering and export functionality is not yet implemented in Stoat & Ferret. This document describes the planned API and capabilities based on design documents. All features described below should be considered future plans and are subject to change.

## Overview

The rendering system will assemble a project's timeline into a final output video file. It will combine clips, apply effects (using the generated FFmpeg filter strings), and encode the result according to the project's output settings.

## Planned API

### POST /api/v1/render/start **[Planned]**

Start a render job for a project.

**Planned Request Body:**

```json
{
  "project_id": "proj-xyz789",
  "output_path": "/output/final.mp4",
  "quality": {
    "preset": "high",
    "video_codec": "libx264",
    "audio_codec": "aac",
    "video_bitrate": "8M",
    "audio_bitrate": "192k",
    "crf": 18
  },
  "hardware_acceleration": {
    "enabled": false,
    "encoder": null
  }
}
```

**Planned Response (202 Accepted):**

```json
{
  "job_id": "render-abc123",
  "project_id": "proj-xyz789",
  "status": "pending"
}
```

### GET /api/v1/render/status/{job_id} **[Planned]**

Get the status and progress of a render job.

**Planned Response:**

```json
{
  "job_id": "render-abc123",
  "status": "running",
  "progress": 45.2,
  "current_phase": "encoding",
  "elapsed_seconds": 120,
  "estimated_remaining_seconds": 147,
  "output_path": "/output/final.mp4"
}
```

**Planned Job Statuses:**

| Status | Description |
|--------|-------------|
| `pending` | Render job is queued |
| `running` | Currently rendering |
| `complete` | Render finished successfully |
| `failed` | Render failed with error |
| `cancelled` | Render was cancelled by user |

### POST /api/v1/render/cancel/{job_id} **[Planned]**

Cancel a running render job.

**Planned Response:**

```json
{
  "job_id": "render-abc123",
  "status": "cancelled"
}
```

### GET /api/v1/render/jobs **[Planned]**

List all render jobs with optional filtering.

**Planned Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `project_id` | string | Filter by project |
| `status` | string | Filter by status |
| `limit` | integer | Pagination limit |
| `offset` | integer | Pagination offset |

## Planned Quality Options

### Video Presets **[Planned]**

| Preset | Codec | CRF | Bitrate | Description |
|--------|-------|-----|---------|-------------|
| `draft` | libx264 | 28 | -- | Fast preview quality |
| `medium` | libx264 | 23 | -- | Balanced quality/speed |
| `high` | libx264 | 18 | -- | High quality, larger file |
| `lossless` | libx264 | 0 | -- | Lossless encoding |

### Audio Options **[Planned]**

| Codec | Bitrate | Description |
|-------|---------|-------------|
| `aac` | 128k-320k | Standard AAC |
| `pcm_s16le` | -- | Uncompressed 16-bit |
| `flac` | -- | Lossless compression |

### Hardware Acceleration **[Planned]**

The rendering system is planned to support hardware-accelerated encoding where available:

| Platform | Encoder | Description |
|----------|---------|-------------|
| NVIDIA | `h264_nvenc` | NVIDIA GPU encoding |
| AMD | `h264_amf` | AMD GPU encoding |
| Intel | `h264_qsv` | Intel Quick Sync |
| macOS | `h264_videotoolbox` | Apple VideoToolbox |

Hardware acceleration will be opt-in and fall back to software encoding if the requested hardware encoder is not available.

## Planned Render Pipeline

The planned rendering pipeline will:

1. **Validate** -- Check that the project timeline is complete and all source files exist
2. **Build filter graph** -- Assemble the FFmpeg filter graph from clip effects and transitions
3. **Execute** -- Run FFmpeg with the generated filter graph and encoding settings
4. **Monitor** -- Track progress via FFmpeg output parsing, reporting percentage complete
5. **Finalize** -- Verify the output file and update job status

The pipeline will leverage the existing FFmpeg executor infrastructure and job queue system that currently powers video scanning.

## Planned Output Formats **[Planned]**

| Container | Extension | Typical Codecs |
|-----------|-----------|----------------|
| MP4 | `.mp4` | H.264 + AAC |
| MOV | `.mov` | H.264 + AAC, ProRes |
| MKV | `.mkv` | H.264/H.265 + AAC/FLAC |
| WebM | `.webm` | VP9 + Opus |

## Current State

While rendering is not yet implemented, the building blocks are in place:

- **Effect system** generates valid FFmpeg filter strings (see [Effects Guide](04_effects-guide.md))
- **Timeline model** tracks clip ordering and positions (see [Timeline Guide](05_timeline-guide.md))
- **Job queue** provides async job execution infrastructure
- **FFmpeg executor** wraps FFmpeg process management with timeout and error handling

## Next Steps

- [Effects Guide](04_effects-guide.md) -- current effect system that generates filter strings
- [Timeline Guide](05_timeline-guide.md) -- building timelines for rendering
- [API Reference](03_api-reference.md) -- currently available endpoints

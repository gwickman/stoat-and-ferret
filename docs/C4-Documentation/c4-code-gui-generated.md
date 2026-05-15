# C4 Code Level: Generated API Types

## Overview

- **Name**: Generated API Types
- **Description**: Auto-generated OpenAPI TypeScript type definitions providing strongly-typed API communication between frontend and backend services.
- **Location**: gui/src/generated
- **Language**: TypeScript
- **Purpose**: Centralized source of truth for API schema types, eliminating manual interface duplication and ensuring type safety across all API consumers.
- **Parent Component**: [Web GUI](./c4-component-web-gui.md)

## Code Elements

### Type Aliases (from types.ts)

Convenience type aliases re-exporting schema types from the OpenAPI definition:

- `Effect`: Alias for `EffectResponse` - Effect metadata with parameter schema and preview
- `Project`: Alias for `ProjectResponse` - Project metadata including dimensions and framerate
- `Clip`: Alias for `ClipResponse` - Timeline clip with in/out points and effects
- `Video`: Alias for `VideoResponse` - Source video metadata
- `Track`: Alias for `TrackResponse` - Timeline track containing clips
- `LayoutPosition`: Alias for `LayoutResponsePosition` - Positioned element with x, y, width, height, z_index
- `LayoutPreset`: Alias for `LayoutPresetResponse` - Predefined layout configuration with AI hints
- `TimelineClip`: Alias for `TimelineClipResponse` - Timeline-aware clip representation
- `TimelineResponse`: Timeline with all clips and tracks
- `LayoutPresetListResponse`: Paginated list of layout presets
- `ProxyStatus`: Union type `"pending" | "generating" | "ready" | "failed" | "stale"`
- `ProxyQuality`: Union type `"low" | "medium" | "high"`
- `SortField`: Union type `'date' | 'name' | 'duration'` (frontend-only)
- `SortOrder`: Union type `'asc' | 'desc'` (frontend-only)

### Core Entity Schemas

#### ProjectResponse
- `id: string` - UUID
- `name: string` - Project name
- `output_width: number` - Output video width in pixels (default: 1920)
- `output_height: number` - Output video height in pixels (default: 1080)
- `output_fps: number` - Output frames per second (default: 30)
- `created_at: string` - ISO 8601 timestamp
- `updated_at: string` - ISO 8601 timestamp

#### VideoResponse
- `id: string` - UUID
- `project_id: string` - Parent project UUID
- `file_path: string` - Full path to source video file
- `duration_seconds: number` - Video duration
- `width: number` - Video width in pixels
- `height: number` - Video height in pixels
- `fps: number` - Video framerate
- `created_at: string` - ISO 8601 timestamp
- `updated_at: string` - ISO 8601 timestamp

#### ClipResponse
- `id: string` - UUID
- `project_id: string` - Parent project UUID
- `source_video_id: string` - Source video reference
- `in_point: number` - Clip start in source (seconds)
- `out_point: number` - Clip end in source (seconds)
- `timeline_position: number` - Position on timeline (seconds)
- `effects?: object[] | null` - Array of applied effects
- `created_at: string` - ISO 8601 timestamp
- `updated_at: string` - ISO 8601 timestamp

#### TrackResponse
- `id: string` - UUID
- `project_id: string` - Parent project UUID
- `name: string` - Track name
- `index: number` - Track order in timeline
- `is_locked: boolean` - Edit lock flag
- `created_at: string` - ISO 8601 timestamp
- `updated_at: string` - ISO 8601 timestamp

#### TimelineClipResponse
- `id: string` - UUID
- `track_id: string` - Parent track reference
- `video_id: string` - Source video reference
- `in_point: number` - Clip start in source
- `out_point: number` - Clip end in source
- `timeline_start: number` - Position on timeline
- `created_at: string` - ISO 8601 timestamp
- `updated_at: string` - ISO 8601 timestamp

### Effect Schemas

#### EffectResponse
- `effect_type: string` - Effect identifier (e.g., 'blur', 'brightness')
- `name: string` - Display name
- `description: string` - User-facing description
- `parameter_schema: object` - JSON Schema for parameters
- `ai_hints: object` - AI prompt suggestions per parameter
- `filter_preview: string` - FFmpeg filter syntax preview

#### EffectApplyRequest
- `effect_type: string` - Effect identifier
- `parameters: object` - Parameter values

#### EffectApplyResponse
- `effect_type: string` - Applied effect type
- `parameters: object` - Resolved parameters
- `filter_string: string` - Generated FFmpeg filter

#### EffectPreviewRequest
- `effect_type: string` - Effect to preview
- `parameters: object` - Parameter values

#### EffectPreviewResponse
- `effect_type: string` - Effect type
- `filter_string: string` - Generated FFmpeg filter

#### EffectUpdateRequest
- `parameters: object` - New parameter values

#### EffectDeleteResponse
- `index: number` - Deleted effect index
- `deleted_effect_type: string` - Type of removed effect

#### EffectListResponse
- `effects: EffectResponse[]` - Available effects
- `total: number` - Total effect count

#### EffectThumbnailRequest
- `effect_type: string` - Effect to preview
- `video_path: string` - Video file path
- `parameters: object` - Effect parameters

#### EffectTransitionResponse
- `id: string` - UUID
- `source_clip_id: string` - Source clip reference
- `target_clip_id: string` - Target clip reference
- `transition_type: string` - Transition identifier
- `parameters: object` - Transition parameters
- `filter_string: string` - Generated FFmpeg filter

### Layout Schemas

#### LayoutPresetResponse
- `name: string` - Preset identifier (e.g., 'PipTopLeft', 'Grid2x2')
- `description: string` - User-facing description
- `ai_hint: string` - AI prompt suggestion
- `min_inputs: number` - Minimum number of inputs
- `max_inputs: number` - Maximum number of inputs
- `positions: LayoutResponsePosition[]` - Default positions

#### LayoutResponsePosition
- `x: number` - Horizontal position (0-1920 default)
- `y: number` - Vertical position (0-1080 default)
- `width: number` - Element width in pixels
- `height: number` - Element height in pixels
- `z_index: number` - Stack order

#### LayoutRequest
- `preset?: string | null` - Preset name OR custom positions
- `positions?: PositionModel[] | null` - Custom positions (normalized 0.0-1.0)
- `input_count: number` - Number of inputs (default: 2)
- `output_width: number` - Output width in pixels (default: 1920)
- `output_height: number` - Output height in pixels (default: 1080)

#### LayoutResponse
- `positions: LayoutResponsePosition[]` - Resolved positions
- `filter_preview: string` - FFmpeg filter syntax

#### PositionModel
- `x: number` - Normalized x coordinate (0.0-1.0)
- `y: number` - Normalized y coordinate (0.0-1.0)
- `width: number` - Normalized width (0.0-1.0)
- `height: number` - Normalized height (0.0-1.0)

### Render Job Schemas

#### CreateRenderRequest
- `project_id: string` - Project to render
- `output_format: string` - Container format (default: 'mp4')
- `quality_preset: string` - Quality level (default: 'standard')
- `render_plan: string` - Serialized render plan JSON (default: '{}')

#### RenderJobResponse
- `id: string` - UUID
- `project_id: string` - Parent project reference
- `status: string` - Job state (pending, running, completed, failed)
- `output_path: string` - Output file path
- `output_format: string` - Container format
- `quality_preset: string` - Quality preset used
- `progress: number` - Progress percentage (0-100)
- `error_message?: string | null` - Failure reason
- `retry_count: number` - Number of retries
- `created_at: string` - ISO 8601 timestamp
- `updated_at: string` - ISO 8601 timestamp
- `completed_at?: string | null` - Completion timestamp

#### RenderListResponse
- `jobs: RenderJobResponse[]` - Paginated job list
- `total: number` - Total job count

### Proxy Schemas

#### ProxyResponse
- `id: string` - UUID
- `source_video_id: string` - Source video reference
- `status: ProxyStatus` - Generation state
- `quality: ProxyQuality` - Preset quality level
- `file_size_bytes: number` - Proxy file size
- `generated_at?: string | null` - Generation timestamp

#### ProxyBatchRequest
- `video_ids: string[]` - Videos to generate proxies for

#### ProxyBatchResponse
- `queued: string[]` - Queued video IDs
- `skipped: string[]` - Skipped video IDs

#### ProxyDeleteResponse
- `freed_bytes: number` - Recovered disk space

### Encoder and Format Schemas

#### EncoderInfoResponse
- `name: string` - Encoder identifier
- `codec: string` - Codec name
- `is_hardware: boolean` - Hardware acceleration flag
- `encoder_type: string` - Encoder category
- `description: string` - Human-readable description
- `detected_at: string` - ISO 8601 timestamp

#### EncoderListResponse
- `encoders: EncoderInfoResponse[]` - Detected encoders
- `cached: boolean` - Cache hit flag

#### CodecInfo
- `name: string` - Codec identifier (h264, vp9)
- `quality_presets: QualityPresetInfo[]` - Bitrate per quality level

#### QualityPresetInfo
- `preset: string` - Quality level name (draft, standard, high)
- `video_bitrate_kbps: number` - Target bitrate in kilobits/second

#### FormatInfo
- `format: string` - Format identifier (mp4, webm, mov, mkv)
- `extension: string` - File extension with dot (.mp4)
- `mime_type: string` - MIME type string
- `codecs: CodecInfo[]` - Supported codecs
- `supports_hw_accel: boolean` - Hardware acceleration support
- `supports_two_pass: boolean` - Two-pass encoding support
- `supports_alpha: boolean` - Alpha channel transparency support

#### FormatListResponse
- `formats: FormatInfo[]` - All available output formats

### Preview and Cache Schemas

#### PreviewStartRequest
- `quality: string` - Quality level (low, medium, high; default: medium)

#### PreviewStartResponse
- `session_id: string` - Unique preview session identifier

#### PreviewStatusResponse
- `session_id: string` - Session identifier
- `status: string` - Session state
- `manifest_url?: string | null` - HLS manifest URL
- `error_message?: string | null` - Error description

#### PreviewSeekRequest
- `position: number` - Seek position in seconds

#### PreviewSeekResponse
- `session_id: string` - Session identifier
- `status: string` - Session state after seek

#### PreviewStopResponse
- `session_id: string` - Session identifier
- `stopped: boolean` - Confirmation flag (default: true)

#### PreviewCacheStatusResponse
- `active_sessions: number` - Currently active preview sessions
- `used_bytes: number` - Cache memory in use
- `max_bytes: number` - Maximum cache memory
- `usage_percent: number` - Cache utilization percentage
- `sessions: string[]` - Active session IDs

#### PreviewCacheClearResponse
- `cleared_sessions: number` - Sessions cleared
- `freed_bytes: number` - Memory freed

### Metadata Schemas

#### DirectoryEntry
- `name: string` - Directory name
- `path: string` - Full path to directory

#### DirectoryListResponse
- `path: string` - Parent directory path
- `directories: DirectoryEntry[]` - Subdirectories
- `total: number` - Total directory count
- `limit: number` - Pagination limit
- `offset: number` - Pagination offset

#### QueueStatusResponse
- `active_count: number` - Running render jobs
- `pending_count: number` - Queued jobs
- `max_concurrent: number` - Concurrent job limit
- `max_queue_depth: number` - Queue size limit
- `disk_available_bytes: number` - Available disk space
- `disk_total_bytes: number` - Total disk space
- `completed_today: number` - Jobs completed since UTC midnight
- `failed_today: number` - Jobs failed since UTC midnight

### API Operation Interfaces

#### paths
Defines API endpoints structure with HTTP method signatures for:
- `/health/live` - Liveness probe
- `/health/ready` - Readiness probe with dependency checks
- `/clips`, `/clips/{id}` - Clip CRUD
- `/tracks`, `/tracks/{id}` - Track CRUD
- `/effects`, `/effects/{id}` - Effect catalog
- `/layouts`, `/layouts/presets` - Layout operations
- `/previews` - Preview session management
- `/proxies` - Proxy generation and management
- `/projects`, `/projects/{id}` - Project CRUD
- `/render` - Render job submission and status
- `/videos` - Video library management
- And many more video editing operations

#### components
Defines reusable schema components and operations, organized into:
- `schemas`: All type definitions
- `responses`: Standardized response shapes
- `parameters`: Shared parameter definitions

## Dependencies

### Internal Dependencies
- `types.ts` imports `api-types.ts` to create convenience aliases

### External Dependencies
- Generated by `openapi-typescript` from backend OpenAPI spec
- No runtime dependencies (pure type definitions)

## Relationships

```mermaid
---
title: Generated API Types Module Structure
---
classDiagram
    namespace APITypes {
        class "api-types.ts" {
            <<generated>>
            +paths
            +components
            -schemas: object
            -operations: object
        }
        class "types.ts" {
            +Effect
            +Project
            +Clip
            +Video
            +Track
            +LayoutPosition
            +LayoutPreset
            +TimelineClip
            +SortField
            +SortOrder
            +ProxyStatus
            +ProxyQuality
        }
    }

    namespace CoreEntities {
        class "ProjectResponse" {
            +id: string
            +name: string
            +output_width: number
            +output_height: number
            +output_fps: number
            +created_at: string
            +updated_at: string
        }
        class "VideoResponse" {
            +id: string
            +file_path: string
            +duration_seconds: number
            +width: height
        }
        class "ClipResponse" {
            +id: string
            +source_video_id: string
            +in_point: number
            +out_point: number
        }
        class "TrackResponse" {
            +id: string
            +name: string
            +is_locked: boolean
        }
    }

    namespace Effects {
        class "EffectResponse" {
            +effect_type: string
            +name: string
            +parameter_schema: object
            +filter_preview: string
        }
        class "EffectApplyRequest" {
            +effect_type: string
            +parameters: object
        }
    }

    namespace Layouts {
        class "LayoutPresetResponse" {
            +name: string
            +positions: LayoutResponsePosition[]
        }
        class "LayoutRequest" {
            +preset: string
            +positions: PositionModel[]
        }
    }

    namespace Rendering {
        class "RenderJobResponse" {
            +id: string
            +status: string
            +progress: number
            +output_path: string
        }
        class "CreateRenderRequest" {
            +project_id: string
            +output_format: string
            +quality_preset: string
        }
    }

    "types.ts" -->|re-exports from| "api-types.ts"
    "api-types.ts" -->|defines| "ProjectResponse"
    "api-types.ts" -->|defines| "VideoResponse"
    "api-types.ts" -->|defines| "ClipResponse"
    "api-types.ts" -->|defines| "TrackResponse"
    "api-types.ts" -->|defines| "EffectResponse"
    "api-types.ts" -->|defines| "LayoutPresetResponse"
    "api-types.ts" -->|defines| "RenderJobResponse"
```

## Notes

- This is an **auto-generated file** produced by `openapi-typescript` from the backend's OpenAPI specification. Do not edit directly; regenerate if the API schema changes.
- The `types.ts` file provides a stable re-export layer, allowing frontend code to import from a single source (`types.ts`) rather than directly from the large `api-types.ts`.
- All datetime fields use ISO 8601 format strings.
- Normalized coordinates in `PositionModel` are in range 0.0-1.0 for layout flexibility across different output dimensions.
- Union types like `ProxyStatus` and `ProxyQuality` are enums at runtime but typed as string literals for strict type checking.

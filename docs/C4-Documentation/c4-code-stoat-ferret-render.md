# C4 Code Level: Render Job Pipeline

## Overview

- **Name**: Render Job Pipeline
- **Description**: Batch video rendering with job queuing, executor management, crash recovery
- **Location**: src/stoat_ferret/render/
- **Language**: Python
- **Purpose**: Orchestrates full render job lifecycle
- **Parent Component**: [Application Services](./c4-component-application-services.md)

## Code Elements

### Enumerations

- RenderStatus (str enum): QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED
  Location: models.py:15-27

- OutputFormat (str enum): MP4, WEBM, MOV, MKV
  Location: models.py:30-36

- QualityPreset (str enum): DRAFT, STANDARD, HIGH
  Location: models.py:39-44

### Data Classes

- RenderJob: Main job model with state machine methods
  Location: models.py:75-215
  Attributes: id, project_id, status, output_path, output_format, quality_preset, render_plan, progress, error_message, retry_count, timestamps

### Classes

- RenderCheckpointManager: Manages per-segment render checkpoints
  Location: checkpoints.py:18-151
  Key Methods: write_checkpoint, get_completed_segments, recover, cleanup_stale

- RenderQueue: Persistent FIFO queue with concurrency limits
  Location: queue.py:35-177
  Key Methods: enqueue, dequeue, recover

- RenderExecutor: FFmpeg subprocess lifecycle management
  Location: executor.py:34-447
  Key Methods: execute, cancel, cancel_all, kill_remaining

- RenderService: Complete job lifecycle orchestration
  Location: service.py:73-400
  Key Methods: submit_job, run_job, cancel_job, recover

### Repository Implementations

- AsyncSQLiteRenderRepository: SQLite implementation
  Location: render_repository.py:141-353

- InMemoryRenderRepository: In-memory test implementation
  Location: render_repository.py:356-456

### Encoder Cache

#### `encoder_cache.py`

**File**: `src/stoat_ferret/render/encoder_cache.py`

Provides hardware encoder detection result caching using SQLite.

| Class / Type | Description |
|---|---|
| `EncoderCacheEntry` | Dataclass storing encoder name, type, availability status, and detection timestamp |
| `AsyncEncoderCacheRepository` | Abstract Protocol type for encoder cache persistence — pluggable implementation |
| `AsyncSQLiteEncoderCacheRepository` | Concrete SQLite implementation of `AsyncEncoderCacheRepository` using aiosqlite |

## Dependencies

Internal: stoat_ferret.api.settings, .api.websocket, .render.metrics, stoat_ferret_core
External: asyncio, aiosqlite, structlog, pathlib, datetime

## Relationships

```mermaid
---
title: Render Job Pipeline Architecture
---
classDiagram
    namespace RenderPipeline {
        class RenderStatus {
            QUEUED
            RUNNING
            COMPLETED
            FAILED
            CANCELLED
        }
        
        class RenderJob {
            +id: str
            +status: RenderStatus
            +progress: float
            +create()
            +complete()
            +fail()
            +cancel()
        }
        
        class RenderQueue {
            +async enqueue(job)
            +async dequeue()
            +async recover()
        }
        
        class RenderExecutor {
            +async execute(job, command)
            +async cancel(job_id)
        }
        
        class RenderService {
            +async submit_job()
            +async run_job()
            +async cancel_job()
        }
    }
    
    RenderJob --> RenderStatus: has
    RenderQueue --> RenderJob: queues
    RenderService --> RenderQueue: uses
    RenderService --> RenderExecutor: uses
    RenderExecutor --> RenderJob: executes
```

## Notes

- State machine enforces valid transitions; retry moves failed to queued
- Progress throttling at 0.5s intervals to reduce broadcast overhead
- Executor uses stdin q for graceful FFmpeg shutdown (cross-platform)
- Checkpoints enable crash recovery with segment-level resumption
- All timestamps use UTC with timezone awareness
- Pre-flight checks validate settings via Rust bindings and disk space
- Queue persisted in database; recovers from server restart
- Per-job retry count tracked and incremented on transition to queued

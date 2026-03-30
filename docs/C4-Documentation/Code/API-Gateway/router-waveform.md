# Waveform Router

**Source:** `src/stoat_ferret/api/routers/waveform.py`
**Component:** API Gateway

## Purpose

Waveform generation and serving for audio visualization. Provides endpoints to queue waveform generation in PNG (image) or JSON (amplitude data) formats, retrieve metadata, and serve generated files.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/videos/{video_id}/waveform | Queue waveform generation (202 Accepted) |
| GET | /api/v1/videos/{video_id}/waveform | Get waveform metadata |
| GET | /api/v1/videos/{video_id}/waveform.png | Serve waveform as PNG image |
| GET | /api/v1/videos/{video_id}/waveform.json | Serve waveform amplitude data as JSON |

### Functions

- `generate_waveform(video_id: str, background_tasks: BackgroundTasks, video_repo: VideoRepoDep, waveform_service: WaveformServiceDep, body: WaveformGenerateRequest | None=None) -> WaveformGenerateResponse`: Validates video exists, determines format (png or json), creates waveform_id, adds generation task. Returns 202 Accepted with waveform_id and "pending" status. Raises 404 if video not found.

- `get_waveform_metadata(video_id: str, waveform_service: WaveformServiceDep, format: str="png") -> WaveformMetadataResponse`: Retrieves waveform metadata (status, format, duration, channels). Computes samples_per_second (0 for PNG, 10 for JSON). Raises 404 if no waveform exists for format.

- `get_waveform_image(video_id: str, waveform_service: WaveformServiceDep) -> FileResponse`: Serves PNG waveform image. Raises 404 if PNG waveform not found or file not ready.

- `get_waveform_json(video_id: str, waveform_service: WaveformServiceDep) -> JSONResponse`: Parses JSON waveform file, constructs WaveformSamplesResponse with samples array, returns as JSON. Raises 404 if JSON waveform not found or file not ready.

### Dependency Functions

- `_get_video_repository(request: Request) -> AsyncVideoRepository`: Gets video repository from app.state or creates from app.state.db.

- `_get_waveform_service(request: Request) -> WaveformService`: Gets waveform service from app.state or raises 503 SERVICE_UNAVAILABLE.

## Key Implementation Details

- **Format selection**: Default format is "png"; request body can override with "json" to generate amplitude data instead

- **Background generation**: Uses FastAPI BackgroundTasks to queue generation asynchronously

- **PNG format**: Generated via FFmpeg showwavespic filter; 1800x140 default resolution with channel-specific colors (blue for mono, blue|red for stereo)

- **JSON format**: Generated via ffprobe with amovie filter source, asetnsamples for 10 samples/second, astats for amplitude extraction; Peak_level and RMS_level values per channel

- **Samples per second**: Metadata indicates 0 for PNG (image-only), 10 for JSON (10 amplitude samples per second of audio)

- **Service dependency**: WaveformService injected from app.state; required for all endpoints (503 if missing)

- **Error responses**: JSON:API-style with code/message fields

- **Dependency injection**: Uses FastAPI Annotated[Type, Depends()] pattern; creates video repo from db if not pre-injected

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.waveform.WaveformGenerateRequest, WaveformGenerateResponse, WaveformMetadataResponse, WaveformSample, WaveformSamplesResponse`: Request/response schemas
- `stoat_ferret.api.services.waveform.WaveformService`: Waveform generation service with generate_png, generate_json, get_waveform methods
- `stoat_ferret.db.async_repository.AsyncVideoRepository, AsyncSQLiteVideoRepository`: Video persistence
- `stoat_ferret.db.models.Waveform, WaveformFormat, WaveformStatus`: Waveform models and enums

### External Dependencies

- `fastapi.APIRouter, BackgroundTasks, Depends, HTTPException, Request, status`: Web framework
- `fastapi.responses.FileResponse, JSONResponse`: Response types
- `pathlib.Path`: File system operations
- `json.loads`: JSON parsing
- `structlog`: Structured logging

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: WaveformService for generation and retrieval, video repository for validation
- **Generates**: Background tasks that call WaveformService.generate_png() or generate_json() asynchronously

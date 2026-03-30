# Proxy Router

**Source:** `src/stoat_ferret/api/routers/proxy.py`
**Component:** API Gateway

## Purpose

Proxy video file generation and management endpoints. Provides endpoints to queue single-video and batch proxy generation, check proxy status, and delete proxies with file cleanup.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | /api/v1/videos/{video_id}/proxy | Queue proxy generation (202 Accepted) |
| GET | /api/v1/videos/{video_id}/proxy | Get proxy status |
| DELETE | /api/v1/videos/{video_id}/proxy | Delete proxy and free disk space |
| POST | /api/v1/proxy/batch | Batch queue proxies for multiple videos (202 Accepted) |

### Functions

- `generate_proxy(video_id: str, request: Request, proxy_repo: ProxyRepoDep, video_repo: VideoRepoDep) -> JobSubmitResponse`: Validates video exists, checks for existing active proxy, submits PROXY_JOB_TYPE to job queue. Returns 202 Accepted with job_id. Raises 404 if video not found, 409 if proxy already exists.

- `get_proxy_status(video_id: str, proxy_repo: ProxyRepoDep) -> ProxyResponse`: Returns most recent proxy status preferring READY state. Raises 404 if no proxy found for video.

- `delete_proxy(video_id: str, proxy_repo: ProxyRepoDep) -> ProxyDeleteResponse`: Deletes all proxies for video including files from disk and DB records. Returns freed_bytes count. Raises 404 if no proxy found.

- `batch_generate_proxies(batch_request: ProxyBatchRequest, request: Request, proxy_repo: ProxyRepoDep, video_repo: VideoRepoDep) -> ProxyBatchResponse`: Queues proxies for multiple videos, skipping those with active proxies or missing videos. Returns lists of queued and skipped video IDs.

### Dependency Functions

- `get_proxy_repository(request: Request) -> AsyncProxyRepository`: Gets proxy repository from app.state or creates from app.state.db.

- `get_video_repository(request: Request) -> AsyncVideoRepository`: Gets video repository from app.state or creates from app.state.db.

## Key Implementation Details

- **Job submission**: Passes video metadata (dimensions, duration in microseconds, path) to job queue with PROXY_JOB_TYPE identifier

- **Existing proxy check**: Filters out FAILED and STALE proxies; any other status blocks generation (PENDING, GENERATING, READY)

- **Proxy selection**: get_proxy_status returns first READY proxy if multiple exist, otherwise first proxy in list

- **Batch handling**: Skips videos that don't exist in repository or have active proxies; returns separate lists of queued and skipped IDs

- **File cleanup**: Uses contextlib.suppress(OSError) for safe file deletion on disk before removing DB record

- **Error responses**: JSON:API-style with code/message fields

- **Dependency injection**: Uses FastAPI Annotated[Type, Depends()] pattern; creates instances from db if not pre-injected

- **Pydantic models**: Inline models ProxyResponse, ProxyDeleteResponse, ProxyBatchRequest, ProxyBatchResponse with ConfigDict(from_attributes=True) for ORM compatibility

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.job.JobSubmitResponse`: Job submission response schema
- `stoat_ferret.api.services.proxy_service.PROXY_JOB_TYPE`: Proxy job type identifier
- `stoat_ferret.db.async_repository.AsyncVideoRepository, AsyncSQLiteVideoRepository`: Video persistence
- `stoat_ferret.db.models.ProxyStatus`: Proxy status enum (PENDING, GENERATING, READY, FAILED, STALE)
- `stoat_ferret.db.proxy_repository.AsyncProxyRepository, SQLiteProxyRepository`: Proxy persistence

### External Dependencies

- `fastapi.APIRouter, Depends, HTTPException, Request, status`: Web framework
- `pydantic.BaseModel, ConfigDict, Field`: Request/response models
- `datetime.datetime`: Timestamp fields
- `structlog`: Structured logging
- `contextlib.suppress`: Safe error handling for file operations
- `os.path.exists, os.remove`: File system operations

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Proxy repository and video repository for data access, job queue for async processing
- **Worked by**: ProxyService which executes PROXY_JOB_TYPE jobs submitted by these endpoints

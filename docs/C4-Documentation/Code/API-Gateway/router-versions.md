# Versions Router

**Source:** `src/stoat_ferret/api/routers/versions.py`
**Component:** API Gateway

## Purpose

Project version listing and restoration endpoints. Manages version history for projects with non-destructive restoration (restoring a version creates a new version rather than overwriting).

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/projects/{project_id}/versions | List versions for project |
| POST | /api/v1/projects/{project_id}/versions/{version}/restore | Restore previous version |

### Functions

- `list_versions(project_id: str, project_repo: ProjectRepoDep, version_repo: VersionRepoDep, limit: int=20, offset: int=0) -> VersionListResponse`: Lists versions for project with pagination (limit 1-100, offset >= 0). Returns version_number, created_at, checksum for each version. 404 if project not found.

- `restore_version(project_id: str, version: int, project_repo: ProjectRepoDep, version_repo: VersionRepoDep) -> RestoreResponse`: Restores previous project version. Non-destructive: restoring version N creates a new version containing the restored data. Returns source version and new version number. 404 if project or version not found.

### Dependency Functions

- `get_project_repository(request: Request) -> AsyncProjectRepository`
- `get_version_repository(request: Request) -> AsyncVersionRepository`

## Key Implementation Details

- **Version semantics**: Each modification to project creates new version; versions are immutable snapshots
- **Non-destructive restore**: Restoring version N doesn't overwrite current state; instead creates new version with restored data, allowing undo of undo
- **Versioning metadata**: Each version has version_number (integer), created_at (timestamp), checksum (for integrity)
- **Pagination**: limit clamped to 1-100; offset must be >= 0
- **Version lookup**: Version repository raises ValueError if requested version doesn't exist; caught and converted to 404

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.version.*`: RestoreResponse, VersionListResponse, VersionResponse
- `stoat_ferret.db.project_repository.AsyncProjectRepository, AsyncSQLiteProjectRepository`: Project persistence
- `stoat_ferret.db.version_repository.AsyncVersionRepository, AsyncSQLiteVersionRepository`: Version persistence

### External Dependencies

- `fastapi`: APIRouter, Depends, HTTPException, Query, Request, status

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Project and version repositories

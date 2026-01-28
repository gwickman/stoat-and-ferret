# Clips API

## Goal
Implement `/projects` and `/projects/{id}/clips` endpoints.

## Requirements

### FR-001: Project Endpoints
- `GET /api/v1/projects` - List projects
- `POST /api/v1/projects` - Create project
- `GET /api/v1/projects/{id}` - Get project
- `DELETE /api/v1/projects/{id}` - Delete project

### FR-002: Clip Endpoints
- `GET /api/v1/projects/{id}/clips` - List clips
- `POST /api/v1/projects/{id}/clips` - Add clip
- `PATCH /api/v1/projects/{id}/clips/{clip_id}` - Update clip
- `DELETE /api/v1/projects/{id}/clips/{clip_id}` - Delete clip

### FR-003: Validation
Validate clips using Rust core before saving.

## Acceptance Criteria
- [ ] All project endpoints implemented
- [ ] All clip endpoints implemented
- [ ] Clips validated before save
- [ ] 404 for unknown project/clip
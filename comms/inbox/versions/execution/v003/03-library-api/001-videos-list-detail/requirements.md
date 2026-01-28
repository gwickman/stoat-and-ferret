# Videos List and Detail

## Goal
Implement `GET /videos` and `GET /videos/{id}` endpoints.

## Requirements

### FR-001: List Videos
`GET /api/v1/videos` with query params:
- `limit`: int (default 20, max 100)
- `offset`: int (default 0)
- `sort`: string (default "modified_desc")

### FR-002: Get Video Detail
`GET /api/v1/videos/{id}` returns full video metadata.

### FR-003: Response Schema
Match API specification VideoResponse schema.

### FR-004: 404 Handling
Return 404 with standard error format for unknown video ID.

## Acceptance Criteria
- [ ] `GET /videos` returns paginated list
- [ ] `GET /videos` respects limit/offset
- [ ] `GET /videos/{id}` returns video details
- [ ] `GET /videos/{id}` returns 404 for unknown ID
# Videos Search

## Goal
Implement `GET /videos/search` with FTS5 query support.

## Requirements

### FR-001: Search Endpoint
`GET /api/v1/videos/search` with query params:
- `q`: string (required) - search query
- `limit`: int (default 20)

### FR-002: FTS5 Query Support
Pass query to repository search method which uses FTS5.

### FR-003: Response Format
Return search results with query echoed back.

## Acceptance Criteria
- [ ] Search finds videos by filename
- [ ] Search finds videos by path
- [ ] Empty results return empty list
- [ ] Query is echoed in response
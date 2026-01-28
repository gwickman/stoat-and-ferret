# Videos Scan

## Goal
Implement `POST /videos/scan` to scan directory for videos.

## Requirements

### FR-001: Scan Endpoint
`POST /api/v1/videos/scan` with body:
```json
{
  "path": "/home/user/videos",
  "recursive": true
}
```

### FR-002: Directory Scanning
- Walk directory (optionally recursive)
- Filter for video extensions (.mp4, .mkv, .avi, .mov, .webm)
- Extract metadata via FFprobe
- Add to repository

### FR-003: Response Format
```json
{
  "scanned": 47,
  "new": 12,
  "updated": 3,
  "skipped": 32,
  "errors": [{"path": "...", "error": "..."}]
}
```

### FR-004: Error Handling
Continue scanning even if individual files fail.

## Acceptance Criteria
- [ ] Scans directory for video files
- [ ] Uses FFprobe to extract metadata
- [ ] Returns scan summary
- [ ] Handles errors gracefully
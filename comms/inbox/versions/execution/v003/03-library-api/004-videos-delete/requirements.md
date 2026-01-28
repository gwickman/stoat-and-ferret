# Videos Delete

## Goal
Implement `DELETE /videos/{id}` with optional file deletion.

## Requirements

### FR-001: Delete Endpoint
`DELETE /api/v1/videos/{id}` with query param:
- `delete_file`: bool (default false)

### FR-002: Database Deletion
Remove video from repository.

### FR-003: Optional File Deletion
If `delete_file=true`, delete source file from disk.

### FR-004: 404 Handling
Return 404 if video not found.

## Acceptance Criteria
- [ ] `DELETE /videos/{id}` removes from database
- [ ] `delete_file=true` removes file from disk
- [ ] Returns 404 for unknown ID
- [ ] Returns 204 on success
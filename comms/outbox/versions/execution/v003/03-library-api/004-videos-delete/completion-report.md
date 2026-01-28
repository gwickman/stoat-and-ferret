---
status: complete
acceptance_passed: 4
acceptance_total: 4
quality_gates:
  ruff: pass
  mypy: pass
  pytest: pass
---
# Completion Report: 004-videos-delete

## Summary

Implemented `DELETE /api/v1/videos/{id}` endpoint with optional file deletion functionality. The endpoint removes videos from the database and optionally deletes the source file from disk when `delete_file=true` query parameter is provided.

## Acceptance Criteria

- [x] `DELETE /videos/{id}` removes from database
- [x] `delete_file=true` removes file from disk
- [x] Returns 404 for unknown ID
- [x] Returns 204 on success

## Implementation Details

### Files Modified

1. **`src/stoat_ferret/api/routers/videos.py`**
   - Added `contextlib` and `os` imports
   - Added `delete_video` endpoint at `DELETE /{video_id}`
   - Returns 404 if video not found
   - Returns 204 No Content on success
   - Optionally deletes source file with `delete_file=true` query param
   - Uses `contextlib.suppress(OSError)` for best-effort file deletion

2. **`tests/test_api/test_videos.py`**
   - Added 5 test cases for delete endpoint:
     - `test_delete_video` - basic deletion from database
     - `test_delete_video_not_found` - 404 for unknown ID
     - `test_delete_video_with_file_deletion` - file removal with `delete_file=true`
     - `test_delete_video_without_file_deletion` - file preserved when `delete_file=false`
     - `test_delete_video_file_already_missing` - graceful handling when file doesn't exist

## Quality Gates

| Gate | Status |
|------|--------|
| ruff check | pass |
| ruff format | pass |
| mypy | pass |
| pytest | pass (318 passed, 8 skipped) |
| coverage | 92.59% (above 80% threshold) |

## Test Results

All tests pass including 5 new delete endpoint tests:
- `test_delete_video`
- `test_delete_video_not_found`
- `test_delete_video_with_file_deletion`
- `test_delete_video_without_file_deletion`
- `test_delete_video_file_already_missing`

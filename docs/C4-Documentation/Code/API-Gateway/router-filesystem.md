# Filesystem Router

**Source:** `src/stoat_ferret/api/routers/filesystem.py`
**Component:** API Gateway

## Purpose

Directory browsing endpoint for file system navigation. Allows clients to explore directory structures with security validation against allowed scan roots.

## Public Interface

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /api/v1/filesystem/directories | List subdirectories in path |

### Functions

- `list_directories(path: str | None = None) -> DirectoryListResponse`: Lists immediate subdirectories within a given path. Hides hidden directories (starting with '.'). Uses run_in_executor for async-safe filesystem access. Defaults to first allowed_scan_root or home directory if no path provided. Returns parent path and sorted list of subdirectories. 400 if path not a directory, 403 if outside allowed roots, 404 if path doesn't exist.

### Helper Functions

- `_list_dirs(path: str) -> list[DirectoryEntry]`: Lists subdirectories in path using os.scandir. Filters to directories only, excludes hidden entries, returns sorted by name (case-insensitive).

## Key Implementation Details

- **Async safety**: Uses asyncio.get_event_loop().run_in_executor() to run blocking os.scandir in thread pool without blocking event loop
- **Path resolution**: Paths are resolved to absolute paths via Path.resolve() to normalize and dereference symlinks
- **Security validation**: Validates path is within allowed_scan_roots before listing (via validate_scan_path())
- **Default path**: When path is None, defaults to first configured allowed_scan_root or user home directory if no roots configured
- **Hidden filtering**: Directories starting with '.' are excluded (e.g., .git, .hidden)
- **Sorting**: Results sorted by name (case-insensitive) for consistent UX
- **Response structure**: Returns path (resolved parent) and directories array with name and absolute path for each entry

## Dependencies

### Internal Dependencies

- `stoat_ferret.api.schemas.filesystem.DirectoryEntry, DirectoryListResponse`: Directory listing schemas
- `stoat_ferret.api.services.scan.validate_scan_path`: Path validation against allowed roots
- `stoat_ferret.api.settings.get_settings`: Settings for allowed_scan_roots

### External Dependencies

- `fastapi`: APIRouter, HTTPException, Query, status
- `asyncio.get_event_loop().run_in_executor`: Async filesystem access
- `os.scandir`: Efficient directory listing
- `pathlib.Path`: Path operations

## Relationships

- **Used by**: API Gateway application via router inclusion
- **Uses**: Settings for allowed roots validation

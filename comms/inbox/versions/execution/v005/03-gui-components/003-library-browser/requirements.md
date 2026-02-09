# Requirements - 003: Library Browser

## Goal

Build the library browser with video grid, thumbnail display, search with debounce, sort/filter controls, scan modal, and virtual scrolling or pagination for large libraries.

## Background

M1.11 specifies a library browser with video grid, search, sort/filter, and scan controls. No frontend components for video display exist. The backend API endpoints (search, list, scan) exist from v003 but have no GUI consumer. Theme 02 provides the thumbnail pipeline and pagination fix that this feature depends on.

**Backlog Item:** BL-033

## Functional Requirements

**FR-001: Video grid**
Display video thumbnails, filename, and duration for each video in a responsive grid layout.
- AC: Video grid shows thumbnail image, filename, and formatted duration for each video

**FR-002: Search**
Search bar calls `/api/videos/search` with 300ms debounced input.
- AC: Typing in search bar triggers API call after 300ms pause, updating grid results

**FR-003: Sort controls**
Sort by date, name, or duration. Changing sort order updates the grid.
- AC: Selecting a sort option reorders the video grid accordingly

**FR-004: Scan modal**
Scan modal triggers directory scan via the jobs API and shows progress feedback.
- AC: Scan modal allows entering a directory path and triggers a scan job; progress is shown

**FR-005: Large library handling**
Virtual scrolling or pagination handles libraries with 100+ videos. Uses total count from fixed pagination endpoint.
- AC: Libraries with 100+ videos render smoothly without loading all items at once

## Non-Functional Requirements

**NFR-001: Search responsiveness**
Search results appear within 500ms of the debounce completing (300ms debounce + API response time).
- Metric: Total search-to-results time < 800ms on localhost

**NFR-002: Grid rendering**
Video grid renders initial page within 200ms.
- Metric: First contentful paint of grid < 200ms

## Out of Scope

- Video preview/playback from the grid
- Drag-and-drop from library to project timeline
- Batch operations on multiple videos
- Advanced filtering (by codec, resolution, etc.)

## Test Requirements

| Category | Requirements |
|----------|-------------|
| Unit tests (Vitest) | Video grid renders thumbnails with filename and duration; search bar triggers debounced API call; sort controls update grid ordering; scan modal renders and triggers scan API call; virtual scrolling renders visible items only |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.
# Requirements - 002: Dashboard Panel

## Goal

Build the dashboard panel with system health cards, real-time activity log via WebSocket, and metrics overview.

## Background

M1.10 specifies a dashboard with system health cards, recent activity log, and metrics overview. No dashboard component exists. The dashboard is the landing page and primary system health visibility tool. The application shell (Feature 001) provides the layout frame, and the WebSocket endpoint (Theme 01) provides real-time event streaming.

**Backlog Item:** BL-031

## Functional Requirements

**FR-001: Health cards**
Display individual component status (Python API, Rust core, FFmpeg) from `/health/ready` response.
- AC: Health cards show green/yellow/red status for each component

**FR-002: Activity log**
Receive and display WebSocket events in real time. Show event type, timestamp, and relevant details.
- AC: Activity log updates in real time as WebSocket events arrive

**FR-003: Metrics cards**
Show API request count and Rust operation timing from `/metrics` endpoint.
- AC: Metrics cards display current request count and average operation timing

**FR-004: Auto-refresh**
Dashboard auto-refreshes on a configurable interval (default 30s).
- AC: Dashboard data refreshes automatically at the configured interval

## Non-Functional Requirements

**NFR-001: Activity log capacity**
Activity log displays the most recent 50 events, discarding oldest when limit is reached.
- Metric: Log maintains <= 50 entries with FIFO eviction

## Out of Scope

- Custom dashboard layouts or widget rearrangement
- Historical metrics or charts
- Alert/notification system
- Export/download of activity log

## Test Requirements

| Category | Requirements |
|----------|-------------|
| Unit tests (Vitest) | Health cards render component status from mock `/health/ready`; activity log appends WebSocket events; metrics cards display request count and timing from mock `/metrics`; auto-refresh triggers on interval |

## Reference

See `comms/outbox/versions/design/v005/004-research/` for supporting evidence.
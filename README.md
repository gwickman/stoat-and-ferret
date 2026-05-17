# stoat-and-ferret

[Alpha] AI-driven video editor with hybrid Python/Rust architecture - not production ready.

**v066 (WebSocket Reconnect & Replay Contract):** Replaces per-scope WebSocket `event_id` counters with a global monotonic counter and adds heartbeat buffering for reliable replay; extends `GET /api/v1/system/state` to surface active render jobs and prune stale terminal entries. See [CHANGELOG.md](docs/CHANGELOG.md) for release details.

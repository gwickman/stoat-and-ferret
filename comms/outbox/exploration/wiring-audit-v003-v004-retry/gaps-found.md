# Wiring Gaps Found

Two gaps found, both in the same feature. The known logging gap (BL-056) is excluded.

---

## Gap 1: `settings.debug` defined but never consumed

- **Version/Theme/Feature:** v003 / 02-api-foundation / 002-externalized-settings
- **Designed:** `STOAT_DEBUG` environment variable (boolean) to enable debug mode, validated by pydantic
- **Implemented:** `Settings.debug` field at `src/stoat_ferret/api/settings.py:49` with default `False`
- **What's wired:** Nothing. The `debug` field is never read by any production code. `create_app()` does not pass `debug=settings.debug` to `FastAPI()`. `__main__.py` does not pass it to `uvicorn.run()`.
- **Completion report caught it:** No. The completion report for 002-externalized-settings reports all fields as implemented and working.
- **Severity:** minor (degraded) — debug mode is a development convenience; the app runs fine without it, but setting `STOAT_DEBUG=true` has no effect.

**Fix:** Pass `debug=settings.debug` to `FastAPI()` in `create_app()` and/or to `uvicorn.run()` in `__main__.py`.

---

## Gap 2: `settings.ws_heartbeat_interval` defined but hardcoded

- **Version/Theme/Feature:** v003 / 02-api-foundation / 002-externalized-settings
- **Designed:** `STOAT_WS_HEARTBEAT_INTERVAL` environment variable (int, >=1) for configurable WebSocket heartbeat timing
- **Implemented:** `Settings.ws_heartbeat_interval` field at `src/stoat_ferret/api/settings.py:71` with default `30`, validation `ge=1`
- **What's wired:** The WebSocket endpoint at `src/stoat_ferret/api/routers/ws.py:15` defines `DEFAULT_HEARTBEAT_INTERVAL = 30` and uses it directly at line 42: `_heartbeat_loop(websocket, DEFAULT_HEARTBEAT_INTERVAL)`. The settings value is completely ignored.
- **Completion report caught it:** No. The completion report lists the setting as implemented.
- **Severity:** minor (degraded) — heartbeat works fine at the default 30s, but setting `STOAT_WS_HEARTBEAT_INTERVAL=10` has no effect.

**Fix:** In `websocket_endpoint()`, read the interval from `websocket.app.state` (populated from settings in lifespan) or from `get_settings().ws_heartbeat_interval` instead of the hardcoded constant.

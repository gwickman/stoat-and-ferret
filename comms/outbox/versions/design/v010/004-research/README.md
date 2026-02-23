# 004-Research: v010 Research and Investigation

v010 targets 5 backlog items across async pipeline correctness (BL-072, BL-077, BL-078) and user-facing job controls (BL-073, BL-074). Research confirms all items are implementable with existing patterns and no external dependencies. The key finding is that Ruff's built-in ASYNC221 rule can replace the planned grep-based CI script for BL-077, reducing implementation complexity significantly. All 12 referenced learnings are verified as still applicable.

## Research Questions

1. **BL-072**: What is the best approach for converting `subprocess.run()` to async — `asyncio.create_subprocess_exec()` or `asyncio.to_thread()`?
2. **BL-072**: What are all blocking `subprocess.run()` calls in `src/` and which are in async contexts?
3. **BL-073**: What changes are needed to `_AsyncJobEntry` and `AsyncioJobQueue` for progress reporting?
4. **BL-073**: How does the frontend ScanModal currently handle progress?
5. **BL-074**: What cancellation mechanism is appropriate — `asyncio.Event`, boolean flag, or `Task.cancel()`?
6. **BL-074**: What cancel API endpoint pattern fits the existing REST API?
7. **BL-077**: Does Ruff already have rules for blocking calls in async functions, or is a custom script needed?
8. **BL-078**: What patterns exist for testing event-loop responsiveness without flaky timing?
9. **Cross-cutting**: How many `create_app()` kwargs exist and will v010 exceed the 6-7 threshold?
10. **Cross-cutting**: Are all 12 referenced learnings still valid?

## Findings Summary

| Question | Finding |
|----------|---------|
| Async subprocess approach | `asyncio.create_subprocess_exec()` for ffprobe (native async I/O, no thread overhead). `asyncio.to_thread()` acceptable for `health.py`'s 5s ffmpeg check. |
| Blocking calls inventory | 3 calls: `probe.py:65`, `executor.py:96`, `health.py:96`. Only `health.py` has `async def` in same file. |
| Progress model changes | Add `progress: float | None = None` to `_AsyncJobEntry`. Add `set_progress(job_id, value)` to queue. Schema already has `progress` field. |
| Frontend progress | ScanModal already reads `status.progress` and renders a percentage bar. Only backend population is missing. |
| Cancellation mechanism | `asyncio.Event` per job — lightweight, awaitable, thread-safe. Check with `event.is_set()` in scan loop. |
| Cancel endpoint | `POST /api/v1/jobs/{id}/cancel` (action endpoint, not DELETE which implies resource deletion). |
| CI blocking check | Ruff rule **ASYNC221** (`flake8-async` set) detects `subprocess.run/call/check_output` inside async functions. Add `"ASYNC"` to ruff select. |
| Responsiveness testing | Use concurrent `httpx.AsyncClient` requests during simulated-slow scan; assert response time < 2s with explicit timeout. |
| create_app() kwargs | Currently 9 kwargs. v010 adds 0 new kwargs (progress/cancellation are internal to job queue). Below threshold. |
| Learnings verification | All 12 learnings VERIFIED — conditions still present in codebase. |

## Unresolved Questions

| Question | Why Unresolved | Mitigation |
|----------|---------------|------------|
| Exact CI runner latency for 2s responsiveness threshold | TBD — requires runtime testing on GitHub Actions | Use generous threshold (2s) and `@pytest.mark.slow` marker; tune after first CI run |
| Whether `executor.py:96` subprocess.run causes blocking under render jobs | Render jobs not yet async — will surface when render pipeline uses job queue | Flag in BL-077 allowlist if needed; address in future version |

## Recommendations

1. **BL-072**: Use `asyncio.create_subprocess_exec()` with `communicate()` for ffprobe. Keep the function signature, make it `async def ffprobe_video()`. Update all callers (just `scan_directory()`).
2. **BL-073**: Add `progress` field to `_AsyncJobEntry`, expose `set_progress()` on queue, pass queue reference into scan handler via closure. No new `create_app()` kwargs needed.
3. **BL-074**: Use `asyncio.Event` per job as cancellation flag. Add `cancel()` method to queue. `POST /api/v1/jobs/{id}/cancel` endpoint. Check flag in scan loop between files.
4. **BL-077**: Add `"ASYNC"` to ruff lint select rules in `pyproject.toml`. This enables ASYNC221 (subprocess in async) plus ASYNC210 (blocking HTTP) and ASYNC230 (blocking file I/O). No custom script needed.
5. **BL-078**: Integration test using `httpx.AsyncClient` with simulated-slow `ffprobe_video` (via `asyncio.sleep` in a real async function, not a mock). Concurrent polling during scan to verify < 2s response.

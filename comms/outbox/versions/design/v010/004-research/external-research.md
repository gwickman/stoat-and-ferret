# External Research — v010

## 1. Async Subprocess Conversion (BL-072)

### Question: `asyncio.create_subprocess_exec()` vs `asyncio.to_thread()` for ffprobe?

**Source:** CPython docs via DeepWiki (`python/cpython`), Python 3.14 docs

**Findings:**

| Approach | Mechanism | Pros | Cons |
|----------|-----------|------|------|
| `asyncio.create_subprocess_exec()` | Native async process, OS-level I/O | No thread overhead, full async I/O, `communicate()` handles pipes | Must rewrite subprocess call, different API than `subprocess.run()` |
| `asyncio.to_thread(subprocess.run, ...)` | Runs blocking call in thread pool | Minimal code change (wrap existing call) | Uses thread pool thread, still blocks that thread, less efficient |

**Recommendation:** Use `asyncio.create_subprocess_exec()` for ffprobe because:
1. ffprobe is an external process — this is the designed use case for `create_subprocess_exec()`
2. No thread pool consumption — important for concurrent multi-file scans
3. `communicate()` handles stdout/stderr collection cleanly
4. Timeout via `asyncio.wait_for()` works reliably since the event loop is never blocked

**Pattern:**
```python
async def ffprobe_video(path: str, ...) -> VideoMetadata:
    proc = await asyncio.create_subprocess_exec(
        ffprobe_path, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    # Parse stdout as JSON, same as current implementation
```

**Python 3.10 note:** `asyncio.create_subprocess_exec()` is available in Python 3.10+. On Windows, requires `ProactorEventLoop` (the default since Python 3.8).

## 2. CI Blocking-Call Detection (BL-077)

### Question: Custom grep script or existing tooling?

**Source:** Ruff documentation (https://docs.astral.sh/ruff/rules/run-process-in-async-function/)

**Finding: Ruff ASYNC221 rule** detects `subprocess.run()`, `subprocess.call()`, `subprocess.check_output()`, and `subprocess.check_call()` inside async functions. This is exactly what BL-077 requires.

**Rule set:** `flake8-async` (prefix `ASYNC`). Key rules:
- **ASYNC221**: Blocking process calls in async functions (subprocess.run, etc.)
- **ASYNC210**: Blocking HTTP calls in async functions (urllib.request, etc.)
- **ASYNC230**: Blocking file I/O in async functions (open(), etc.)

**Integration:** Add `"ASYNC"` to `select` in `pyproject.toml`:
```toml
select = ["E", "F", "I", "UP", "B", "SIM", "ASYNC"]
```

**Advantages over custom grep script:**
1. AST-based (not grep-based) — understands Python syntax, no false positives from comments/strings
2. Already integrated into existing ruff CI step — zero CI configuration changes
3. Reports exact file, line, and column with descriptive error message
4. Maintained by the ruff community — catches edge cases we wouldn't
5. Also catches blocking HTTP and file I/O — broader protection

**Impact on BL-077 scope:** The backlog item described a "grep-based CI script (~20 lines)". Using ruff ASYNC rules is a 1-line config change that provides superior detection. BL-077's acceptance criteria are still met:
- AC1: Check exists (ruff ASYNC rules) ✓
- AC2: Runs as part of quality gates (already in ruff) ✓
- AC3: Clear error message with file/line (ruff output) ✓
- AC4: Passes after BL-072 fix (async ffprobe won't trigger ASYNC221) ✓
- AC5: No false positives on sync-only files (AST-aware, only flags async functions) ✓

**Other tools evaluated:**
- `pylint-blocking-calls` (PyPI) — requires pylint, not used in this project
- `blockbuster` (GitHub: cbornet/blockbuster) — runtime detection, not static analysis
- Custom grep — fragile, false positives from comments/strings

## 3. Cooperative Cancellation (BL-074)

### Question: What cancellation mechanism for job queue?

**Source:** Python asyncio docs, ethereum/asyncio-cancel-token, CPython issue #103486

**Options evaluated:**

| Mechanism | Pros | Cons |
|-----------|------|------|
| `asyncio.Event` | Lightweight, awaitable, thread-safe, stdlib | Requires passing to handler |
| `Task.cancel()` + `CancelledError` | Built into asyncio | Hard to handle partial results, propagates unexpectedly |
| Boolean flag | Simplest | Not awaitable, requires polling |
| `asyncio-cancel-token` | Structured pattern | External dependency, unmaintained |

**Recommendation:** `asyncio.Event` per job entry.
- Set via `cancel()` method on queue: `entry.cancel_event.set()`
- Check in scan loop: `if cancel_event.is_set(): break`
- Thread-safe (important for potential future multi-worker)
- No external dependencies (aligns with LRN-010)

**Pattern:**
```python
@dataclass
class _AsyncJobEntry:
    ...
    cancel_event: asyncio.Event = field(default_factory=asyncio.Event)

# In scan handler:
for file_path in root.glob(pattern):
    if cancel_event.is_set():
        break
    # ... process file ...
```

## 4. Event-Loop Responsiveness Testing (BL-078)

### Question: How to reliably test event-loop blocking without flaky timing?

**Source:** pytest-asyncio docs, deepankarm.github.io/posts/detecting-event-loop-blocking

**Approach:** Use `httpx.AsyncClient` to make concurrent requests during a scan with simulated-slow processing.

**Pattern:**
```python
async def test_event_loop_responsive_during_scan():
    # 1. Create app with async ffprobe that simulates slow processing
    async def slow_ffprobe(path, **kw):
        await asyncio.sleep(0.5)  # Simulates real I/O without blocking
        return fake_metadata

    # 2. Start scan via POST
    # 3. While scan runs, poll GET /api/v1/jobs/{id} with 2s timeout
    # 4. Assert response received within timeout
```

**Key design decisions:**
- Use `asyncio.sleep()` (not `time.sleep()`) in the simulated ffprobe to prove the event loop is free
- If someone regresses to blocking calls, `time.sleep()` would block the loop and the polling request would time out
- Use explicit `asyncio.wait_for()` with 2-second timeout (LRN-043)
- Mark with `@pytest.mark.slow` for CI selection
- Use `httpx.AsyncClient` (already a project dependency) for async HTTP in tests

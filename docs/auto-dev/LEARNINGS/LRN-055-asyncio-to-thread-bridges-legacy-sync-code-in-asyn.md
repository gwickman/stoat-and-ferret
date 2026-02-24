## Context

When migrating a codebase from sync to async, some functions contain sync blocking calls (like `subprocess.run()`) that cannot be easily converted to fully async equivalents. This is common in utility functions, health checks, and third-party library calls.

## Learning

Use `asyncio.to_thread()` to wrap blocking synchronous calls in async contexts when a full async rewrite is impractical or unnecessary. This moves the blocking call to a thread pool, preventing event-loop starvation while maintaining the existing sync implementation. Reserve `asyncio.create_subprocess_exec()` for new code or high-frequency paths where the full async approach is warranted.

## Evidence

v010 Feature 002 (async-blocking-ci-gate) used `asyncio.to_thread()` to wrap the health check's `subprocess.run()` call rather than converting it to `asyncio.create_subprocess_exec()`. This was appropriate because:
- Health checks run infrequently (not a hot path)
- The existing sync implementation was well-tested
- The change was minimal and low-risk

Meanwhile, Feature 001 used `asyncio.create_subprocess_exec()` for `ffprobe_video()` because it runs per-file during scans (hot path).

## Application

When encountering blocking sync calls in async code:
- **High-frequency paths**: Convert to native async (`asyncio.create_subprocess_exec()`, `aiohttp`, etc.)
- **Low-frequency paths**: Wrap with `asyncio.to_thread()` for minimal-risk unblocking
- **Third-party sync libraries**: `asyncio.to_thread()` is the only practical option without replacing the library
- Note: `asyncio.to_thread()` is available from Python 3.9+
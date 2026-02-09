# Handoff: 001-job-queue-infrastructure

## What Was Built

- `AsyncioJobQueue` in `src/stoat_ferret/jobs/queue.py` - async job queue with background worker
- Lifespan integration in `src/stoat_ferret/api/app.py` - worker starts/stops with the app
- `create_app()` accepts `job_queue` parameter for DI in tests

## How to Use

### Register a handler and submit jobs

```python
from stoat_ferret.jobs.queue import AsyncioJobQueue

queue = AsyncioJobQueue(timeout=300)  # 5 min default
queue.register_handler("scan", scan_handler)

job_id = await queue.submit("scan", {"path": "/videos", "recursive": True})
status = await queue.get_status(job_id)
result = await queue.get_result(job_id)
```

### Access the queue from routes

The queue is stored on `app.state.job_queue` by the lifespan manager. Access it via `request.app.state.job_queue` in route handlers.

## What the Next Feature Should Know

- The worker processes one job at a time (single worker). This is sufficient for current scale per requirements.
- Job handlers are async callables with signature `async def handler(job_type: str, payload: dict) -> Any`.
- No handlers are registered by default. The next feature (likely async scan endpoint) should register a scan handler before the worker starts processing, or at app startup.
- The `InMemoryJobQueue` remains available for testing - it executes jobs synchronously at submit time.

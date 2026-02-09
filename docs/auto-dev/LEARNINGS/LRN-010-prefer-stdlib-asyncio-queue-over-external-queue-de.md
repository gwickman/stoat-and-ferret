## Context

Job queue implementations often default to external systems (Redis, RabbitMQ, arq) even when the application's scale doesn't require them. This adds deployment complexity and external dependencies.

## Learning

For applications with modest job queue requirements (single-worker, in-process), use Python's stdlib `asyncio.Queue` with a producer-consumer pattern instead of external queue systems. This eliminates an external dependency, simplifies deployment, and integrates naturally with FastAPI's lifespan context manager. Scale up to external queues only when demonstrated need arises.

## Evidence

- v004 Theme 03: Replaced planned arq/Redis dependency with `asyncio.Queue`. The single-worker producer-consumer pattern meets all current requirements.
- The version retrospective explicitly called this out as a cross-theme learning.
- Design documents were updated to replace arq/Redis references with asyncio.Queue.

## Application

- Start with stdlib solutions (asyncio.Queue, threading.Queue) before reaching for external dependencies.
- Design the queue protocol/interface generically so external implementations can be swapped in later if needed.
- Use InMemoryJobQueue (synchronous execution) for testing, AsyncioJobQueue (background worker) for production.
- This is a specific application of the general principle: avoid external dependencies until demonstrated need.
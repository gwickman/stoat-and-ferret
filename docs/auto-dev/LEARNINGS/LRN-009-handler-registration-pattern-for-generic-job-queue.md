## Context

Job queue systems need to route different job types to different handler functions. Common approaches include configuration files, decorator-based registration, or class hierarchies.

## Learning

Use a `register_handler(job_type, handler_fn)` method on the queue that wires job types to async functions at startup. This keeps routing explicit, avoids a separate handler registry module, and fails immediately with a clear error for unregistered job types. Combine with a factory function pattern (e.g., `make_scan_handler(repo)`) to inject dependencies into handlers at registration time.

## Evidence

- v004 Theme 03 Feature 001 (job-queue-infrastructure): `AsyncioJobQueue.register_handler()` wired job types to handlers.
- `make_scan_handler()` factory captured dependencies at registration time, keeping handlers testable in isolation.
- `InMemoryJobQueue` also supported handler registration for deterministic test execution.
- Jobs submitted without a registered handler failed immediately with a descriptive error.

## Application

- Prefer explicit registration over convention-based or configuration-based routing.
- Use factory functions to inject dependencies into handlers rather than having handlers reach into global state.
- Ensure unregistered job types fail fast with clear error messages.
- Apply the same registration pattern to both production and test queue implementations.
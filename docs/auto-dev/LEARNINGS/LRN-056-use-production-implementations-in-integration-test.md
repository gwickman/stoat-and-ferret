## Context

Integration tests that verify concurrent async behavior need to exercise real async scheduling and task interleaving. Synchronous test doubles that execute operations immediately mask concurrency issues.

## Learning

Use production async implementations (not synchronous test doubles) in integration tests that verify concurrent behavior. Synchronous in-memory stubs execute handlers immediately at submit time, bypassing async task scheduling entirely, which defeats the purpose of testing async concurrency properties like event-loop responsiveness or task interleaving.

## Evidence

v010 Feature 003 (event-loop-responsiveness-test) used the production `AsyncioJobQueue` instead of `InMemoryJobQueue` for its integration test. The `InMemoryJobQueue` executes jobs synchronously at submit time, which would not exercise actual async concurrency. The production queue's async task scheduling was essential to verify that the event loop stayed responsive during a scan with simulated-slow processing.

## Application

When writing integration tests for async behavior:
- Use the production async queue/scheduler, not a synchronous test double
- Synchronous test doubles are appropriate for unit tests where you test handler logic in isolation
- Only integration tests that specifically verify concurrency properties need the production implementation
- Clearly mark these tests with appropriate markers (`@pytest.mark.integration`, `@pytest.mark.slow`)
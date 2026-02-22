## Context

Many applications accumulate dead code — components that are implemented but never wired into the runtime dependency injection chain. Wiring these components into the live application can be done as a dedicated activity once the DI pattern is well-established.

## Learning

Features that wire existing, tested code into the DI chain follow a predictable pattern and complete quickly with minimal risk of regressions. When the DI pattern is established (add kwarg → instantiate in lifespan → store on app.state → pass to dependents), each successive wiring feature is faster than the last. Consider batching similar DI wiring tasks into dedicated versions.

## Evidence

In v009, all six features either wired existing components (Theme 01: FFmpeg observability, audit logging, file logging) or extended existing patterns (Theme 02: SPA routing, pagination, broadcasts). All 31 acceptance criteria passed with zero quality gate failures. Each feature in Theme 01 followed the identical DI wiring pattern, making the third feature noticeably faster than the first. Coverage stayed stable at ~92.9% throughout, and test count grew from ~890 to 936.

## Application

When planning versions:
1. Identify dead code or unwired components in the codebase
2. Batch wiring tasks into a dedicated theme — the shared DI pattern creates compounding efficiency
3. Expect high first-iteration success rates for wiring features
4. Monitor `create_app()` kwarg count — consider introducing a DI container or config dataclass if it exceeds 6-7 parameters
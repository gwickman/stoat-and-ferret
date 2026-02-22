## Context

When wiring settings or configuration values to framework APIs across module boundaries, the correct consumer API is not always obvious. Implementation plans may suggest API calls that seem reasonable but are actually invalid.

## Learning

Static type checkers (mypy) are especially valuable during wiring work that connects configuration to framework APIs. They catch invalid keyword arguments, wrong parameter types, and missing method signatures before runtime — errors that would otherwise only surface in production or integration tests. This is more valuable than in typical application code because wiring crosses module boundaries where the author may not be intimately familiar with the target API.

## Evidence

In v008, the implementation plan for feature 003 (orphaned settings) suggested wiring `settings.debug` to both `FastAPI(debug=...)` and `uvicorn.run(debug=...)`. mypy caught that `uvicorn.run()` does not accept a `debug` keyword argument. The correct consumer was `FastAPI(debug=...)` only. Without mypy, this would have been a runtime error in production.

## Application

When wiring configuration to third-party or framework APIs:
1. Run mypy after each wiring change, not just at the end
2. Treat mypy errors as design feedback — they may indicate the implementation plan has an incorrect assumption about the target API
3. Trust the type checker over documentation or implementation plans when they disagree
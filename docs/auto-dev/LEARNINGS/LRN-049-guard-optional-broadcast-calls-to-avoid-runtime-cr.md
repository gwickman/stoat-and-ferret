## Context

When adding event broadcasting (e.g., WebSocket notifications) to existing operations like record creation or background job completion, the broadcasting infrastructure may not always be available — particularly in tests, minimal deployments, or when the WebSocket manager hasn't been initialized.

## Learning

Guard all broadcast calls with a simple `if manager:` check so they become a no-op when the broadcasting component is absent. This decouples event emission from core functionality and eliminates the need to mock or initialize broadcast infrastructure in unrelated tests.

## Evidence

In v009, WebSocket broadcasts for `PROJECT_CREATED`, `SCAN_STARTED`, and `SCAN_COMPLETED` events were added with `if ws_manager:` guards. This allowed all existing tests to pass unchanged — only dedicated broadcast tests needed to set up the mock manager. No crashes occurred in contexts where `ws_manager` was not set.

## Application

When adding optional notification/broadcast capabilities to existing operations:
1. Accept the broadcast dependency as an optional parameter (e.g., `ws_manager: ConnectionManager | None`)
2. Guard every broadcast call with `if dependency:` before calling methods on it
3. This pattern avoids forcing all consumers to provide the dependency
4. Dedicated tests can inject a mock to verify broadcast behavior
5. Non-broadcast tests need no changes to their setup
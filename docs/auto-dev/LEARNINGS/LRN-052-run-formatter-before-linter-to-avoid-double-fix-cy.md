## Context

When implementing features, code is written and then quality gates are run. Session analytics show that nearly every v009 implementation session encountered ruff format failures on the first quality gate run, followed by ruff check import-ordering failures — requiring multiple fix-and-rerun cycles.

## Learning

Run `ruff format` before `ruff check` during local development. Format failures cause sibling tool call errors in parallel quality gate runs, and import-ordering violations (I001) are often side effects of unformatted code. Running the formatter first eliminates a class of linter errors and reduces fix cycles.

## Evidence

Session analytics for v009 show recurring error patterns: `ruff format --check` failures for newly-written test files (test_ffmpeg_observability.py, test_audit_logging.py, test_logging_startup.py, test_spa_routing.py, test_websocket_broadcasts.py) and `ruff check` I001 import-ordering violations. These appeared in nearly every feature implementation session as the first quality gate run, requiring at least one fix-and-rerun cycle each time.

## Application

In implementation workflows:
1. Run `ruff format` first after writing/modifying code
2. Then run `ruff check` — many I001 violations will already be resolved
3. When running quality gates in parallel, expect sibling errors if format fails
4. Consider running format as part of the edit workflow (on-save) rather than as a post-implementation check
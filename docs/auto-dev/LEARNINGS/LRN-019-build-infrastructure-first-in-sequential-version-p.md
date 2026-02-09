## Context

When planning a version with multiple themes, the ordering of themes matters. Some themes produce infrastructure consumed by later themes, while others are independent.

## Learning

Sequence "infrastructure" themes (test doubles, DI patterns, fixture factories) before "consumer" themes (feature tests, security tests, integration tests). The upfront investment in testing infrastructure pays off immediately when subsequent themes consume it without friction. Design independent features within themes whenever possible to avoid sequential bottlenecks.

## Evidence

- v004: Theme 01 (test foundation) was consumed by every subsequent theme. Theme 02 used DI pattern and InMemory doubles. Theme 03 extended create_app() with job_queue. Theme 04 used fixture infrastructure for security tests.
- The version retrospective explicitly validated this "build infrastructure first" sequencing strategy.
- Independent features within themes (Themes 02, 04, 05) executed cleaner than sequential features (Themes 01, 03).

## Application

- Place infrastructure/foundation themes at the beginning of version plans.
- Within themes, prefer independent features over sequential chains when possible.
- When sequential ordering is necessary, use handoff documents between features to provide clear context.
- This applies to any multi-theme development plan.
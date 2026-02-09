## Context

When building in-memory repository implementations for testing, mutation isolation between test cases is critical. If test doubles share object references with callers, one test's modifications can leak into another.

## Learning

Apply `deepcopy()` on **both read and write operations** in InMemory repository implementations. Deepcopy only on read still allows callers to mutate stored state via input references from write operations. Both directions must be isolated.

## Evidence

- v004 Theme 01 Feature 001 (inmemory-test-doubles): All three InMemory repositories (Project, Video, Clip) required deepcopy on both `add()`/`update()` inputs and `get()`/`list()` outputs to prevent cross-test pollution.
- 10 dedicated isolation tests were added to verify no mutation leakage.

## Application

- Any in-memory repository or cache used for testing should deepcopy on both ingress and egress.
- Add explicit isolation tests that verify stored objects cannot be mutated by callers.
- This pattern applies to any language/framework where test doubles hold mutable state.
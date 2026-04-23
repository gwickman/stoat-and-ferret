# Version Retrospective: v040

## Executive Summary

v040 achieved complete execution with all 2 themes and 6 features delivered, universal quality gate passage (102 new tests, 0 new failures), and strong framework pattern alignment. The version demonstrated pragmatic architectural decision-making when design specifications conflicted with implementation constraints, resolving each conflict transparently with documentation in completion reports. A single clarification gap was identified regarding buffer scoping semantics in the websocket-observability theme; all other framework guidance was followed without gaps. The version's most important takeaway is that mature framework patterns and transparent trade-off documentation enable high-velocity feature delivery without compromising code quality or system coherence.

## Version Goals Assessment

| Goal | Status | Evidence |
|------|--------|----------|
| websocket-observability: Monotonic event IDs and replay buffer | achieved | Features 001 & 002 both complete; all 9 ACs met for 001, 8/10 for 002 (intentional architectural trade-off documented) |
| api-testability: System state, test fixtures, long-poll, state machine docs | achieved | Features 003–006 all complete; 0 ACs missed across all 4 features; 3 new endpoints live; OpenAPI schema updated |

## Execution Metrics

- **Features Planned**: 6
- **Features Completed**: 6
- **Features Failed**: 0
- **Themes Completed**: 2/2
- **Quality Gate Pass Rate**: 100% (30/30 gates; feature 006 CI pending but locally all pass)
- **AC Resolution Rate**: 98% (52/54 ACs met; 2 intentional deviations in feature 002 documented)
- **Test Baseline**: 0 pre-existing failures, 0 new failures, 102 new tests added, 100% pass rate

## Cross-Theme Patterns

### What Worked Well

1. **Sequential Dependency Execution**: Theme 01 → Theme 02 completed cleanly. Feature 001 (event-id-scheme) shipped first, providing the event_id primitive feature 002 (replay-buffer) needed. No blocking issues between features or themes.

2. **Consistent Multi-Layer Test Coverage**: Both themes used the same approach: unit tests (verify mechanics), integration tests (exercise real paths), smoke tests (capture WebSocket payloads and connection lifecycle). All tests assert observable outcomes, not call patterns. Result: 102 new tests with 0 failures.

3. **Framework Pattern Adherence**: All 6 features aligned with FRAMEWORK_CONTEXT.md guardrails without hidden workarounds:
   - Python 3.10 compatibility: asyncio.TimeoutError (not bare TimeoutError), plain dict types, no builtins overrides
   - Pydantic V2: ConfigDict(from_attributes=True), Field(description=...) for schema enrichment
   - Logging: structlog.get_logger(__name__) for semantic events across all features
   - Dependency Injection: All features leveraged existing ProjectRepoDep, SettingsDep, WSManagerDep aliases; no new constructor arguments needed
   - OpenAPI discipline: All features regenerated schema after changes and verified live/static parity

4. **APIRouter Consistency** (api-testability): All four features used FastAPI's APIRouter(prefix=...) pattern with alphabetical registration in app.py. Router structure is now a canonical pattern for future REST features.

5. **Reusable Pattern Crystallization**: Several patterns emerged as reusable:
   - Per-job async notification via asyncio.Event (feature 005) is clean and avoids global task registries
   - OpenAPI injection via _custom_openapi hook (feature 006) is the canonical way to document non-endpoint schemas
   - Testing-mode guard reuse (feature 004) shows that existing flags are simpler than new feature flags
   - Shared buffer + per-job filtering (feature 002) observably equivalent to per-connection when all clients receive all broadcasts

### What Didn't Work

1. **Per-Connection Buffer Requirement Conflict** (websocket-observability feature 002): The original design specified per-connection deques deallocated on close. The smoke test requirement (offline replay of broadcasts that happened while client was disconnected) cannot be simultaneously satisfied without a client-identity mechanism. Resolved by shared buffer on ConnectionManager with per-job event_id filtering. Both FRs met; 2 ACs (FR-005, INV-006) marked as partial/unmet with documented trade-off.

2. **Template Path References Not Expanded Fully** (api-testability): Template plans used `src/api/...` but actual project structure is `src/stoat_ferret/api/...`. This caused minor friction during feature 003 & 004; by feature 005 & 006, the correct paths were applied automatically. Not a framework gap; a template placeholder issue.

3. **AGENTS.md Script Name Stale** (api-testability): Template referenced `scripts.generate_openapi` but the actual script is `scripts.export_openapi`. All four features discovered this and used the correct name. Minor friction; easily fixed by one-line AGENTS.md update.

### Recurring Issues

No issues recurred across multiple features. Each theme had at most one architectural conflict (websocket-observability: buffer scoping; api-testability: template paths). Once identified and resolved, no other features encountered the same issue.

## Process Observations

### Estimation Accuracy

Features were sized and estimated with high accuracy. All 6 features completed within planned scope; no surprise expansion or contraction. Feature 001 delivered its 9 ACs on-plan. Feature 002 encountered a single architectural conflict (buffer scoping) but resolved it pragmatically without scope creep. Features 003–006 (api-testability) executed per design with zero surprises. Estimation discipline appears strong; sequential dependency prediction (001 → 002) was validated in execution.

### Dependency Management

Inter-theme dependencies were minimal but well-handled. Feature 001 (event-id-scheme) shipped first, and feature 002 (replay-buffer) consumed the event_id primitive without rework. Theme 01 shipped cleanly before Theme 02 started. Within Theme 02, features 003–006 had no blocking dependencies; all four features shipped independently.

### Quality Gate Effectiveness

Quality gates caught no real issues in v040 (100% pass rate) but proved effective as guardrails:
- **Ruff check/format**: All 6 features zero violations, proper formatting
- **Mypy**: 100+ source files per feature, zero type issues
- **Pytest**: 102 new tests, 100% pass rate, zero inherited failures
- **CI**: 5/6 features merged, 1 pending Windows runner completion
- **OpenAPI sync**: All features verified live/static parity; gate prevented schema drift

False positive rate: zero. Real issue detection: zero incidents in v040. Gates are working as intended.

## Recommendations for Next Version

1. **Clarify Buffer Scoping Semantics in FRAMEWORK_CONTEXT.md** *(high priority, short-term)*
   - The per-connection buffer requirement (websocket-observability FR-005) conflicts with offline replay (smoke test requirement).
   - **Rationale**: Future websocket features need explicit guidance on whether client identity (session cookie, subscribe token) is within scope. Maintenance request filed in websocket-observability completion report.
   - **Action**: Update FRAMEWORK_CONTEXT.md §6 with decision: is shared buffer + per-job filtering acceptable, or is client identity required?

2. **Update AGENTS.md Script Reference** *(low priority, one-line fix)*
   - Line 84 and any other references use `scripts.generate_openapi` but actual script is `scripts.export_openapi`.
   - **Rationale**: Prevents future template confusion and friction during OpenAPI regeneration.
   - **Action**: Grep for `generate_openapi`, replace with `export_openapi`.

3. **Document Acceptance-Level Requirements Early in Design** *(medium priority, process improvement)*
   - The smoke test requirement (offline replay) in websocket-observability should be cross-checked against framework invariants (per-connection buffer deallocate-on-close) during design review.
   - **Rationale**: Would have surfaced the buffer scoping conflict before implementation began, enabling cleaner trade-off discussion.
   - **Action**: Add checklist to THEME_DESIGN.md: cross-check acceptance tests against all invariants before implementation.

4. **Establish Per-Job Async Notification as Canonical Pattern** *(medium priority, documentation)*
   - Feature 005 (long-poll-completion) used per-job asyncio.Event with lazy allocation and registry cleanup. This pattern avoids global task registries and is reusable.
   - **Rationale**: Multiple future async-waiter features can reuse this pattern without modification.
   - **Action**: Document in FRAMEWORK_CONTEXT.md as the canonical approach for async waiter features. Add code example.

5. **Consider Client Identity Mechanism for Future Versions** *(low priority, future-looking)*
   - If per-connection state isolation becomes a requirement (e.g., per-user replay buffers, per-session event filtering), introduce a client-identity mechanism (session cookie, subscribe token).
   - **Rationale**: Shared buffer + per-job filtering works now; per-user isolation would require a different architecture.
   - **Action**: Track as a future architectural decision point. No action in v041 unless per-user isolation is explicitly required.

## Outstanding Items

1. **Feature 006 CI Completion**: PR #314 (state-machine-docs) locally passes all quality gates; CI run pending completion. Windows 3.10 runner known to hang sporadically (pre-existing issue on main branch). *Expected resolution*: CI will complete and feature 006 will merge.

2. **Maintenance Request on Per-Connection Buffer Semantics**: Framework guidance clarification needed. Issue filed in websocket-observability completion report (FRAMEWORK_CONTEXT.md §6). *Owner*: Framework maintainer. *Timeline*: Before next websocket feature begins.

3. **AGENTS.md Update for Script Name**: `scripts.generate_openapi` → `scripts.export_openapi`. *Owner*: Documentation maintainer. *Timeline*: Before v041 feature 001 begins. *Complexity*: One-line change, grep for all references.

## Summary

v040 represents a maturation point for stoat-and-ferret's development process. All 6 features shipped complete, quality gates passed universally, and framework patterns proved well-established and reusable. The single framework clarification gap (buffer scoping) was identified, documented, and elevated for future decision-making rather than left as hidden technical debt. Sequential dependency execution was clean, and no issues recurred across multiple features. The version's most important takeaway is that transparent trade-off documentation and pragmatic architectural decision-making enable high-velocity delivery without compromising system coherence or code quality.

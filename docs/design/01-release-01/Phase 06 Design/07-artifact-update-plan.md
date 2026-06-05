# Phase 6: Artifact Update Plan

## Design Documents

| File | Action | Purpose |
|------|--------|---------|
| `docs/design/01-roadmap.md` | Modify | Mark Phase 6 milestones as in-progress/complete |
| `docs/design/05-api-specification.md` | Modify | Add system state, seed, version, schema, flags endpoints |
| `docs/design/08-gui-architecture.md` | Modify | Add workspace layout, settings panel, batch panel, accessibility |
| `docs/design/Phase 06 Design/` | New (9 files) | This design suite |

## Rust New Files

| File | Purpose | Milestone |
|------|---------|-----------|
| `rust/stoat_ferret_core/src/version.rs` | VersionInfo struct with build metadata | M6.2 |
| `rust/stoat_ferret_core/src/schema.rs` | ParameterSchema and effect introspection | M6.3 |
| `rust/stoat_ferret_core/build.rs` | Build-time env vars (timestamp, git sha) — modify if exists | M6.2 |

## Python New Files

| File | Purpose | Milestone |
|------|---------|-----------|
| `src/stoat_ferret/api/routers/version.py` | GET /api/v1/version endpoint | M6.2 |
| `src/stoat_ferret/api/routers/system_state.py` | GET /api/v1/system/state endpoint | M6.7 |
| `src/stoat_ferret/api/routers/seed.py` | POST/DELETE /api/v1/testing/seed endpoint | M6.7 |
| `src/stoat_ferret/api/routers/schema.py` | GET /api/v1/schema/{resource} endpoint | M6.3 |
| `src/stoat_ferret/api/routers/flags.py` | GET /api/v1/flags endpoint | M6.2 |
| `src/stoat_ferret/models/system_state.py` | SystemStateSnapshot, QueueStatus models | M6.7 |
| `src/stoat_ferret/models/seed.py` | SeedFixtureRequest/Response models | M6.7 |
| `src/stoat_ferret/models/version.py` | VersionResponse model | M6.2 |
| `src/stoat_ferret/models/feature_flags.py` | FeatureFlags model | M6.2 |
| `src/stoat_ferret/services/seed_service.py` | Fixture creation and teardown logic | M6.7 |
| `src/stoat_ferret/services/migration_service.py` | Backup-before-migrate, rollback support | M6.2 |
| `src/stoat_ferret/ws/replay_buffer.py` | Bounded ring buffer for event replay | M6.7 |
| `src/stoat_ferret/ws/event_ids.py` | Monotonic event ID generation | M6.7 |
| `Dockerfile` | Multi-stage production build (Python + Rust) | M6.1 |
| `.dockerignore` | Exclude dev files from image | M6.1 |
| `docker-compose.yml` | Local dev/test deployment | M6.1 |
| `scripts/deploy_smoke.sh` | Post-deployment smoke test suite | M6.1 |

## Test New Files

| File | Purpose | Milestone |
|------|---------|-----------|
| `tests/smoke/test_version.py` | Version endpoint smoke tests | M6.2 |
| `tests/smoke/test_system_state.py` | System state endpoint smoke tests | M6.7 |
| `tests/smoke/test_seed.py` | Seed endpoint smoke tests | M6.7 |
| `tests/smoke/test_flags.py` | Feature flags endpoint smoke tests | M6.2 |
| `tests/smoke/test_schema.py` | Schema endpoint smoke tests | M6.3 |
| `tests/smoke/test_ws_replay.py` | WebSocket replay smoke tests | M6.7 |
| `tests/smoke/test_ws_event_ids.py` | Event ID smoke tests | M6.7 |
| `tests/smoke/test_long_poll.py` | Long-poll pattern smoke tests | M6.7 |
| `tests/test_contract/test_migration.py` | Migration safety contract tests | M6.2 |
| `tests/test_contract/test_ws_replay.py` | Replay buffer contract tests | M6.7 |
| `tests/test_contract/test_system_state.py` | System state contract tests | M6.7 |
| `tests/test_blackbox/test_deployment_workflow.py` | Deployment verification black box | M6.1 |
| `tests/test_blackbox/test_agent_workflow.py` | Agent testability E2E black box | M6.7 |
| `tests/test_blackbox/test_ws_reconnection.py` | WebSocket reconnection black box | M6.7 |
| `tests/e2e/test_workspace.spec.ts` | Playwright: workspace layout (J601) | M6.6 |
| `tests/e2e/test_settings.spec.ts` | Playwright: settings panel (J602) | M6.6 |
| `tests/e2e/test_batch_panel.spec.ts` | Playwright: batch panel (J603) | M6.6 |
| `tests/e2e/test_keyboard_nav.spec.ts` | Playwright: keyboard navigation (J604) | M6.9 |
| `tests/e2e/test_accessibility.spec.ts` | Playwright: WCAG AA (J605) | M6.9 |
| `tests/e2e/test_agent_seed.spec.ts` | Playwright: agent seed workflow (J606) | M6.7 |
| `tests/benchmarks/test_api_latency.py` | API latency benchmark suite | M6.5 |
| `tests/benchmarks/test_ws_replay_perf.py` | WebSocket replay benchmark | M6.5 |
| `tests/security/test_audit.py` | Automated security checks | M6.5 |

## GUI New Files

| File | Purpose | Milestone |
|------|---------|-----------|
| `src/gui/src/components/workspace/WorkspaceLayout.tsx` | Root resizable panel layout | M6.6 |
| `src/gui/src/components/workspace/WorkspacePresetSelector.tsx` | Preset dropdown | M6.6 |
| `src/gui/src/components/workspace/PanelVisibilityToggle.tsx` | Panel visibility toggles | M6.6 |
| `src/gui/src/components/settings/SettingsPanel.tsx` | Settings panel | M6.6 |
| `src/gui/src/components/settings/ThemeSelector.tsx` | Theme picker | M6.6 |
| `src/gui/src/components/settings/KeyboardShortcutOverlay.tsx` | Shortcut reference | M6.6 |
| `src/gui/src/components/settings/ShortcutEditor.tsx` | Shortcut rebinding | M6.6 |
| `src/gui/src/components/a11y/AccessibilityWrapper.tsx` | A11y focus and ARIA management | M6.9 |
| `src/gui/src/components/batch/BatchPanel.tsx` | Batch submission and monitoring | M6.6 |
| `src/gui/src/components/batch/BatchJobList.tsx` | Batch job list with progress | M6.6 |
| `src/gui/src/stores/workspaceStore.ts` | Workspace layout state | M6.6 |
| `src/gui/src/stores/settingsStore.ts` | Settings state | M6.6 |
| `src/gui/src/stores/batchStore.ts` | Batch job state | M6.6 |
| `src/gui/src/hooks/useWorkspace.ts` | Workspace hook | M6.6 |
| `src/gui/src/hooks/useSettings.ts` | Settings hook | M6.6 |
| `src/gui/src/hooks/useKeyboardShortcuts.ts` | Global shortcut handler | M6.6 |
| `src/gui/src/hooks/useBatchJobs.ts` | Batch job polling/subscription | M6.6 |
| `src/gui/src/hooks/useFocusTrap.ts` | Focus trap for modals | M6.9 |
| `src/gui/src/hooks/useAnnounce.ts` | Screen reader announcements | M6.9 |

## Documentation New Files

| File | Purpose | Milestone |
|------|---------|-----------|
| `docs/manual/operator-guide.md` | Agent operator guide | M6.8 |
| `docs/manual/prompt-recipes.md` | AI prompt recipes for common scenarios | M6.8 |
| `docs/manual/canonical-workflows.md` | Multi-step workflow documentation | M6.8 |
| `docs/manual/runbook.md` | Operational runbook | M6.4 |
| `docs/manual/troubleshooting.md` | Troubleshooting guide | M6.4 |
| `docs/manual/ws-event-vocabulary.md` | WebSocket event type reference | M6.4 |
| `scripts/examples/wait-for-render.py` | Example: wait for render completion | M6.8 |
| `scripts/examples/dump-ws-events.py` | Example: dump WebSocket events | M6.8 |

## Modified Files

| File | Reason | Milestone |
|------|--------|-----------|
| `src/stoat_ferret/api/app.py` | Register new routers (version, state, seed, schema, flags) | M6.2/M6.7 |
| `src/stoat_ferret/config.py` | Add deployment and WebSocket config fields | M6.1/M6.7 |
| `src/stoat_ferret/api/routers/effects.py` | Add AI hints, ai_summary, example_prompt fields | M6.3 |
| `src/stoat_ferret/api/routers/health.py` | Add database_version, core_version to ready response | M6.2 |
| `src/stoat_ferret/api/routers/batch.py` | Add format-encoder validation at submission (BL-258) | v037 |
| `src/stoat_ferret/ws/connection_manager.py` | Integrate replay buffer, add event_id to all events | M6.7 |
| `src/stoat_ferret/db/schema.py` | Add feature_flag_log, migration_history tables | M6.2 |
| `rust/stoat_ferret_core/src/lib.rs` | Register VersionInfo, ParameterSchema, get_effect_parameter_schemas | M6.2/M6.3 |
| `src/stoat_ferret_core/_core.pyi` | Add VersionInfo and ParameterSchema stubs | M6.2/M6.3 |
| `src/gui/src/components/Shell.tsx` | Replace fixed layout with WorkspaceLayout | M6.6 |
| `src/gui/src/App.tsx` | Add AccessibilityWrapper, skip links | M6.9 |
| `src/gui/src/pages/RenderPage.tsx` | Add batch panel tab | M6.6 |
| `src/gui/src/pages/DashboardPage.tsx` | Add version info card | M6.2 |
| `pyproject.toml` | Add new test dependencies (locust, axe-core) | M6.5 |

Audit v005 of stoat-and-ferret for "wiring gaps" — things designed and implemented as individual pieces but never connected, components created but not registered, API endpoints defined but not mounted, GUI components built but not rendered, or features marked complete that aren't functional at runtime.

Context: We already know about the logging wiring gap — skip that. We're looking for OTHER similar patterns, particularly in the GUI and backend services layer.

## Method

For each theme in v005:

1. **Read the design docs**: Check `comms/inbox/versions/execution/v005/` for requirements.md and implementation-plan.md files
2. **Read the completion reports**: Check `comms/outbox/versions/execution/v005/` for completion-report.md files
3. **Cross-reference against actual code**: Check both `src/stoat_ferret/` (Python) and `gui/` (frontend) directories
4. **Check frontend wiring**: Are all components imported and rendered in the app? Are routes registered? Are API integrations actually calling real endpoints?
5. **Check backend wiring**: Are WebSocket handlers registered? Are new API endpoints mounted on the app? Are services instantiated?
6. **Check static file serving**: Is the GUI actually served by FastAPI?
7. **Check handoff-to-next.md files**: Unactioned suggestions representing wiring gaps

### v005 themes: 01-frontend-foundation, 02-backend-services, 03-gui-components, 04-e2e-testing

## Output Requirements

Create findings in comms/outbox/exploration/wiring-audit-v005/:

### README.md (required)
First paragraph: Summary of wiring gaps found (or "no gaps found" if clean).
Then: Per-theme findings with severity.

### gaps-found.md
For each gap:
- Version/theme/feature
- What was designed vs what's wired up
- Whether completion report caught it
- Severity: critical (non-functional), minor (degraded), cosmetic (dead code)

If no gaps found, state that clearly.

## Guidelines
- Under 200 lines per document
- Skip the known logging gap
- Pay particular attention to frontend-backend integration points — components that render but don't connect to real API endpoints
- Use grep/find to verify wiring
- Commit when complete

## When Complete
git add comms/outbox/exploration/wiring-audit-v005/
git commit -m "exploration: wiring-audit-v005 complete"

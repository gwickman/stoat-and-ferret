Audit v006 and v007 of stoat-and-ferret for "wiring gaps" — things designed and implemented as individual pieces but never connected, Rust functions exposed via PyO3 but never called from Python, API endpoints defined but not mounted, effect registry entries that don't resolve, or features marked complete that aren't functional at runtime.

Context: We already know about the logging wiring gap — skip that. We're looking for OTHER similar patterns, particularly in the effects/filter pipeline and the Effect Workshop GUI.

## Method

For each theme in v006 and v007:

1. **Read the design docs**: Check `comms/inbox/versions/execution/v006/` and `comms/inbox/versions/execution/v007/` for requirements.md and implementation-plan.md files
2. **Read the completion reports**: Check `comms/outbox/versions/execution/v006/` and `comms/outbox/versions/execution/v007/` for completion-report.md files
3. **Cross-reference against actual code**: Check `rust/stoat_ferret_core/src/` for Rust functions, `src/stoat_ferret/` for Python, and `gui/` for frontend
4. **Check Rust-Python wiring**: Are all PyO3-exposed functions actually called from Python code? Are there Rust functions exposed but unused?
5. **Check effect registry**: Are all registered effects resolvable? Does the registry connect to actual filter builders?
6. **Check API endpoint mounting**: Are all effects API routes mounted on the FastAPI app?
7. **Check GUI-to-API wiring**: Does the Effect Workshop GUI connect to real API endpoints?
8. **Check handoff-to-next.md files**: Unactioned suggestions

### v006 themes: 01-filter-engine, 02-filter-builders, 03-effects-api
### v007 themes: 01-rust-filter-builders, 02-effect-registry-api, 03-effect-workshop-gui, 04-quality-validation

## Output Requirements

Create findings in comms/outbox/exploration/wiring-audit-v006-v007/:

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
- Pay particular attention to the Rust-Python boundary — PyO3 bindings that exist but aren't called
- Use grep/find to verify wiring
- Commit when complete

## When Complete
git add comms/outbox/exploration/wiring-audit-v006-v007/
git commit -m "exploration: wiring-audit-v006-v007 complete"

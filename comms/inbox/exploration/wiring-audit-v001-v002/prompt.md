Audit v001 and v002 of stoat-and-ferret for "wiring gaps" — things that were designed and implemented as individual pieces but never connected, settings defined but never consumed, functions created but never called, or features marked complete that aren't functional at runtime.

This is modelled on a known issue: `configure_logging()` was created in v002 but never called at startup, and `settings.log_level` was defined but never consumed. Both passed all quality gates. We want to find any similar patterns across all implemented work.

## Method

For each theme in v001 and v002:

1. **Read the design docs**: Check `comms/inbox/versions/execution/v001/` and `comms/inbox/versions/execution/v002/` for requirements.md and implementation-plan.md files
2. **Read the completion reports**: Check `comms/outbox/versions/execution/v001/` and `comms/outbox/versions/execution/v002/` for completion-report.md files
3. **Cross-reference against actual code**: For each feature reported as complete, verify that the implemented code is actually wired up and functional — not just present as dead code
4. **Check for orphaned settings**: Look in `src/stoat_ferret/api/settings.py` for any settings defined in v001/v002 that are never read by application code
5. **Check for uncalled functions**: Look for functions/classes created in these versions that are never imported or called outside their own module and tests

### v001 themes: 01-rust-python-bindings, 02-tooling-process
### v002 themes: 03-database-foundation, 04-ffmpeg-integration

## Output Requirements

Create findings in comms/outbox/exploration/wiring-audit-v001-v002/:

### README.md (required)
First paragraph: Summary of wiring gaps found (or "no gaps found" if clean).
Then: Per-theme findings with severity (critical/minor/cosmetic).

### gaps-found.md
For each gap found:
- Which version/theme/feature
- What was designed vs what's actually wired up
- Whether the completion report caught it
- Severity: critical (feature non-functional), minor (degraded), cosmetic (dead code)

If no gaps found, state that clearly.

## Guidelines
- Under 200 lines per document
- Test claims by checking actual imports, call sites, and startup paths — not just file existence
- Use grep/find to verify wiring (e.g., is function X imported anywhere outside its own module?)
- Commit when complete

## When Complete
git add comms/outbox/exploration/wiring-audit-v001-v002/
git commit -m "exploration: wiring-audit-v001-v002 complete"

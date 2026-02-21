Audit v003 and v004 of stoat-and-ferret for "wiring gaps" — things designed and implemented as individual pieces but never connected, settings defined but never consumed, functions created but never called, or features marked complete that aren't functional at runtime.

Context: We already know about the logging wiring gap (configure_logging never called, settings.log_level never consumed) — skip that, it's already tracked as BL-056. We're looking for OTHER similar patterns.

## Method

For each theme in v003 and v004:

1. **Read the design docs**: Check `comms/inbox/versions/execution/v003/` and `comms/inbox/versions/execution/v004/` for requirements.md and implementation-plan.md files
2. **Read the completion reports**: Check `comms/outbox/versions/execution/v003/` and `comms/outbox/versions/execution/v004/` for completion-report.md files
3. **Cross-reference against actual code**: For each feature reported as complete, verify the implemented code is actually wired up and functional at runtime
4. **Check for orphaned settings**: Any settings in settings.py defined in these versions that are never consumed
5. **Check for uncalled functions**: Functions/classes created that are never imported or called outside their own module and tests
6. **Check middleware and startup**: Are all middleware components registered? Are all startup hooks called?
7. **Check handoff-to-next.md files**: Look for unactioned suggestions that represent wiring gaps

### v003 themes: 01-process-improvements, 02-api-foundation, 03-library-api, 04-clip-model
### v004 themes: 01-test-foundation, 02-blackbox-contract, 03-async-scan, 04-security-performance, 05-devex-coverage

## Output Requirements

Create findings in comms/outbox/exploration/wiring-audit-v003-v004-retry/:

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
- Skip the known logging gap (BL-056) — we want NEW findings
- Test claims by checking actual imports, call sites, startup paths
- Use grep/find to verify wiring
- Commit when complete

## When Complete
git add comms/outbox/exploration/wiring-audit-v003-v004-retry/
git commit -m "exploration: wiring-audit-v003-v004-retry complete"

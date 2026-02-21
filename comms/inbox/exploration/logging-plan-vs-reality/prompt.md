Explore the stoat-and-ferret comms folders and changelog to compare what was planned/designed for logging vs what was actually implemented.

## Investigation Areas

1. **Changelog**: Check `CHANGELOG.md` or any changelog files in the project root for mentions of logging, structlog, observability, or related work.

2. **Comms inbox** (`comms/inbox/`): Search through version designs, theme designs, and feature requirements for anything related to logging, structured logging, structlog, observability, log levels, configure_logging, correlation IDs, or debug output. Check all versions (v001 through v007+). Look at VERSION_DESIGN.md, THEME_DESIGN.md, requirements.md, and implementation-plan.md files.

3. **Comms outbox** (`comms/outbox/`): Check completion reports, STATUS.md files, and summary.md files for logging-related features. Look for what was reported as done.

4. **Cross-reference**: Compare the design documents' logging requirements against what the previous exploration found — `configure_logging()` is never called, `settings.log_level` is never consumed, and most structlog log statements are silently dropped.

5. **Which version/theme was supposed to implement logging?** Identify the specific version, theme, and feature that owned logging setup. Was it marked complete? Did the completion report flag any gaps?

## Output Requirements

Create findings in comms/outbox/exploration/logging-plan-vs-reality/:

### README.md (required)
First paragraph: Summary of the gap — what was planned, what was delivered, and where it fell through.
Then: Version/theme/feature that owned logging, and whether completion reports caught the gap.

### planned-logging.md
- All logging-related requirements found in design documents
- Which version/theme/feature owned it
- Specific acceptance criteria or implementation plan items for logging
- Include relevant quotes from the design docs

### implemented-logging.md
- What was actually delivered (cross-ref with the check-logging-output exploration)
- What completion reports said about logging
- Whether quality gates or reviews caught the gap
- Any changelog entries about logging

### gap-analysis.md
- Specific items that were designed but not implemented or not wired up
- Items that were reported as complete but aren't functional
- Root cause analysis: was it a design gap, implementation miss, or verification gap?

## Guidelines
- Under 200 lines per document
- Include actual quotes from design/requirements docs
- Be specific about version numbers, theme names, feature names
- Focus on facts, not speculation
- Commit when complete

## When Complete
git add comms/outbox/exploration/logging-plan-vs-reality/
git commit -m "exploration: logging-plan-vs-reality complete"

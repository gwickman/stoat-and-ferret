Investigate how the project was delivered through 9 versions without a .env.example file.

**The issue:** No .env.example exists to guide environment configuration. Users must reverse-engineer required environment variables from source code.

**Your task:** Full audit to trace how this happened.

1. Read the original design docs under `docs/design/` for anything specifying environment configuration, deployment setup, or developer onboarding
2. Review backlog items related to environment config, .env, configuration, and onboarding (search relevant terms)
3. Find which version(s) first introduced environment variable dependencies (Docker, database, FFmpeg paths, etc.)
4. Read the version design documents and implementation plans from comms/ folders
5. Read the retrospectives — was missing developer documentation ever flagged?
6. Examine the actual codebase for how environment variables are consumed (settings.py, config files, docker-compose)
7. Based only on evidence, identify whether this was never considered, deferred, or lost track of
8. Check latest processes, code, and pending backlog for stoat-and-ferret and auto-dev-mcp for gaps already improved since
9. Recommend specific changes

Analysis only — do not make any changes or create any items.

## Output Requirements

Create findings in comms/outbox/exploration/rca-no-env-example/:

### README.md (required)
Summary of findings and recommendations.

### evidence-trail.md
Chronological trace through design → backlog → version → implementation → retrospective.

### recommendations.md
Specific process/tooling changes recommended, noting already-addressed gaps.

## Guidelines
- Keep each document under 200 lines
- Cite specific documents, line numbers, timestamps
- Distinguish evidence from speculation

## When Complete
git add comms/outbox/exploration/rca-no-env-example/
git commit -m "exploration: rca-no-env-example complete"

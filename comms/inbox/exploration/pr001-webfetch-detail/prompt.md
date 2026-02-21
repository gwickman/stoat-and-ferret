Investigate PR-001: "Session health: Orphaned WebFetch calls across 14 instances" — provide a detailed breakdown by version and session.

## Background

The v007-retro-004b-health session health check already identified 14 unique orphaned WebFetch tool_use calls across 11 sessions. These HTTP requests were issued but never returned results. The raw data is in comms/outbox/versions/retrospective/v007/004b-session-health/findings-detail.md.

Here are the 14 known orphaned WebFetch calls:

| Session ID | Tool Use ID | URL | DB Rows |
|------------|-------------|-----|---------|
| `792eb162-520c-44c4-b20c-7aa9535bd873` | `toolu_01QygWk7ruTJJ4wEMJ5z3bWk` | ayosec.github.io/ffmpeg-filters-docs/7.1/Filters/Audio/atempo.html | 4 |
| `98c9d711-45bb-4294-95d0-3bab9a14a7fc` | `toolu_01WBWuJUp2CpndMA93ZdKt2Y` | platform.claude.com/docs/en/about-claude/pricing | 2 |
| `agent-a5f8dfc` | `toolu_01Navb37g1e4YNc2xyd6E273` | releasebot.io/updates/anthropic/claude-code | 1 |
| `4a029681-5c00-4623-81d8-b633eca67df4` | `toolu_01VohDh6N9MPDSQtzqgTATBG` | code.claude.com/docs/en/sub-agents | 1 |
| `agent-ae168d6` | `toolu_019dw4KbiYRerSDbfQD4Wz9c` | platform.claude.com/docs/en/agents-and-tools/tool-use/implement-tool-use | 1 |
| `agent-ab353ea` | `toolu_01HdDSqMkgysFuZ3v5ixuNRA` | gist.github.com/tirufege/0720c288092c1a3a4750f7c198aa524b | 2 |
| `agent-a8410c2` | `toolu_01P6d5g1fojjr2cwWv1iZp2A` | www.braydenblackwell.com/blog/ffmpeg-text-rendering | 1 |
| `agent-a8410c2` | `toolu_01SfXvgj3vswAvPshEBNuNWw` | ffmpegbyexample.com/examples/50gowmkq/fade_in_and_out_text_using_the_drawtext_filter/ | 1 |
| `agent-a3ef471` | `toolu_01To8o5Hj2igTSrQHnmuWwYp` | github.com/golemcloud/golem-ai/issues/23 | 3 |
| `agent-ab31cde` | `toolu_01WH2jbvkMi3nXykc57E82pQ` | algora.io/golemcloud/home | 1 |
| `agent-ab601f1` | `toolu_01RBau1R4HSzby6X9rNE1Ahp` | github.com/MonoGame/MonoGame/issues/8120 | 5 |
| `agent-a73b721` | `toolu_01JkbNVvPUau1aGvyauLFhwQ` | www.upwork.com/freelance-jobs/apply/... | 1 |
| `47054390-287b-4d87-963a-69480668444e` | `toolu_01PgbiNAZFw9Nu2Da664Kq8G` | github.com/Jij-Inc/pyo3-stub-gen | 9 |
| `23c77755-b880-4a44-81fc-c6f3813e9986` | `toolu_01HB9LmpcGuVu2hEt2fKc1mx` | github.com/Jij-Inc/pyo3-stub-gen/tree/main/examples | 2 |

## Investigation Tasks

Use `query_cli_sessions` MCP tool to answer the following:

### 1. Version-by-version breakdown
For each of the 14 orphaned WebFetch calls, determine which version (v001-v007) the session was working on. Use queries like:
```sql
SELECT s.session_id, s.start_time, s.end_time, s.model, s.is_subagent, s.parent_session_id, s.initial_prompt_snippet
FROM sessions s
WHERE s.session_id IN ('792eb162-520c-44c4-b20c-7aa9535bd873', '98c9d711-45bb-4294-95d0-3bab9a14a7fc', 'agent-a5f8dfc', '4a029681-5c00-4623-81d8-b633eca67df4', 'agent-ae168d6', 'agent-ab353ea', 'agent-a8410c2', 'agent-a3ef471', 'agent-ab31cde', 'agent-ab601f1', 'agent-a73b721', '47054390-287b-4d87-963a-69480668444e', '23c77755-b880-4a44-81fc-c6f3813e9986')
```

For sub-agent sessions (agent-*), also look up parent sessions to determine version context:
```sql
SELECT s.session_id, s.parent_session_id, s.initial_prompt_snippet, s.start_time
FROM sessions s
WHERE s.session_id LIKE 'agent-a%'
AND s.session_id IN ('agent-a5f8dfc', 'agent-ae168d6', 'agent-ab353ea', 'agent-a8410c2', 'agent-a3ef471', 'agent-ab31cde', 'agent-ab601f1', 'agent-a73b721')
```

Use the initial_prompt_snippet and start_time to map each session to a version. Cross-reference with version execution dates from the project. Some sessions may not be stoat-and-ferret work - flag those separately.

### 2. Session-level detail
For each affected session: what theme/feature was being worked on, how many WebFetch calls orphaned, what URLs were being fetched.

### 3. Timeline
When did orphaned WebFetch calls start appearing? Was it concentrated in certain versions or spread evenly?

### 4. Root causes
Were these caused by: timeouts on slow URLs, fetching non-existent URLs, fetching URLs from memory vs search results, or something else? Look at the URLs for patterns.

### 5. Impact
Estimate total wasted time from orphaned WebFetch calls if the data supports it (e.g., from session duration data).

### 6. Current status
Note that BL-054 (WebFetch safety rules in AGENTS.md) has been cancelled in favour of auto-dev-mcp BL-536 which addresses this at the MCP server level.

## Output Requirements

Save findings to comms/outbox/exploration/pr001-webfetch-detail/:

### README.md (required)
First paragraph: Summary of orphaned WebFetch distribution across versions.
Then: Key patterns, worst-affected versions, and whether the problem is getting better or worse.

### version-breakdown.md
Per-version table with: version, session count, orphaned WebFetch count, affected themes/features, and any identifiable root causes.

## Guidelines
- Under 200 lines per document
- Include actual session IDs and timestamps where available
- If query_cli_sessions doesn't have the granularity needed, say so explicitly
- Commit when complete

## When Complete
git add comms/outbox/exploration/pr001-webfetch-detail/
git commit -m "exploration: pr001-webfetch-detail complete"
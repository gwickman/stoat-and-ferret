# External Research — v012

## Zustand Paired Selection Pattern (BL-066)

**Source**: DeepWiki — pmndrs/zustand

**Question**: Best practices for managing paired entity selection (source + target clip) in Zustand stores.

**Finding**: Zustand recommends a **single store with slices pattern** for related entities. For BL-066's clip-pair selector:

1. Create a `useTransitionStore` with slices for source and target selection
2. Keep paired selection logic (adjacency validation) in the store, not components
3. Apply the existing effectFormStore pattern — schema-driven form with `defaultsFromSchema()`

**Recommended approach for BL-066**:
```typescript
// Single store managing transition state
const useTransitionStore = create((set, get) => ({
  sourceClipId: null,
  targetClipId: null,
  selectSource: (clipId) => set({ sourceClipId: clipId, targetClipId: null }),
  selectTarget: (clipId) => set({ targetClipId: clipId }),
  isReady: () => get().sourceClipId !== null && get().targetClipId !== null,
  reset: () => set({ sourceClipId: null, targetClipId: null }),
}));
```

**Rationale**: Follows existing per-entity store pattern (effectStackStore, effectCatalogStore) while adding paired selection logic. Adjacency validation can remain server-side (already implemented at effects.py:556-566).

## FFmpeg Progress Reporting (BL-079)

**Source**: Codebase investigation (no external research needed)

FFmpeg progress reporting is already implemented in the codebase:
- `scan.py:214-215`: Progress = `processed / total_files` (0.0 to 1.0)
- `queue.py:349-358`: `set_progress(job_id, value)` stores float
- Render jobs (future): Design spec at `05-api-specification.md:1184-1189` shows 0.45 example

**Recommended realistic values for spec examples**:
| State | progress | Rationale |
|-------|----------|-----------|
| pending | null | No progress before execution starts |
| running | 0.45 | Mid-execution example (matches render spec) |
| complete | 1.0 | Fully completed |
| failed | 0.72 | Partial progress before failure |
| timeout | 0.38 | Partial progress before timeout |
| cancelled | 0.30 | Partial progress at cancellation |

## Dead Code Removal Patterns (BL-061, BL-067, BL-068)

**Source**: Project learnings (LRN-029) + AGENTS.md

**Pattern**: Remove dead code with documented upgrade triggers.

For each removal, document:
1. What was removed (function names, module paths)
2. Why it was removed (zero production callers)
3. What would trigger re-adding (specific future feature)

**Upgrade triggers for v012 removals**:
| Removed | Re-add Trigger |
|---------|---------------|
| execute_command() | Phase 3 Composition Engine or any render/export endpoint that needs Rust command building |
| find_gaps, merge_ranges, total_coverage | Phase 3 Composition Engine (multi-clip timeline editing) |
| validate_crf, validate_speed | Python code needing standalone input validation outside Rust builders |
| Expr (PyO3) | Python-level expression building for custom filter effects |
| compose_chain/branch/merge (PyO3) | Python-level filter graph composition outside Rust builders |

## Session Analytics Insights

**Source: query_cli_sessions** — 60-day project history

### Tool Reliability
| Tool | Calls | Error % | Risk Level |
|------|-------|---------|------------|
| Bash | 16,306 | 14.4% | Expected (command failures are normal) |
| Edit | 2,574 | 9.5% | Medium (non-unique match errors) |
| WebFetch | 84 | 35.7% | High (URL timeouts/failures) |
| mcp__deepwiki__ask_question | 47 | 12.8% | Medium (occasional timeouts, avg 14.5s latency) |
| All MCP auto-dev tools | ~9,500+ | <2% | Low (reliable) |

### Session Duration Patterns
- Exploration sessions (design research): 88-325 seconds (1.5-5.5 min)
- Retrospective sessions: 83-245 seconds (1.4-4 min)
- C4 documentation sessions: 59-263 seconds (1-4.4 min)
- Largest session: 2,747 seconds (45 min, high message count 352)

**Implication for v012**: Features are well-scoped with clear ACs. Based on past session patterns, each feature should complete in 1-2 sessions. The audit-and-trim pattern (BL-067, BL-068) is mechanical and should be fastest.

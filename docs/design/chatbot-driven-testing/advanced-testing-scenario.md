# Advanced Chatbot-Driven Testing Scenario (Adaptive Round, ~2–3 h)

> Status: Living spec. Re-interpret it freshly each round; do not treat it as a script.
> Companion: `advanced-testing-scenario-massive.md` — the multi-day exhaustive variant. Shared rules (safety, evidence schema, budget management, mode discipline) live there and are referenced from this document. Read the actual sections, not paraphrases.
> Audience: a Claude Code CLI session operating locally against a running stoat-and-ferret instance. Run is fully autonomous; the human supervisor points the chatbot at this document and walks away.

---

## Why this document is a goal-shaped spec, not a script

**Target reader:** a current flagship reasoning model (Claude Opus/Sonnet, GPT-5-class, Gemini Ultra, or peer) with access to this project's tool ecosystem. The doc assumes the reader can compose a plan from goals plus grounding, and explicitly leaves test design to the chatbot rather than handing it a recipe.

A prior iteration hard-coded eight scenarios with verbatim steps. Steps drift the moment a doc heading is rewritten, an endpoint is renamed, or a backlog item is closed; the document then either lies or needs constant editing. Goals don't drift.

Autonomy expectations: the chatbot grounds itself, writes a plan, executes it, reports. It does not pause to ask permission. Safety constraints from the massive doc §0 are the only hard limits; everything else (real-mode renders, Playwright for GUI scenarios, the exploratory focus, the time-budget split) is the chatbot's call. If the chatbot genuinely cannot proceed within safety constraints, it records the blocker in the round summary and stops — it does not idle waiting for a human.

---

## Inherited rules

These live in `advanced-testing-scenario-massive.md`:

- **§0 Safety constraints** — non-negotiable. Allow/deny table is authoritative.
- **§4.1 Mode discipline** — `noop` vs `real`.
- **§4.2 Seed strategy** — clean DB from `tests/fixtures/stoat.seed.db`, fresh data dirs, pin `/api/v1/version` into every evidence packet.
- **§4.3–4.4 Background captures** — global WS dump + 10 s metrics scrape sidecars.
- **§4.5 End-of-round teardown** — stop server processes, reseed DB, clear runtime artifact dirs, delete temp files, verify clean exit. Intentional residue is opt-in and must be itemised.
- **§6 Evidence collection protocol** — per-scenario packet shape.
- **§7.5 Context and usage-budget management** — stream evidence to disk, no large bodies in chatbot context, `check_usage` between goal areas, hard stop at 25 % / round.

Re-read those sections, don't restate them here.

---

## Output location

`testing-evidence/chatbot-testing-evidence/{YYYYMMDD_HHMMSS}_adaptive/` at the repo root. Per-scenario packets and `_summary/` follow §6 of the massive doc.

Hard stop: 3 h wall clock. The chatbot writes the summary even on timeout.

---

## Goals (priority order)

The round must answer these questions. Scenario selection serves them, not the reverse.

1. Have recently shipped fixes regressed?
2. Has any older bug returned in a class that has historically recurred?
3. Does the canonical end-to-end path still work on the seed sample?
4. Do the agent-facing canonical docs still match the live API?
5. Where are the cracks in areas prior rounds did not probe — pick one focus and find out.
6. Are mutating-endpoint error messages still agent-actionable?

Goals 1–4 are the regression-detector floor. Goal 5 is the chatbot's own contribution beyond canned coverage. Goal 6 is the recurring ergonomics watch.

---

## Grounding

Read the current state before planning. The chatbot knows how to read these surfaces — the bullets below say what is on each surface, not how to parse it.

- Load the `using-auto-dev-mcp` skill first. It carries the project conventions for the auto-dev-mcp tools used throughout the round (`get_project_info`, `list_backlog_items`, `search_learnings`, `read_document`, etc.), the path-resolution discipline, and the requirement to `tool_help` an unfamiliar tool before first call. Everything below assumes that skill is loaded.
- `{artifacts_root}/docs/auto-dev/plan.md` — recently shipped versions, their headline focus, BL/PR ids closed.
- `docs/CHANGELOG.md` — narrative of what shipped per version, including ad-hoc fixes between versions.
- `git log` for the last two weeks against the project repo — fixes that landed without a numbered version.
- `list_backlog_items(status="open")` — known issues. Read titles + tags first; pull bodies on demand.
- `search_learnings(...)` and `list_learnings(...)` — accumulated knowledge about which bug classes have recurred and what the historical reproducer shape is.
- Most recent run under `testing-evidence/uat-evidence/{TS}/uat-report.md` — fresh evidence about what is already known-green.
- Most recent run under `testing-evidence/chatbot-testing-evidence/{TS}_*/_summary/` — prior adaptive or massive rounds, what they verified, what they found.
- The four canonical agent docs: `docs/manual/operator-guide.md`, `docs/manual/prompt-recipes.md`, `docs/manual/ws-event-vocabulary.md`, `docs/manual/ai-integration-patterns.md`. `git log` per file tells the chatbot whether full-parity or spot-check is warranted.

If grounding takes 20–30 minutes, that is fine. A good plan compresses the round.

---

## Plan, then execute

After grounding, write `testing-evidence/chatbot-testing-evidence/{TS}_adaptive/_plan/round-plan.md`. This is for traceability — the chatbot pins what it decided and why, so a future round can see the choices. The plan is also the chatbot's own working notes; it is not a permission gate.

The plan should make these choices explicit: which fixes are being re-verified, which older recurring classes are being re-proven, the happy-path target, the per-doc parity choice, the exploratory focus and its justification, the error-ergonomics sample, the known-issue avoidance list, and the time budget split. Shape and detail are up to the chatbot.

Once the plan is on disk, start executing. No pause.

---

## Goal area treatments

Each subsection is a short brief. Scripts are deliberately absent.

### Recent-fix regression

Re-verify fixes shipped in the last two versions **or** the last two weeks, whichever spans more change. Scope it generously; better to overlap with a recent UAT than to miss a fix.

For each fix, design the smallest reproducer that would have caught the original bug. If a recent UAT or chatbot round already exercised the affected surface, defer to that evidence and note the deferral — **but only if `git log` shows no changes to the relevant code, docs, or endpoints in the interval**. If the surface has moved since the prior run, the deferral is evidence laundering; re-run.

### Older-fix recurrence (history watch)

Identify bug classes that have re-emerged before — across multiple versions, across multiple BLs with similar tags, or across learnings flagged as recurring. The grounding sources (`list_backlog_items` historical, `search_learnings`, retrospective notes in the artefacts repo, `git log` against high-churn paths) carry this signal. There is no canonical category list; classes evolve. Decide which 2–3 categories are worth a re-prove this round based on what the data says, and rotate the picks over time so coverage drifts across categories.

A recurrence is a stronger finding than a fresh discovery. Severity should reflect that.

### Canonical happy path

Seed → project → timeline → preview → render on the sample project. Run `noop` first and, if green, repeat the final render in `real` to confirm the output is a valid file.

### Doc parity

For each of the four canonical agent docs in grounding, pick full-verbatim, spot-check, or skip based on what `git log` and recent rounds show. Justify the choice once in the plan; don't agonise.

### Exploratory probe

The round's most chatbot-shaped section. Pick one focus that prior rounds and canned suites have not exercised, and run scenarios there. The focus is chosen from current state — recently changed surfaces, untested subsystem boundaries, unusual sequences the docs do not anticipate, agent perspectives the operator-guide does not address. State the focus, the use cases, and why in the plan. "Nothing found" is a legitimate outcome and worth recording.

Constraints: respect §0 safety, capture a reproducer, attach evidence per the standard packet.

### Error ergonomics

Hit a handful of mutating endpoints with deliberately malformed payloads and rate each error body for self-correctability. Endpoint choice, malformation choice, and rubric shape are up to the chatbot; pick what surfaces signal.

---

## Working with open backlog items

The known-issues list from grounding is an input to scenario design, not background reading.

- **Avoidance.** Don't spend effort re-confirming an open bug — *unless* the surface has changed since the bug was filed, or the round is explicitly validating a claimed fix. A known bug sitting in a high-churn area still warrants a quick probe; dodging it there manufactures false confidence.
- **Dedup before filing.** Before writing an inconsistency, check for tag/substring overlap with open BL and PR items. If a finding matches an existing item, point at it rather than create a duplicate.
- **Close-candidate.** If an open BL describes a symptom the round's evidence shows is gone, file a `close-candidate` meta-finding citing the disproving evidence.
- **Plan/backlog divergence.** If `plan.md` says a BL closed in version N but `list_backlog_items` still shows it open, record one `plan-backlog-divergence` finding listing the BL ids. Don't try to reconcile — the supervisor does.

---

## Execution

Goal areas in priority order, single CLI session, serial. Sub-explores are allowed if the exploratory probe earns it, but default to serial; the round is short.

After each goal area, append one line to `_progress.md` with area, status, elapsed, finding count. That's it.

At the 3 h boundary, stop mid-scenario if necessary, mark the in-flight area `TIMEOUT`, write the summary, **launch the independent review per the massive doc §9.5, amend the findings when it returns, then run teardown per §4.5**, then exit. Summary, review, amendments, and teardown all always run, even on timeout. A truncated round with a reviewed summary on a clean machine beats a complete round with no review on a dirty one. If the wall clock leaves no room for the review, file a P1 `bug-operational` finding noting the skipped review and proceed straight to teardown.

---

## Reporting

Under `_summary/`:

- `README.md` — round metadata, per-goal-area outcome, total findings by severity, regression yes/no, **a "Teardown verification" block (§4.5)**, and a five-line plain-text wrap-up for the supervisor.
- `inconsistency-ledger.md` — §6.1-schema entries, deduped against open backlog per the working-with rule above.
- `round-plan.md` — the plan, pinned for traceability.
- `exploratory-probe.md` — focus, use cases, findings, ideas for next round.

The five-line wrap is the actionable deliverable. Everything else is for replay.

Once the reports are on disk, the round continues into the **Independent review** phase (next section) and only then into teardown. The teardown discussion below is unchanged; what's new is the review step that goes between reports and teardown.

---

## Independent review

After the round summary is written and **before** §4.5 teardown runs, launch a cynical second-opinion review explore per the massive doc §9.5. The review is an independent Opus explore that re-derives every verdict from source; the chatbot then propagates the verdicts back into the round artefacts. The round's residue (running server, populated DB) is deliberately left alive for the reviewer to inspect.

Steps:

1. **Launch via `start_exploration`** (model `opus`). Use the prompt template from massive doc §9.5; populate the `{round-id}` (this round's timestamped folder), `{repo}`, and `{results_folder}` (kebab-case, 2–4 words, e.g. `review-adaptive-cynical`). The review writes its substantive output to `independent-review/` under this round's evidence tree, and a short pointer README to the framework outbox `{artifacts}/comms/outbox/exploration/{results_folder}/`.

2. **Monitor with the Test-Path loop, not by polling `get_exploration_status`:**

   ```powershell
   while (-not (Test-Path '<outbox_path>\<results_folder>\README.md')) { Start-Sleep 5 }; Write-Output 'README.md appeared'
   ```

   First attempt: `timeout_ms=120000` (2 min). If it times out, call `get_exploration_status` **once** to confirm the explore is still alive (status `running`, `process_alive: true`), then re-monitor with `timeout_ms=900000` (15 min). A typical adaptive-round review takes 10–20 min.

3. **When complete, read `independent-review/README.md` and amend additively:**
   - Each affected `<goal-area>/findings.md` gets a "## Post-review amendment ({date})" section: verdict (UPHELD / REFUTED / RECLASSIFIED / NEEDS-MORE-EVIDENCE), any severity changes, mechanism corrections, fix-recommendation updates, and a pointer to the relevant `independent-review/` file.
   - `_summary/inconsistency-ledger.md` gets an "## Amendments from independent review ({date})" section near the top: a verdict table (one row per finding), a sub-table for new `INC-REV-NNN` findings, and a re-totalled severity matrix.
   - `_summary/README.md` gets a "## Post-review amendment ({date})" section: the re-totalled severity table, an amended top-findings list, and an amended five-line wrap. The original five-line wrap stays for replay; the amended version is appended.

   The amendment phase is bounded to ~15 min. The review did the substantive work; the chatbot's job is propagation.

4. **If the review fails (timeout > 30 min total, exception, no output)** — file a P1 `bug-operational` finding in the ledger, note in `_summary/README.md` that the round closes without amendments, and proceed to teardown.

Teardown (§4.5) runs **after** amendments, not before. The review explore is itself bound by §0 + §4.5 if it boots anything; the chatbot's teardown is a final sweep across both the round and any residue the reviewer didn't clear.

---

## When this round is appropriate vs the massive variant

| Situation                                                                  | Adaptive | Massive |
|----------------------------------------------------------------------------|---------|---------|
| Recent small-surface or doc-only change, want a regression check            | ✓       |         |
| ~1 week since the last chatbot round, weekly cadence                       | ✓       |         |
| Before kicking off a new version cycle, to confirm baseline                | ✓       |         |
| Specific subsystem suspicion — steer the exploratory focus there           | ✓       |         |
| Quiet period spanning many versions, want exhaustive sweep                 |         | ✓       |
| Need fresh full performance baseline (encoder matrix etc.)                 |         | ✓       |
| Need a large backlog-ready findings list for planning                      |         | ✓       |

This round is intentionally re-runnable on a weekly cadence. The massive round is quarterly or post-major-refactor.

---

## Test corpus on disk

`videos/test-corpus/` (gitignored) holds a small set of CC-licensed real-world clips fetched from the Blender Foundation open-movie archive. Available files at the time of writing:

- `BigBuckBunny_320x180.mp4` — animated short, 10 min, h.264 in MP4, 320×180. Smallest clip in the corpus.
- `big_buck_bunny_480p_h264.mov` — same content, 480p, h.264 in MOV. Different container for the same source.
- `Sintel.2010.720p.mkv` — fantasy short, ~15 min, 720p in MKV.
- `tears_of_steel_720p.mov` — real-world VFX short, ~12 min, 720p in MOV.

The existing `videos/` folder also holds the 6-clip demo set used by `scripts/seed_sample_project.py` and the smoke fixtures. Mind that `seed_sample_project.py` currently recursive-scans `videos/` (see BL-378); avoid relying on the seed contract while the corpus is present unless the corpus location is moved or the scan is fixed.

The corpus exists to broaden what scenarios can pick from — codec, container, resolution, length, real-world content vs. animation. Use whichever clips suit the scenario; nothing in this document tells you which clip goes where.

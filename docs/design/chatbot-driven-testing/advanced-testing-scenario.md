# Advanced Chatbot-Driven Testing Scenario (2–3 Hour Round)

> Status: PLAN — not yet executed.
> Companion: `advanced-testing-scenario-massive.md` — the full multi-day variant of this plan. Most rules (safety, evidence schema, context/budget management) are defined there and **only referenced** here.
> Audience: Claude Code CLI operating locally against a running stoat-and-ferret instance, with a human supervisor.

---

## 0. Inherited rules

These are defined in `advanced-testing-scenario-massive.md` and apply unchanged:

- **§0 Safety constraints** — no deliberate damage to the developer environment. The allow/deny table is the authoritative reference.
- **§6 Evidence collection protocol** — per-scenario evidence packet shape (`actions.jsonl`, `ws-events.jsonl`, pre/post snapshots, `findings.md`, `inconsistencies.jsonl`, `reproducer.md`).
- **§7.5 Chatbot context and usage-budget management** — stream evidence to disk, do not retain bodies in context, `check_usage` between scenarios, hard stop at 25%/round.

Skip back to those sections rather than rereading them in summary form. This document only describes what is *different* about a 2–3 hour scoped round.

---

## 1. Objective

The massive round is a bug *hunter* — a multi-day exhaustive sweep that finds new defects across all subsystems. This round is a **regression *detector*** — a 2–3 hour focused pass that re-verifies the highest-risk surfaces and the most recently-fixed defects to confirm the system has not regressed since the last bug-finding round.

Specifically this round answers, in order:

1. Are the canonical agent-facing docs (operator-guide, prompt-recipes, ws-event-vocabulary) still aligned with the live API?
2. Does the end-to-end seed → timeline → preview → render happy path still work?
3. Do the recent reliability fixes (v066 WS replay contract, v067 GUI error boundary, v067 GUI render_plan construction) still hold?
4. Is the cancellation race still race-free?
5. Are render-submit error messages still agent-actionable?

If all five pass cleanly, the system is regression-clean and the next version can proceed. If any fail, that becomes the focus of a follow-up bug-fix cycle — no need to run the massive round to find it.

Time budget: **2–3 hours wall clock**. Hard stop at 3 hours regardless of progress; whatever has run gets summarised, whatever hasn't is recorded as `SKIPPED_TIME`.

---

## 2. When to run this vs the massive round

| Situation                                                                  | Run this 2–3 h round | Run the massive round |
|----------------------------------------------------------------------------|----------------------|------------------------|
| You just merged a doc-only or small-surface change and want a regression check | ✓                    |                        |
| It's been a week since the last chatbot round and you want a smoke pass    | ✓                    |                        |
| Before kicking off a new version cycle, to confirm the baseline is clean   | ✓                    |                        |
| After a quiet period where multiple versions have shipped, exploring for new defects | | ✓                |
| To establish a fresh performance baseline                                  |                      | ✓                      |
| To produce a backlog-ready list of new findings                            |                      | ✓                      |
| You have a few hours and a known anxiety about a specific subsystem        | ✓ (with targeted scenario)             |                        |

This round can be invoked routinely (weekly cadence is reasonable). The massive round runs ~once per quarter or after major refactors.

---

## 3. Test environment

Same as the massive round, simplified:

- One server instance, fresh DB from `tests/fixtures/stoat.seed.db` via `scripts/init_local_db.py`.
- Default mode is `STOAT_RENDER_MODE=noop`. One scenario (I4) flips to `real` for a single render.
- No new test corpus required. The existing `videos/` folder (the 6 demo MP4s) is the only media surface this round touches — keeps setup time near zero. The massive round's `videos/test-corpus/` is **not** needed.
- Background metrics scrape and global WS capture per §4.3/§4.4 of the massive doc.

Output location: `chatbot-testing-evidence/{YYYYMMDD_HHMMSS}_quick/` at repo root. Same evidence packet shape as massive (§6 of massive doc), but typically smaller (~MB per scenario, not tens of MB).

---

## 4. Scenarios

Eight scenarios. Numbered I1–I8 ("I" = the indispensable subset, also distinct from the massive doc's A–H tiers so they don't get confused).

Each scenario specifies its time budget. The chatbot enforces it: if a scenario hasn't completed within its budget × 1.5, it is recorded as `TIMEOUT` and the round moves on. **The whole-round 3-hour hard stop overrides everything.**

### I1 — Operator-guide canonical loop verbatim (~25 min, noop+real)

**Hypothesis**: The canonical render loop documented in `docs/manual/operator-guide.md` is still copy-paste correct.

**Steps**:
1. Open `docs/manual/operator-guide.md`. Identify the canonical agent sequence (the "run a render" walkthrough).
2. For each step in the document, copy the payload verbatim and execute it against the running server.
3. Log every API call to `actions.jsonl`.
4. Where the doc says "expect status X", verify the live response matches X.
5. Run the full loop in `noop` mode first; if green, repeat the *final render submit only* in `real` mode and let the render complete.

**Pass criteria**:
- Every documented payload accepted (no 422s on documented examples).
- Every documented status token matches what the server emits (`completed` vs `complete`, etc.).
- The render reaches its documented terminal state in both modes.

**Why it matters**: This is the regression check for the v064/v065/v067 doc remediation rounds. If this fails again, the doc has drifted again.

### I2 — Prompt recipes verbatim (~20 min, noop)

**Hypothesis**: The recipes in `docs/manual/prompt-recipes.md` still resolve to working API sequences.

**Steps**:
1. Enumerate each recipe in `prompt-recipes.md`.
2. Execute the underlying API calls for each recipe verbatim (no improvisation).
3. Note which recipes reference helper scripts (`wait-for-render.py`, etc.) and confirm those scripts still execute without error.

**Pass criteria**:
- Every recipe completes its documented outcome.
- No recipe requires a step not in the document.
- Helper script references are accurate.

### I3 — WebSocket event vocabulary round-trip (~20 min, real)

**Hypothesis**: Every event documented in `docs/manual/ws-event-vocabulary.md` is emitted by the live server, with the documented shape, and no undocumented events arrive unannounced.

**Steps**:
1. Connect a WS client and start the global event log.
2. Trigger each documented event by performing the action that should cause it (scan, project create, clip add, preview start, render submit, etc.).
3. For every received event, validate its shape against the documented schema.
4. After the action sweep, diff observed-events against documented-events: missing on either side is a finding.

**Pass criteria**:
- All documented events observed.
- No undocumented event categories observed.
- Shape matches doc for each event.

**Why it matters**: This is the regression check for v066 (WS replay contract) and v067 BL-376 (heartbeat replay doc). Catches event drift before it becomes a v063-style cleanup project.

### I4 — End-to-end happy path on the seed sample project (~25 min, noop + real)

**Hypothesis**: The complete happy path — seed → project → timeline → effects → preview → render — still works end to end on the canonical sample project.

**Steps**:
1. Run `scripts/seed_sample_project.py http://localhost:8765` to build "Running Montage".
2. Confirm the project exists, has 4 clips, 5 effects, 1 transition.
3. Start a preview session, monitor to ready state, terminate.
4. Submit a render in `noop` mode, confirm terminal state.
5. Submit the same render in `real` mode, let it complete, ffprobe the output.
6. Record per-encoder fps for the real render as a one-point perf baseline (a single data point, not the full Tier F sweep).

**Pass criteria**:
- Seed completes without error.
- Preview reaches ready in <30s.
- Both noop and real renders complete; the real render output is a valid video file per ffprobe.
- The recorded fps is within 50% of historical (if a baseline exists from a prior round); otherwise note as a new baseline.

### I5 — WS reconnect & replay contract (~15 min, real)

**Hypothesis**: v066's `Last-Event-ID` replay contract still works under realistic disconnect.

**Steps**:
1. Submit a 60-second `real`-mode render.
2. Connect a WS client; record the highest `event_id` received before disconnect.
3. At ~30% progress, close the socket.
4. Reconnect with `Last-Event-ID` = the recorded value.
5. Verify the replay starts strictly *after* the recorded event_id (no duplicates, no skips).
6. Verify the render completes and the post-disconnect events arrive in order.

**Pass criteria**:
- No duplicate events.
- No skipped events.
- Replay does not include events from other scopes (per-job scoping).
- Render reaches terminal state.

**Why it matters**: This is the regression check for v066 (BL-356/357). The fix landed a wire-format change; this confirms it still holds.

### I6 — Cancellation race smoke (~15 min, noop)

**Hypothesis**: Cancelling a render right at the worker's terminal-state transition does not produce orphan jobs or a wedged queue.

**Steps**:
1. In a tight loop (10 iterations):
   - Submit a fast noop render.
   - Immediately fire `POST /render/{job_id}/cancel`.
   - Record the observed terminal state.
2. After the loop, confirm the queue is empty and no job is stuck in an inconsistent state.

**Pass criteria**:
- Every iteration reaches *some* terminal state (`completed` or `cancelled`); no `running` zombies.
- Queue is empty post-loop.
- Repeated runs are stable (no flaky behaviour across the 10).

### I7 — Render-submit error surface check (~15 min, noop)

**Hypothesis**: A failed render submit shows a useful inline error in the GUI (v067 BL-372 regression check) and the API returns an actionable error body.

**Steps** (Playwright + API):
1. Open `/gui/render`.
2. Submit 5 deliberately-malformed render requests via the GUI form (missing project, missing render_plan, invalid encoder, invalid format, malformed total_duration).
3. For each, screenshot the page state after submit. Verify: the page did **not** unmount (no white-screen), an inline error message appears, the error mentions the offending field.
4. Submit the same 5 malformed requests directly via API. Capture the response bodies and confirm each is a structured error with a usable `detail`.

**Pass criteria**:
- 0 white-screens.
- 0 missing inline errors.
- API error bodies all have structured `detail` and identify the failing field.

**Why it matters**: Regression check for v067 BL-371 + BL-372. The fix landed an error boundary + GUI render_plan; this verifies they survived subsequent changes.

### I8 — Agent ergonomics spot-check (~15 min, noop)

**Hypothesis**: An unfamiliar agent can build valid requests for the core mutating endpoints using only `GET /api/v1/schema` introspection, and gets actionable error messages when wrong.

**Steps**:
1. Pick 3 endpoints: `POST /projects`, `POST /projects/{id}/clips`, `POST /render`.
2. For each, fetch only the schema introspection output (no docs).
3. Build a request body from the schema alone and submit.
4. If accepted: noted as pass. If rejected: read the 422 detail and attempt one self-correction. Note whether the correction succeeded.
5. Separately, submit 5 deliberately-wrong requests across the API and rate each error message on whether an agent could correct itself from it.

**Pass criteria**:
- Schema-built requests succeed within 2 attempts for all 3 endpoints.
- ≥4 of 5 deliberately-wrong errors are self-correctable from the error body alone.

**Why it matters**: This is the regression check for `schema-introspection` (v039) and the recurring P3 error-message quality theme.

---

## 5. Execution model

### 5.1 Order

I1 → I2 → I3 → I4 → I5 → I6 → I7 → I8.

Rationale:
- Doc parity first (I1, I2, I3) — fast, highest hit rate for cheap regressions.
- Happy path (I4) — confirms baseline before pushing on edge cases.
- Edge cases (I5, I6, I7) — known recent fixes; this is what the round is for.
- Ergonomics (I8) — last because if it fails, it does not block the others' findings.

### 5.2 Checkpointing

The chatbot writes a one-line status to `chatbot-testing-evidence/{TS}_quick/_progress.md` after each scenario:

```
I1 PASS  24m  0 findings
I2 PASS  18m  1 finding (P3, recipe X step 4 references endpoint Y but body should be Z)
I3 FAIL  19m  2 findings (P2 — undocumented event "render.heartbeat_extended" observed)
...
```

No tier-level checkpoints; the round is short enough that one continuous progress file suffices.

### 5.3 Parallelism

None. Single CLI session, serial execution. The round is too short to justify sub-explore overhead.

### 5.4 Hard stop

At 3 hours wall-clock, the chatbot stops mid-scenario if necessary, writes a `TIMEOUT` row for the in-flight scenario, writes the summary, and exits. The summary lists every scenario as PASS / FAIL / TIMEOUT / SKIPPED.

---

## 6. Reporting

### 6.1 Round summary

`chatbot-testing-evidence/{TS}_quick/_summary/README.md`:

- Round metadata: start time, end time, runtime version pinned (`/api/v1/version`).
- Per-scenario PASS/FAIL/TIMEOUT with one-line summary.
- Total findings by severity.
- "Regression detected?" — yes/no, with the implicated commit/version if identifiable.

### 6.2 Inconsistency ledger

`chatbot-testing-evidence/{TS}_quick/_summary/inconsistency-ledger.md`:

Same schema as §6.1 of the massive doc, but expected to be small (often empty). If non-empty, the human supervisor inspects each entry before deciding whether to file a backlog item or whether the next action is a bigger run.

### 6.3 Output for the supervisor

A 5-line text summary printed at the end:

```
Quick round complete (2h 47m).
8 scenarios: 7 PASS, 1 FAIL.
Failure: I3 (WS event vocabulary) — 2 findings, P2.
Regression: yes — likely introduced between v066 and HEAD.
Suggested next step: investigate I3 findings, run massive Tier E if widespread.
```

This is the actionable deliverable. Everything else is for replay.

---

## 7. Exit criteria

The round is "done" when one of:

1. All 8 scenarios have a final state (PASS / FAIL / TIMEOUT / SKIPPED) and the summary + ledger are written.
2. The 3-hour hard stop fires and the partial summary is written.

The chatbot does not extend the round past 3 hours without explicit human approval. If a finding is so interesting that more time would help, that is a separate decision recorded as `EXTENSION_REQUEST` in the summary.

---

## 8. What I need from you before this round launches

Far less than the massive round. These are the only open questions:

1. **Run identifier suffix** — assumed `_quick`. Override if you want a more descriptive tag (e.g. `_pre-v068`, `_post-merge-454`).
2. **Confirm the real-mode render in I4** is OK (it does a real FFmpeg encode of the Running Montage sample — a few minutes of CPU). If FFmpeg is missing or you'd rather skip, I4 collapses to noop-only and the perf baseline data point is not recorded.
3. **Should I7 launch Playwright** for the GUI parts, or is API-only acceptable? Playwright adds ~3-5 min for browser launch but catches the actual white-screen condition. API-only catches the structured-error condition but misses the GUI side of BL-372.

Everything else inherits from the massive doc and does not need re-approval.

# Advanced Chatbot-Driven Testing Scenario (Massive Edition)

> Status: PLAN — not yet executed.
> Companion docs: `README.md`, `lightweight-design.md`, `example-workflow.md`, `gap-analysis.md` in this folder; `docs/manual/operator-guide.md`, `docs/manual/prompt-recipes.md`, `docs/manual/ws-event-vocabulary.md`, `docs/manual/ai-integration-patterns.md`.
> Audience: Claude Code CLI operating locally against a running stoat-and-ferret instance, with a human supervisor.
> See also: `advanced-testing-scenario.md` — a tighter 2–3 hour scoped variant of this plan, for when full-corpus exhaustive runs are too expensive.

---

## 0. Safety constraints (READ FIRST)

**Deliberately damaging the developer environment is not allowed. Full stop.**

The chatbot is exercising the application's error and recovery paths. It is **not** exercising the developer's machine. The line is firm:

| Allowed                                                                       | Not allowed                                                                |
|-------------------------------------------------------------------------------|----------------------------------------------------------------------------|
| Killing the stoat-and-ferret server process (it is meant to restart)          | Filling the disk, even by writing into the app's own data directory        |
| Sending malformed API or WebSocket payloads                                   | Modifying or removing system binaries (FFmpeg, ffprobe, sqlite3, python)   |
| Cancelling in-flight jobs, including racing the cancellation                  | Renaming, deleting, or symlinking anything outside the project repo        |
| Briefly locking the project SQLite DB with `BEGIN EXCLUSIVE` (auto-releases)  | Holding a DB lock indefinitely or corrupting the DB file                   |
| Placing deliberately malformed media files in the test corpus                 | Modifying anything in `tests/fixtures/` — these are read-only seeds        |
| Simulating disconnects, restarts, partial mutations from inside the app       | Filling memory deliberately to provoke an OS-level OOM                     |
| Connecting many WebSocket clients up to a documented ceiling                  | Launching unbounded subprocesses, fork-bombs, or background workers        |

If a scenario as written would violate this rule, the chatbot must **skip it and record a `SAFETY_SKIP` entry** in the tier checkpoint, not improvise an alternative that "kind of" damages the environment. The human supervisor will decide whether the scenario can be re-scoped.

Any operation that modifies system state outside the project repo (`/usr`, `/etc`, `C:\Windows`, `C:\Program Files`, `~/.ssh`, `~/.aws`, etc.) is forbidden without exception. The repo + its own `data/` + the `videos/test-corpus/` corpus are the only writeable surfaces.

---

## 1. Objective

The two prior chatbot-driven testing rounds (2026-05-05 and 2026-05-18) each ran for a few hours, exercised the **canonical happy-path agent loop**, and surfaced predominantly *single-call defects* — wrong status tokens, wrong field names, a missing `render_plan`, a Windows path separator, a stale baseline-uat entry. They were valuable but shallow: they re-read the operator-guide and confirmed it page-by-page.

This round is qualitatively different. It treats the chatbot as a **long-running, evidence-producing test pilot** that exercises the full system across all subsystems, deliberately probes for failure modes that prior rounds did not reach (concurrency, restart recovery, cross-day persistence, doc-vs-runtime parity for non-canonical paths), and produces a structured evidence corpus that survives the session. The expected outputs are:

1. A populated `chatbot-testing-evidence/{TS}_round-3/` artifact tree containing per-scenario evidence packets.
2. An **inconsistency ledger** listing every observed gap between documentation claims and runtime behaviour, with severity and reproducibility.
3. A **performance baseline snapshot** (encoder throughput, WS event rates, memory profile during long render) that future rounds can diff against.
4. A backlog-ready findings file (`findings-as-backlog.md`) with proposed `BL-` items pre-formatted for direct ingest.

Time budget: **open-ended.** The chatbot runs to completion of the scenario list; intermediate state is checkpointed so the session can be paused and resumed by the human supervisor.

---

## 2. Why this is "much more thorough" than prior rounds

| Dimension                       | Round 1 (v064) | Round 2 (v067) | Round 3 (this plan) |
|---------------------------------|----------------|----------------|---------------------|
| Subsystems exercised            | 3 (docs, render submit, hygiene test) | 4 (GUI render modal, render error UI, docs, UAT scripts) | **All 14** (scan, library, projects, clips, effects, timeline, composition, preview, proxy, thumbnails, waveform, render, versions, batch) |
| Scenarios run                   | ~10 manual probes | ~15 manual probes | **~70 scripted scenarios across 8 tiers** |
| Failure-mode coverage           | None | None | **Chaos tier: 7 non-destructive scenarios (kill+restart, WS disconnect, corrupt media, brief DB lock, cancellation race, malformed WS frames, replay buffer overflow). See §0 — environment-damaging scenarios are explicitly excluded.** |
| Concurrency coverage            | None | None | **4 scenarios (50 WS clients, 10 parallel renders, 100-clip timeline, 1000-effect catalog)** |
| Persistence / restart coverage  | None | None | **3 scenarios spanning server restarts** |
| Evidence capture                | Ad-hoc prose in transcript | Ad-hoc + uat-evidence dump | **Structured per-scenario packets: actions.jsonl, ws-events.jsonl, pre/post snapshots, ffprobe metadata, screenshots, findings.md** |
| Documentation parity audit      | Operator-guide line scan | Operator-guide + ai-integration-patterns | **Field-by-field audit of every doc against live API: operator-guide, prompt-recipes, ws-event-vocabulary, ai-integration-patterns, 03_api-reference, 04_effects-guide, 07_rendering-guide, 08_ai-integration** |
| Cross-day persistence test      | No | No | Yes (scenario B1) |
| GUI parity audit                | No | No | Yes (Tier G, all GUI pages) |
| Performance baseline            | No | Load test baseline (v047) | **Encoder-matrix throughput + memory profile, with diffable snapshot format** |
| Output is reusable next round?  | Transcript only | uat-evidence dump (partial) | **Artifact tree designed to be diff'd against future rounds** |

The qualitative shift: previous rounds were "read the script, follow the script, log what broke." This round is **exploratory + adversarial + scientific** — every scenario captures a pre-state, an action stream, a post-state, and an inconsistency record. The chatbot is expected to *reason about anomalies*, not just transcribe them.

---

## 3. Actors and roles

- **Application** — local stoat-and-ferret instance, started fresh from a known seed.
- **Chatbot Pilot** — Claude Code CLI session running this scenario plan. Has read-write access to the repo, full local shell access, and can drive the API + WS + Playwright + ffprobe.
- **Human Supervisor (Grant)** — defines goal, approves destructive scenarios (Tier C), inspects checkpoint summaries between tiers, decides whether to proceed.

The chatbot **does not** modify production code during the round. It may write evidence files under `chatbot-testing-evidence/{TS}_round-3/` and may create/update `backlog.json` proposals. Any code change is deferred to a follow-up version triggered by the findings.

---

## 4. Test environment

### 4.1 Baseline modes

Two server modes will be used. The scenario list specifies which mode each scenario requires.

| Mode       | Env var                       | Used for                                 |
|------------|-------------------------------|------------------------------------------|
| `noop`     | `STOAT_RENDER_MODE=noop`      | Tiers A/B doc parity, semantics, queueing, agent flows where the render *content* does not matter |
| `real`    | `STOAT_RENDER_MODE=real` (default) | Tiers C/D/F/G where the actual encode is the thing under test |

The `noop` mode is the primary mode for the long doc-parity tiers because it is fast and deterministic — verified in BL-355 (v065). `real` is used selectively where the actual output bytes matter.

### 4.2 Seed strategy

Each tier begins from a **known seed**. The chatbot:

1. Stops any running instance.
2. Restores `data/stoat.db` from `tests/fixtures/stoat.seed.db` via `scripts/init_local_db.py`.
3. Clears `data/thumbnails/`, `data/proxies/`, `data/waveforms/`, `data/previews/`, `data/renders/`.
4. Starts the server with the scenario-required mode env var.
5. Calls `GET /api/v1/version` to confirm runtime identity and pin it to the evidence packet.
6. Calls `GET /api/v1/system/state` to capture starting state.

For scenarios that need a pre-built project (e.g. render encoder matrix), the chatbot uses `scripts/seed_sample_project.py` (Running Montage) and confirms the resulting project_id is what the operator-guide expects.

### 4.3 Persistent WebSocket capture

For the **entire** round, a background process runs `scripts/examples/dump-ws-events.py` writing to `chatbot-testing-evidence/{TS}_round-3/_global/ws-events.jsonl`. Per-scenario WS capture is *additionally* spawned with a scenario-scoped filter, so events are recorded twice (global archive + per-scenario filtered view). This guarantees that even unanticipated cross-scenario events (e.g. background worker traffic) are not lost.

### 4.4 Metrics scraping

Every 10 seconds, a sidecar scrapes `GET /metrics` and appends to `chatbot-testing-evidence/{TS}_round-3/_global/metrics.jsonl` with a timestamp. Per-scenario the chatbot snapshots immediately before and after each scenario and diffs them.

---

## 5. Test asset acquisition

Stoat-and-ferret needs media. The existing `tests/fixtures/stoat.seed.db` plus the Running Montage sample project give one narrow corpus (3 clips, all the same format). A serious test round needs **diverse media along the axes the application is actually expected to handle**.

### 5.1 Axes to cover

| Axis              | Values                                                     | Why it matters                                                |
|-------------------|------------------------------------------------------------|---------------------------------------------------------------|
| Codec             | H.264, H.265/HEVC, VP9, AV1, ProRes                        | Encoder/decoder dispatch paths in FFmpeg integration          |
| Container         | MP4, MKV, MOV, WebM                                        | Demuxer paths, metadata extraction                            |
| Resolution        | 480p, 720p, 1080p, 4K                                      | Layout calculator, proxy sizing, performance                  |
| Frame rate        | 23.976, 24, 25, 30, 50, 60                                 | Timeline math, render plan duration                           |
| Audio             | None / mono / stereo / 5.1 / 16-bit / 24-bit               | Audio mixing, waveform generation                             |
| Length            | <1s, 5s, 30s, 5min, 60min                                  | Buffer/memory behaviour, progress reporting cadence           |
| VFR vs CFR        | Both                                                       | Variable framerate handling is a classic edge case            |
| HDR               | SDR, HDR10                                                 | Colour space handling (likely fails gracefully today)         |
| Pathological      | Truncated mid-frame, zero-byte, wrong-extension, non-video | Error-handling assertions                                     |

### 5.2 Recommended sources (CC-licensed, easy to script)

**Synthesised via FFmpeg (preferred for deterministic axes):**
- Zero external download. Fully reproducible. Can fabricate exact length, framerate, codec, resolution combinations.
- Example: `ffmpeg -f lavfi -i testsrc2=size=1920x1080:rate=30 -f lavfi -i sine=frequency=440 -c:v libx264 -c:a aac -t 30 -shortest test_30s_1080p_h264.mp4`
- Pathological cases are easy: `dd` truncate, `head -c 1024` for a stub MP4 header without payload, etc.

**Blender Open Movies (CC-BY, ~MB to ~GB):**
- Big Buck Bunny: `https://download.blender.org/demo/movies/BBB/` — 8 minute test feature, multiple resolutions and codecs available.
- Sintel: `https://media.xiph.org/sintel/` — 15 minute test feature, has HDR and 4K variants.
- Tears of Steel: `https://mango.blender.org/download/` — 12 minutes, real-world filming with effects.
- Spring: `https://studio.blender.org/films/spring/` — short film, modern HDR.
- These give *real* video content for visual verification scenarios (where synthesised testsrc2 patterns are not adequate).

**Xiph.org Derf Collection (PD test sequences):**
- `https://media.xiph.org/video/derf/` — short reference clips (e.g. `akiyo_qcif`, `bus_cif`) historically used for codec testing. Useful for VFR / unusual aspect ratio edge cases.

**Pexels CC0:**
- `https://www.pexels.com/videos/` — real-world short clips for visual verification when the user-facing render needs to *look* like something a user would render.

### 5.3 Proposed corpus + acquisition script

Create `scripts/testing/fetch-test-corpus.py` (does not exist yet — **deliverable of this round to write**) that:

1. Reads `videos/test-corpus/corpus-manifest.json` listing each required clip (axis values + source URL or FFmpeg synthesis command + expected sha256).
2. For synthesised clips, runs the FFmpeg command and verifies sha256.
3. For downloaded clips, fetches with retries, verifies sha256, caches under `videos/test-corpus/` (gitignored via the existing `/data/*` rule is **not** sufficient — see compatibility note below).
4. Emits a manifest report (`videos/test-corpus/corpus-status.json`) listing each clip's local path, codec/container/duration/audio summary from ffprobe, and ready-state.

Target corpus size: **~30 synthesised clips + 4 real clips (Big Buck Bunny 480p, BBB 4K, Sintel HDR, one Pexels CC0 real-world clip). Total ~5 GB.**

This is small enough to live on a dev laptop, large enough to exercise the proxy/preview/render paths meaningfully.

#### 5.3.1 Why `videos/test-corpus/` and not `data/test-corpus/`

The existing `videos/` folder at the repo root already holds 6 demo clips used by `scripts/seed_sample_project.py` and the smoke-test fixtures. Co-locating the corpus there keeps "all input media" under one root.

**Compatibility caveats** — verified against the current code:

- `scripts/seed_sample_project.py:114` submits a scan with `recursive: True` against the `--videos-dir` argument (default `./videos`). A subfolder under `videos/` *will* be picked up by that scan and added to the library, inflating the library count from 6 to 6+corpus.
- `tests/smoke/conftest.py` has a `videos_dir` fixture that asserts 6+ MP4s in `videos/` root and a `create_adjacent_clips_timeline` helper that scans the directory. Same recursive-scan exposure.
- `scripts/uat_journey_402.py:120` uses `(PROJECT_ROOT / "videos")` as a scan source.

**Mitigation — required before the round runs:**

1. Add `videos/test-corpus/` to `.gitignore` (the corpus files are big and locally-generated; never tracked).
2. Update the three call sites above to scan with `recursive: False` *or* to enumerate only the top-level demo MP4s explicitly. Recommend keeping the explicit named-file approach the seed script already uses for clip mapping — extending that pattern to the directory listing.
3. The chatbot's own scenarios always scan `./videos/test-corpus/` directly, never the parent `./videos/` recursively. This isolates corpus-driven tests from demo-driven tests.

If step 2 cannot land in the same change, fall back to placing the corpus at `test-corpus/` at the repo root (sibling of `videos/`), which the existing code does not touch.

### 5.4 What I need from you

- **Confirm** the disk budget for `data/test-corpus/` (~5 GB) is acceptable, or specify a smaller target (I can drop the 4K Big Buck Bunny and Sintel HDR to halve this).
- **Confirm** the chatbot may execute network fetches during the round (the Blender + Pexels downloads). If not, the corpus must be entirely synthesised, which limits the visual-verification scenarios.
- One **optional** asset: if you have a real video file from a personal use case that exposes a known frustration ("this video confused the scanner last month"), drop the path in the corpus manifest and the chatbot will treat it as a dedicated scenario.

---

## 6. Evidence collection protocol

The single most important upgrade over prior rounds. Every scenario produces a packet under `chatbot-testing-evidence/{TS}_round-3/<tier>-<id>-<slug>/` containing:

```
chatbot-testing-evidence/{TS}_round-3/A2-effects-catalog-full-coverage/
├── findings.md             # Human-readable summary, severity-tagged
├── actions.jsonl           # Every API call: {ts, method, url, req_body, status, resp_body, latency_ms}
├── ws-events.jsonl         # Scenario-scoped WS event capture
├── metrics-pre.json        # /metrics snapshot before scenario
├── metrics-post.json       # /metrics snapshot after scenario
├── state-pre.json          # /api/v1/system/state before
├── state-post.json         # /api/v1/system/state after
├── version.json            # /api/v1/version (pinned runtime identity)
├── outputs/                # Files produced by the scenario (renders, previews, etc.)
│   └── ffprobe/            # ffprobe -show_format -show_streams of every output file
├── screenshots/            # Optional Playwright captures
├── inconsistencies.jsonl   # One JSON object per observed gap (see schema below)
└── reproducer.md           # Exact steps another agent (or you) can run to replay this scenario
```

### 6.1 Inconsistency record schema

Every gap between expectation and observation goes into `inconsistencies.jsonl`:

```json
{
  "id": "INC-A2-001",
  "scenario": "A2-effects-catalog-full-coverage",
  "claim_source": "docs/manual/04_effects-guide.md:142",
  "claim": "All effects accept a `params` object with parameter overrides.",
  "observed": "Effect `speed_change` rejects `params` with 422 — schema names the field `parameters`.",
  "severity": "P2",
  "category": "doc-runtime-mismatch",
  "reproducer": "curl -X POST .../effects/preview -d '{\"effect_type\":\"speed_change\",\"params\":{...}}'",
  "evidence_files": ["actions.jsonl#L42", "ws-events.jsonl#L7"],
  "proposed_bl": "Either docs rename `params`→`parameters` (XS, P2) or API accept both (S, P3)",
  "first_seen_round": "round-3"
}
```

These are aggregated at the end of the round into `chatbot-testing-evidence/{TS}_round-3/_summary/inconsistency-ledger.md`.

### 6.2 Categories of inconsistency

- `doc-runtime-mismatch` — docs say one thing, server does another.
- `doc-gap` — server behaviour exists but no doc describes it.
- `bug-functional` — server behaviour is wrong by its own spec.
- `bug-performance` — works but exceeds plausible time/memory.
- `bug-ergonomics` — works but error message / response shape is hostile to an agent.
- `bug-gui-parity` — GUI does not reflect API truth.
- `bug-observability` — event/metric/log expected but absent.
- `enhancement` — works fine but the scenario suggests an improvement.

### 6.3 Severity rubric

- `P1` — blocks canonical workflows or causes data loss / silent corruption.
- `P2` — works around-able but degrades agent confidence; visible to a careful user.
- `P3` — cosmetic, documentation, or ergonomic only.

The chatbot **must** justify severity in `findings.md` — the severity field is not a free guess.

### 6.4 Action log discipline

`actions.jsonl` is the chatbot's audit trail. Every API call is logged. The chatbot wraps its HTTP client (or runs every call through a small helper script) so it cannot bypass the log. Latency is captured. Request and response bodies are captured **verbatim** (no summarisation) so a finding can be reproduced byte-exactly.

This matters because past rounds had "the chatbot says X happened" but no machine-verifiable record. This time the artifact tree is the source of truth.

---

## 7. Scenarios

Eight tiers, ~80 scenarios. Tiers run roughly in order but are independent — a tier C failure does not block tier E.

### Tier A — Capability validation (deep, single-subsystem)

Each Tier A scenario takes one subsystem and exercises it exhaustively against its own documented surface.

| ID  | Scenario | Mode | Evidence focus |
|-----|----------|------|----------------|
| A1  | Library scan across the full test corpus (every codec/container/edge case) | real | Metadata extraction completeness per axis; what does the scanner do with corrupt/truncated/zero-byte files? Are errors visible in the WS scan event? |
| A2  | Effects catalogue — call `GET /effects`, then for every returned effect: validate schema introspection (`GET /api/v1/schema`), apply via `/effects/preview`, verify filter string round-trip, apply to a clip, render preview thumbnail | noop | Every effect's `parameters` schema vs actual accepted body; effect_type list parity with docs/manual/04_effects-guide.md |
| A3  | Timeline CRUD exhaustive — every endpoint under `/projects/{id}/timeline` and `/projects/{id}/clips`, including absolute-time vs relative-time semantics, gap handling, overlap rejection, retime | noop | 422 reasons; PATCH/PUT semantics consistency |
| A4  | Composition layouts — every preset from `/compose/presets`, plus a custom layout, applied and previewed | real | Layout math: do clip positions in preview match documented preset? |
| A5  | Preview session full lifecycle — start, monitor readiness, seek, switch quality, terminate, restart | real | WS event sequence vs ws-event-vocabulary.md; HLS manifest correctness |
| A6  | Render encoder × format matrix — for every (encoder, format) in `/render/encoders` × `/render/formats`, submit a render and verify completion + ffprobe output | real | Which combinations are documented as supported but fail? Which fail with poor error messages? |
| A7  | Versioning round-trip — save N versions, list, restore each, delete, confirm DB invariants | noop | Version restore correctness; orphan rows? |
| A8  | Batch operations — submit a batch of 5 renders, monitor aggregate progress, cancel mid-batch | noop | Batch progress event correctness; mid-batch cancellation semantics |
| A9  | Proxy + thumbnail + waveform — for every clip in the corpus, generate all three, verify persistence across server restart | real | Persistence correctness (BL-class issue from gap-analysis); thumbnail cache deduplication |

### Tier B — Cross-subsystem flows

Each Tier B scenario chains multiple subsystems and looks for handoff bugs.

| ID  | Scenario | Mode | Evidence focus |
|-----|----------|------|----------------|
| B1  | Multi-day project lifecycle — Day 1: scan + create project + add 5 clips. Restart server. Day 2: add effects + build timeline. Restart server. Day 3: preview + render. (Chatbot saves checkpoint at each day boundary.) | real | Persistence across restart for every subsystem touched |
| B2  | Project clone — save version, restore into a new project, verify clip/timeline/effect parity | noop | Version round-trip fidelity |
| B3  | Preview → render parity — for the same project, generate a preview and a render. Sample-frame compare the preview HLS segments against the render output at matching timestamps | real | The two pipelines should produce visually consistent output for the same project (modulo encoder quality differences) |
| B4  | Effect-on-clip survival — apply an effect, save version, restore, preview, render. Does the effect survive every hop? | noop | Effect persistence semantics |
| B5  | Concurrent edits from two clients — open the same project from two API clients, mutate in interleaved order, observe last-write semantics and WS event delivery to both | noop | Concurrency model is currently undocumented — any observed conflict resolution becomes a finding |

### Tier C — Failure and recovery (the "chaos" tier, non-destructive)

These scenarios exercise the app's error and recovery paths **without modifying the developer environment** (see §0). Each one perturbs only the running stoat-and-ferret server or its own data, and the post-condition is a clean restart and recovery audit. Five originally-considered scenarios (disk-full simulation, FFmpeg binary removal, deliberate OOM, timing-sensitive cache corruption, FFmpeg subprocess orphan-risk kill) were excluded under §0 — they probed real defects but in ways that risked the dev machine. Equivalent coverage for those gaps belongs in a dedicated CI infrastructure test, not a chatbot session.

| ID  | Scenario | Mode | Evidence focus |
|-----|----------|------|----------------|
| C1  | Server kill during render — submit a 60s render in noop, send SIGTERM at ~30% progress, restart, observe whether the job resumes / fails-cleanly / orphan-locks the queue. Graceful kill only; the server is meant to handle this. | noop | Worker recovery (BL-class historical: v055 worker loop) |
| C2  | WS disconnect during long render — connect a WS client, close the socket at ~50% progress, reconnect with `Last-Event-ID`, verify replay correctness (this is v066's contract — does it hold under fanout load?) | real | Replay contract (BL-356/357); event_id scope correctness |
| C3  | Corrupted media handling — submit scan with the truncated/zero-byte/wrong-extension test corpus subset. Files are pre-built fixtures; nothing is corrupted at runtime. | real | Error message quality; partial library state |
| C6  | DB briefly locked — open a sqlite3 CLI shell, run `BEGIN EXCLUSIVE` for at most 5 seconds, submit a project mutation during the window, then `ROLLBACK`. Lock is bounded by an explicit timer the chatbot controls. | real | DB lock handling; does the request hang, return 503, or 500 within the window? |
| C7  | Cancellation race — submit a render, fire `POST /render/{job_id}/cancel` exactly as the worker transitions to `completed`. Repeat 20 times in noop mode. | noop | Race window between worker terminal-state write and cancel handler |
| C10 | Truncated WS frame — using a low-level WS client (`websockets` library), send a deliberately malformed frame mid-stream. Server should reject the client, not crash. | real | WS server robustness; the chatbot is the only client affected |
| C11 | Replay buffer overflow — issue enough job mutations to exceed the replay deque. Connect with an out-of-range `Last-Event-ID`. Expected: a documented "gap" response, not silent truncation. | noop | Replay overflow semantics (currently undocumented) |

**Excluded scenarios and where to test them instead:**

- *Disk-full behaviour* → CI scenario using a small loopback filesystem with a quota; do not test by filling the developer's actual disk.
- *FFmpeg missing* → CI scenario using a container without FFmpeg; covered by `health/ready` failing readiness, which is also testable via dependency injection (mock the executor in unit tests).
- *Memory ceiling on huge timelines* → property-based test with a synthetic render plan; the failure mode is the same and does not require thrashing the dev machine.
- *Encoder-cache power-fail timing* → unit test with the cache module mocked, asserting it survives a partial-write at the right offset.
- *FFmpeg subprocess kill* → unit test on the executor's `Process.wait` / `Popen.terminate` handling.

These are real coverage gaps and should be filed as backlog items if not already covered — but the chatbot is not the right tool for them.

### Tier D — Concurrency and scale

| ID  | Scenario | Mode | Evidence focus |
|-----|----------|------|----------------|
| D1  | 50 concurrent WS clients, single render — confirm fanout integrity (every client receives every event, in order, no duplicates) | noop | WS broadcast correctness under fanout load |
| D2  | 10 concurrent renders — verify queue ordering, fairness, no starvation; verify that the queue position reported via `/render/queue` is consistent with WS events | real | Queue semantics; back-pressure |
| D3  | 100-clip timeline — render a project with 100 clips; measure render time, memory peak, and timeline-page render latency | real | Performance ceiling; GUI scalability |
| D4  | Pagination soak — `GET /videos?limit=10` across 500 seeded videos; verify total count, no skipped/duplicated rows | noop | Pagination correctness |
| D5  | Effect catalogue pagination — even if today the catalogue is small, simulate 1000 effects (or page through repeatedly) and verify the contract | noop | Pagination contract on /effects |

### Tier E — Documentation parity audit

Each document is read end-to-end by the chatbot; every concrete claim is verified against the live server.

| ID  | Scenario | Source document | Mode |
|-----|----------|------|-----|
| E1  | Operator-guide canonical loop — copy every documented payload verbatim, execute, log discrepancies | docs/manual/operator-guide.md | noop |
| E2  | API reference field-by-field — for every documented endpoint, request, response field: verify presence, type, validation | docs/manual/03_api-reference.md | noop |
| E3  | WS event vocabulary — for every documented event: trigger it and verify shape; for every observed event: confirm it is documented | docs/manual/ws-event-vocabulary.md | real |
| E4  | Effects guide — every documented effect with every documented parameter combination | docs/manual/04_effects-guide.md | noop |
| E5  | Rendering guide — every documented preset, encoder, format combination | docs/manual/07_rendering-guide.md | real |
| E6  | AI integration patterns — verify every claim about reconnect/replay/schema discovery still holds (v066 fixed the heartbeat claim; this is the regression check) | docs/manual/ai-integration-patterns.md | real |
| E7  | Prompt recipes — execute every recipe verbatim end-to-end | docs/manual/prompt-recipes.md | noop |
| E8  | Glossary correctness — for every term, find at least one in-codebase or in-API confirmation of the definition | docs/manual/09_glossary.md | noop |
| E9  | Runbook procedures — for every runbook procedure, verify the steps still work | docs/manual/runbook.md | real |
| E10 | Configuration reference — every documented STOAT_* env var: verify it is read and has the documented effect | docs/manual/configuration-reference.md | both |

### Tier F — Performance and observability

| ID  | Scenario | Mode | Evidence focus |
|-----|----------|------|----------------|
| F1  | Prometheus metric audit — every documented metric: confirm present and labelled; every emitted metric: confirm documented | real | Metric drift |
| F2  | Render throughput baseline — for each encoder, measure FPS over a 60s render of a known reference clip | real | Encoder throughput baseline (diff-able next round) |
| F3  | Memory profile — 30-minute render with periodic RSS sampling | real | Memory leak detection |
| F4  | Happy-path log noise audit — execute the operator-guide loop end-to-end; count error/warning-level logs. Expectation: zero. | real | Log hygiene |
| F5  | Cold-start time — measure server-ready time from boot | real | Startup baseline |
| F6  | WS event rate ceiling — how many events/sec can the server emit before clients lag? | real | WS performance ceiling |

### Tier G — GUI parity audit

Driven by Playwright. The chatbot navigates each page and validates that the rendered DOM reflects the API truth.

| ID  | Scenario | Evidence focus |
|-----|----------|----------------|
| G1  | Library page parity — does the videos list in the DOM match `GET /videos`? | List parity |
| G2  | Project page parity — clips, timeline, effects panels reflect API | DOM parity |
| G3  | Render page parity — running renders, queue, completed history match `/render/*` endpoints | DOM parity |
| G4  | Workspace settings round-trip — change every setting; restart; verify persistence (regression for v044/v049) | Settings persistence |
| G5  | Keyboard nav reachability — every interactive element reachable via keyboard (regression for v052 a11y work) | A11y |
| G6  | Error surface — induce every error category documented in docs/manual/03_api-reference.md error catalogue; verify the GUI renders an inline message (regression for v067 BL-372) | Error UI |
| G7  | Theater Mode behaviour during render — start a render, open theater mode, confirm progress is reflected (v032 integration regression check) | Cross-feature |
| G8  | Workspace layout presets — load each preset, confirm panels mount in the expected positions | Preset correctness |

### Tier H — Agent ergonomics

These scenarios test the chatbot's own experience — they intentionally exercise the system the way an unfamiliar agent would.

| ID  | Scenario | Evidence focus |
|-----|----------|----------------|
| H1  | Cold-start chatbot — using only the operator-guide as context (no other docs), can the chatbot complete every prompt-recipe? | Doc sufficiency |
| H2  | Error message quality — submit 20 deliberately-malformed requests across the API; rate each error message on whether an agent could correct itself from the message alone | Error ergonomics |
| H3  | Schema introspection sufficiency — using only `GET /api/v1/schema`, can the chatbot build a valid request for every mutating endpoint? | Schema completeness |
| H4  | Recovery from partial mutation — induce a 500 mid-multi-step flow; can the chatbot determine the recoverable state from API alone? | State recoverability |
| H5  | Status token namespacing — verify that render endpoints emit `completed` and async/batch endpoints emit `complete`, per BL-358; trigger every state machine | Token correctness |

---

## 7.5. Chatbot context and usage-budget management

A round of this size will exceed any single Claude Code CLI context window if run naively. It will also burn far more API tokens than necessary if the chatbot keeps every request body, response body, and WS event in its working memory. The chatbot must follow these rules.

### 7.5.1 Stream evidence to disk, do not keep in context

- Every action (HTTP request/response, WS event, subprocess call) is **written immediately** to the scenario's `actions.jsonl` / `ws-events.jsonl`. The chatbot does not echo the bodies back into its own context.
- When the chatbot needs to reason about an observation, it reads back **only the relevant fields** (e.g. `jq '.status' actions.jsonl | sort | uniq -c`), not the full body.
- Large response bodies (>1 KB) are referenced by `actions.jsonl#L{n}` in findings, never inlined.
- Render output, preview segments, and screenshots are summarised by their `ffprobe`/`file` output, not their bytes.

### 7.5.2 One scenario, one focus

Each scenario starts fresh: pre-state snapshot, action loop, post-state snapshot, write `findings.md`, **compact the context** (move on without retaining the scenario's verbose body). The chatbot keeps in context only:

- The current tier's goal.
- A running tally of inconsistency IDs filed.
- Cross-references it expects to need in subsequent scenarios.

Everything else lives on disk.

### 7.5.3 Sub-explore offloading for the long tiers

Tiers E (doc parity, ~10 scenarios) and A (capability, ~9 scenarios) are good candidates to offload to **sub-explorations** via `start_exploration` with `parent_exploration_id` set to the master. Each sub-explore handles one tier (or a few related scenarios), writes its own evidence under the same `chatbot-testing-evidence/{TS}_round-3/` tree, and reports a one-page summary back to the master. The master orchestrator never sees the full per-call detail — only the summaries and the inconsistency-ledger entries.

This is the same pattern the version orchestrator uses for design/exec/retrospective. It keeps the master context coherent across a multi-day round.

### 7.5.4 API usage budget

Rough estimates, to be revised after the first tier:

| Tier | Calls in/out of CLI (approx) | Notes |
|------|------------------------------|-------|
| E    | High (the doc lines are the workload) | Use Haiku where possible — line-by-line doc checks are bulk work |
| A    | Medium  | Sonnet for reasoning, Haiku for bulk fixture comparison |
| B    | Medium  | Multi-step flows, mostly Sonnet |
| F    | Low (mostly waiting on real renders) | Sonnet |
| G    | Medium (Playwright + DOM diff) | Sonnet |
| H    | Low to medium  | Sonnet — this tier needs reasoning about doc sufficiency |
| D    | Medium  | Sonnet, but bulk WS event verification can be Haiku |
| C    | Low (7 scenarios)  | Sonnet — recovery semantics need careful reasoning |

The master orchestrator runs `check_usage` between tiers and pauses if usage thresholds are crossed.

### 7.5.5 Hard stop on runaway costs

If `check_usage` reports >25% of the daily/weekly budget consumed in a single tier, the master orchestrator pauses and asks the supervisor before continuing. No tier proceeds silently past a budget threshold.

---

## 8. Execution model

### 8.1 Order

Recommended order, with rationale:

1. **Tier E (doc parity)** first — runs in `noop` mode, exposes the highest-density inconsistencies, cheap, no chaos.
2. **Tier A (capability)** — depth pass on each subsystem, builds confidence in baseline.
3. **Tier B (cross-subsystem)** — exposes integration bugs once each subsystem is known-good.
4. **Tier F (performance)** — must run on quiet system; schedule when no other tier is active.
5. **Tier G (GUI)** — independent, can interleave with any other tier.
6. **Tier H (agent ergonomics)** — best run after E/A so the chatbot already knows the system.
7. **Tier D (concurrency / scale)** — heavier; runs after baseline tiers are clean.
8. **Tier C (chaos)** — LAST. Destructive scenarios should not pollute earlier tiers' evidence. Each scenario followed by clean reseed.

### 8.2 Checkpointing

Between every tier, the chatbot writes a `chatbot-testing-evidence/{TS}_round-3/_checkpoints/after-<tier>.md` summarising:
- Scenarios run, scenarios skipped (and why), scenarios timed-out.
- Inconsistency count by severity.
- Top 5 findings so far.
- Estimated time to next checkpoint.

The human supervisor reviews each checkpoint and either says "continue" or "pause, investigate finding X." This is the natural multi-day cadence.

### 8.3 Parallelism

A single Claude Code CLI session is serial. The chatbot may spawn **sub-explorations** (via `start_exploration` with `parent_exploration_id` set) to run independent tiers in parallel — but only with the human supervisor's explicit approval, because parallel chaos can produce confusing evidence.

Default: serial.

### 8.4 Timeouts and abort criteria

- Per-scenario timeout: 30 minutes (most are 2–10 minutes).
- Per-tier timeout: 8 hours.
- Round abort criteria (chatbot stops and asks the human):
  - A P1 finding that blocks subsequent scenarios in the same tier.
  - More than 5 unexpected 500-class errors across any tier.
  - The application becomes unresponsive in a way not described by a Tier C scenario.
  - `chatbot-testing-evidence/` exceeds 10 GB (sanity bound — evidence should be small; renders are referenced by ffprobe, not stored long-term).
  - Free disk on the working drive drops below 10 GB (regardless of cause — the chatbot stops and waits rather than risk filling the disk).
  - `check_usage` reports >25% budget consumed in a single tier (§7.5.5).
  - Any §0 safety constraint is on the verge of being violated — the chatbot stops, files a `SAFETY_SKIP`, and asks.

---

## 9. Reporting

### 9.1 Per-round summary

`chatbot-testing-evidence/{TS}_round-3/_summary/README.md`:
- Round metadata: dates, runtime version pinned, total scenarios run.
- Tier-by-tier headline numbers.
- Top 10 findings (highest severity × reproducibility).
- Performance baseline numbers (encoder throughput, memory peak, cold-start time).
- Cross-reference: which findings would have been caught by which existing test (smoke / contract / UAT / E2E) had they been written, and which ones genuinely needed a chatbot pilot.

### 9.2 Inconsistency ledger

`chatbot-testing-evidence/{TS}_round-3/_summary/inconsistency-ledger.md`:
- One section per `category` from §6.2.
- Inside each section, items sorted by severity then by `claim_source`.
- Each item lists `id`, `scenario`, `claim_source`, `observed`, `proposed_bl`, `evidence_links`.

### 9.3 Backlog-ready findings

`chatbot-testing-evidence/{TS}_round-3/_summary/findings-as-backlog.md`:
- Pre-formatted as `BL-NEW-*` items: title, priority, size, tags, description (sourced verbatim from `findings.md`), acceptance criteria (derived from the reproducer).
- Ingestible directly by `add_backlog_item` calls in a follow-up planning session.

### 9.4 Performance baseline

`chatbot-testing-evidence/{TS}_round-3/_summary/perf-baseline.json`:
- A machine-readable record of every Tier F measurement, for diff against future rounds.

---

## 10. Exit criteria

The round is "done" when:

1. Every scenario in §7 has either an evidence packet under `chatbot-testing-evidence/{TS}_round-3/` or is documented as `SKIPPED` with a reason in the tier checkpoint.
2. `_summary/README.md`, `inconsistency-ledger.md`, `findings-as-backlog.md`, `perf-baseline.json` all exist and pass a basic schema check (the chatbot runs a `jq`/grep validation pass).
3. The chatbot has summarised the round in plain text to the human supervisor and received explicit approval to close out.

---

## 11. Estimated effort

Rough budget at the per-tier level. Numbers are wall-clock for an active Claude Code CLI session, not human time.

| Tier | Scenarios | Est. duration |
|------|-----------|---------------|
| E    | 10        | 4–6 h         |
| A    | 9         | 6–10 h        |
| B    | 5         | 4–6 h         |
| F    | 6         | 3–5 h (mostly waiting on real renders) |
| G    | 8         | 3–4 h         |
| H    | 5         | 2–3 h         |
| D    | 5         | 3–5 h         |
| C    | 7         | 2–3 h         |
| **Total** | **~55** | **~25–37 h of active CLI time** |

That maps to roughly 3–5 calendar days with checkpoints between tiers, more if the human supervisor wants to investigate findings between tiers.

---

## 12. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Chatbot loses context mid-tier | Every tier starts from a fresh checkpoint. The chatbot can resume from `after-<previous-tier>.md` without rerunning earlier tiers. |
| Evidence files grow huge (renders, WS dumps) | WS dumps rotated per scenario. Render outputs deleted after ffprobe metadata extraction unless flagged for visual review. Targeted size budget ~20 GB. |
| Chaos tier corrupts the dev environment | §0 forbids environment-damaging scenarios; the surviving Tier C scenarios touch only the running server process or the project's own DB (briefly). Clean reseed between scenarios. The originally-considered destructive scenarios are listed as excluded with redirects to safer venues (CI / unit tests). |
| Chatbot context exhaustion mid-tier | §7.5 — evidence streams to disk, sub-explores offload heavy tiers. The master holds only summaries and ledger IDs. |
| API budget overrun | §7.5.4 / §7.5.5 — `check_usage` between tiers, hard stop at 25%/tier, model selection per workload. |
| Inconsistencies become noise | Severity discipline (§6.3); inconsistencies must be reproducible (`reproducer.md`) to count. |
| Human supervisor cannot review checkpoints in real time | The chatbot's default is to **pause** at each checkpoint and wait. Async-friendly. |
| Findings are duplicates of known backlog items | The chatbot cross-references every finding against the current backlog via `search_learnings` and `list_backlog_items` before filing. |
| Test corpus fetch fails partway | `corpus-status.json` tracks ready state; scenarios depending on missing clips are auto-skipped, not failed. |
| Network fetches blocked | If you decline §5.4 network permission, the corpus shrinks to synthesised-only and the four Blender/Pexels visual-verification scenarios are skipped — round still valid. |

---

## 13. What I need from you before the chatbot launches

These are decisions only the supervisor can make. The chatbot will not start the round until they're answered.

1. **Disk + network for the test corpus** — ~5 GB approved (your reply). Confirm placement at `videos/test-corpus/` and accept the small refactor in §5.3.1 (three `recursive: True` callers) before the round runs, OR fall back to `test-corpus/` at the repo root.
2. **Tier C scope confirmation** — Tier C now contains only the non-destructive subset (server kill+restart, WS disconnect, brief DB lock, etc., see §0). Confirm the surviving list is OK; the excluded scenarios are listed with their proposed CI / unit-test homes.
3. **Order tweaks** — default order is §8.1 (E → A → B → F → G → H → D → C). Override if you'd prefer.
4. **Personal asset** (optional) — any real video file you've found frustrating in the past goes into the corpus as a dedicated scenario.
5. **Round identifier** — assumed `round-3` and timestamped folder `chatbot-testing-evidence/YYYYMMDD_HHMMSS_round-3/` at repo root, mirroring `uat-evidence/`. Override if you want a different name.
6. **Model mix** — §7.5.4 proposes Sonnet for reasoning tiers, Haiku for bulk doc-line and event-shape checks. Override if you want everything on Sonnet or everything on Haiku.

Once these are answered the chatbot can execute autonomously across tiers with checkpoint pauses.

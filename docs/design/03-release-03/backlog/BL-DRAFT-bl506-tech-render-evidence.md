# BL-DRAFT-bl506-tech-render-evidence

**Status:** drafted, not filed
**Relationship to BL-506:** **child / sibling technical item** under live BL-506 — **NOT a supersession.** Per codex `14` and T7d's drift table: live BL-506 is the broader verification-workflow parent (output integrity, source attribution, effect presence, workspace hygiene, Windows player compatibility, timebase rule, fontconfig noise). This draft narrowly adds the **render evidence API substrate** that the BL-506 harness depends on. Filing as a supersession would narrow BL-506, which is the opposite of what's needed.
**Suggested title for filing:** `BL-506-tech: persist render evidence artefact for completed jobs`
**Evidence:** `poc-work/poc-obs-render-command/recommendation.md`, codex `12` Section 10, codex `07` Section 8, codex `14` Section 3 Blocker C
**Why now:** the v082 silent-success failure mode was caused by the chatbot-driven harness trusting API success rather than verifying output. Fixing this needs more than docs (parent BL-506) — it also needs a render evidence artefact the harness can consume (this BL).

## Problem statement

PoC-Obs probed the render path for ways to retrieve the actual FFmpeg command a render job invoked. Findings:

- `src/stoat_ferret/render/executor.py:102` emits `render_executor.ffmpeg_command` at DEBUG. Structured but log-level-dependent.
- `ExecutionResult.command: list[str]` exists in-process at `src/stoat_ferret/ffmpeg/executor.py:109` but is not exposed via the API.
- `POST /render/preview` (`src/stoat_ferret/api/routers/render.py:794`) returns a command for *settings* with placeholder data, not for a real job.
- `GET /render/{job_id}` does NOT expose the command, exit code, or stderr.

A harness asserting "the render succeeded" today has no supported way to confirm what was actually executed.

## Proposed acceptance criteria

1. **Render evidence persisted per job.** When the render executor invokes FFmpeg, persist into a job-scoped evidence record:
   - `command_args: list[str]` (exact arg list passed to `asyncio.create_subprocess_exec`)
   - `command_build_error: Optional[str]` (if the command never spawned)
   - `exit_code: Optional[int]`
   - `stderr_tail: str` (last 100 lines or 16 KB, whichever is smaller)
   - `output_path: str`
   - `output_size_bytes: Optional[int]`
   - `filter_script_path: Optional[str]` (if `-filter_complex_script` was used)
2. **API surface.** Expose via either (a) extending `GET /render/{job_id}` with these fields, OR (b) adding `GET /render/{job_id}/evidence`. Pick one.
3. **Redaction + access policy (corrected 2026-06-16 per codex `18` Major Risk).** snf has no admin/role auth surface today (verified by codex `18` grep — no `admin/require_admin/current_user` matches in `src/stoat_ferret/api/`). The model is env-gated, not role-gated:
   - **Default-public surface** (returned in `GET /render/{job_id}`): `exit_code`, `output_size_bytes`, `command_build_error`. Sanitised — no absolute paths, no env-derived values.
   - **Full evidence endpoint** (`GET /render/{job_id}/evidence`): disabled by default; opt-in via **`STOAT_RENDER_EVIDENCE_FULL_ACCESS=true`**. When disabled, returns 403. When enabled, returns full `command_args` + `stderr_tail` + `output_path` + `filter_script_path`.
   - **Redaction pass on full evidence** (always-on): strip any value matching `sk-or-v1-*` (OpenRouter key prefix) or environment-derived `STOAT_*` variable values BEFORE serialisation.
   - This BL owns `STOAT_RENDER_EVIDENCE_FULL_ACCESS`: documented in BOTH `docs/setup/04_configuration.md` AND `docs/manual/configuration-reference.md`. `KNOWN_UNDOCUMENTED_SETTINGS_VARS` stays empty.
4. **Harness contract.** `scripts/verify_render_output.py` (or equivalent) MUST fail loudly when expected evidence fields are absent or empty. No silent pass.
5. **Hygiene test.** Add a test that submits a render, retrieves the evidence, and asserts every field is populated.

6. **Structured event naming (per codex `18` Major Risk).** Fire `render.evidence_persisted` (NOT `render_executor.evidence_persisted` — the `render_executor.*` namespace is not approved; `render.*` is). Companion events from BL-505A: `render.preflight_warning`, `render.preflight_reject`.

7. **OpenAPI freshness:** PR includes regenerated `gui/openapi.json` + `gui/src/generated/api-types.ts`.

8. **Redaction unit tests:** seed an OpenRouter API key (`sk-or-v1-fake-...`) and a `STOAT_*` env-derived value into a render command's args; assert both are stripped from the full-evidence response.

## Out of scope

- Re-architecting the render queue.
- Multi-job evidence aggregation / history endpoints.
- Streaming command/stderr in real-time (post-completion retrieval is enough for BL-506).

## Unit test seeds

```python
def test_render_evidence_populated_on_success(client, sample_project):
    r = client.post(f"/render", json={"project_id": sample_project.id, ...})
    job_id = r.json()["job_id"]
    wait_for_job(job_id)
    e = client.get(f"/render/{job_id}/evidence").json()
    assert e["exit_code"] == 0
    assert e["command_args"][0].endswith("ffmpeg") or e["command_args"][0].endswith("ffmpeg.exe")
    assert e["output_size_bytes"] > 0
    assert "Error" not in e["stderr_tail"][:1024]
```

## Risks / open questions

- Storage size of `stderr_tail` for long-running renders — capped at 16 KB but worth confirming the tail is enough to diagnose typical failures.
- Whether the existing `RenderJobResponse` schema in `src/stoat_ferret/api/schemas/render.py` is extensible without breaking GUI clients.

## Evidence pointers

- `poc-work/poc-obs-render-command/recommendation.md` — original PoC findings
- `07-codex-review-1.md` Section 8 — expansion to render evidence
- `12-codex-review.md` Section 10 — full field list

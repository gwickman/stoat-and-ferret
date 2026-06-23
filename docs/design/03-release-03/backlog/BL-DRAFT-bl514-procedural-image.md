# BL-DRAFT-bl514-procedural-image

**Status:** drafted, **decision locked 2026-06-15: bespoke parser (Option B)**
**Supersedes / amends:** BL-514 (Generic procedural image builder — equation/expression-driven shape generator)
**Evidence:** `poc-work/poc-1-parser-langfit/language-fit.md`, `poc-work/poc-1-parser-langfit/bespoke-spike/`
**Decision locked 2026-06-15:** User chose Option B (bespoke parser) over Option A (adopt AGPL-3.0 evalexpr). Rationale: avoid AGPL drag on the snf binary, keep the maintenance surface small, only ship the grammar BL-514 actually needs.

## Problem statement

snf has fixed-shape generators (BL-441 gradient_generator, BL-441 noise_generator, BL-DRAFT-bl513 spiral/burst/checkerboard/rings). BL-514's pitch is: let users supply an arbitrary mathematical expression evaluated once per pixel, so they can build any procedural pattern.

Naïve design at 1280×720: 921,600 evaluations per frame, 27.6 million per second at 30 fps.

## Language-fit analysis result

Per `poc-work/poc-1-parser-langfit/language-fit.md`:

- `meval`: disqualified (no comparisons, no conditionals)
- `fasteval`: disqualified (missing atan2, hypot, conditionals)
- `mexe`: disqualified (arithmetic only — confirmed by docs grammar)
- `rsx-math`: does not exist on docs.rs
- **`evalexpr` 13.1.0: passes — only candidate** with variables, all required math functions including atan2/hypot, comparisons, and `if(cond,then,else)` conditionals.

## Path chosen — Option B (bespoke parser) — SPIKE COMPLETE

Locked 2026-06-15. Spike validated at `poc-work/poc-1-parser-langfit/bespoke-spike/`. **Verified outcomes:**

| Criterion | Result |
|---|---|
| Implementable in one file | **352 lines of Rust** (codex estimate was 500-1000) |
| Per-pixel eval cost | **~0.42 µs constant** across 320×320 → 1280×1280 |
| 1280×720 single-frame render | **~393 ms** (spike measured 700 ms at 1280×1280) |
| `pow(2, pow(2, 30))` aborts | YES — exponent-magnitude clamp at 100 |
| 40-deep `if()` aborts | YES — AST depth budget 32 |
| `image = "0.25"` integration | clean, no extra deps |

Spike implements exactly the BL-514 grammar:

- Variables: `x`, `y`, `t` (caller injects)
- Math fns: `sin`, `cos`, `tan`, `atan2`, `hypot`, `sqrt`, `exp`, `log`, `abs`, `floor`, `ceil`, `mod` / `%`, `pow`
- Comparisons: `<`, `>`, `<=`, `>=`, `==`, `!=`
- Conditionals: `if(cond, then, else)`
- Safety bounds: AST depth ≤ 32, eval step budget ≤ 10k, `pow`/`^` exponent magnitude ≤ 100

The 352 lines drop into a single `rust/stoat_ferret_core/src/effects/procedural_parser.rs` file. No external parser combinator library; just `std`.

## Proposed acceptance criteria (assumes parser chosen)

1. **GenericProceduralImageBuilder** registered with parameters:
   - `expression: str` — user formula in `x`, `y`, `t` returning a value in [0, 1].
   - `width: int`, `height: int` — output size.
   - `output_format: Literal["rgba","grayscale"]` — defaults to rgba.
2. **Safety bound (corrected per codex `14`):**
   - **AST depth limit ≤ 32** (matches the spike implementation; the earlier "≤ 20" wording was wrong).
   - **Eval step budget ≤ 10,000 per pixel.**
   - **pow / ^ exponent magnitude clamp ≤ 100.**
   - **Per-render wall-clock timeout** (e.g. 5 s for 720p, scales with resolution). NOT per-pixel — the earlier "1 s per pixel" phrasing was nonsensical (would have permitted a single frame to take days).
   - Reject pathological expressions at API boundary via parse-time depth check before render even starts.
3. **Output:** PNG saved to project temp dir; referenced as an image-clip per BL-DRAFT-bl511.
4. **Perf budget:** ≤ 500 ms per frame at 1280×720 on dev workstation (offline render). Verified by the bespoke-spike at ~390 ms. 1920×1080 is ~887 ms.
5. **Animation semantics (clarified per codex `14`):** the grammar includes the variable `t`. The renderer renders ONE frame at a caller-supplied `t` value (e.g. via an `at_time` parameter on the builder). Out-of-scope "per-frame regeneration at 30 fps" means the snf render pipeline does NOT call this builder once per output frame — too slow at 720p+. If a user wants animated procedural content, they synthesise N frames as separate assets and stitch them via the normal multi-clip render. The single-frame-at-t pattern still lets the procedural output participate in larger timeline-based animation via BL-DRAFT-bl512 windows.
6. **Three contract tests:** linear gradient `x`, radial `hypot(x-0.5,y-0.5)`, animated spiral `if(lt(atan2(y-0.5,x-0.5)*3/(2*PI)+hypot(x-0.5,y-0.5)/0.28,0.5),0,1)`.

## Out of scope

- Per-frame regeneration at 30 fps (perf doesn't allow at 720p).
- GPU acceleration.
- User-defined functions / multi-line expressions.

## Dependencies

- BL-DRAFT-bl511 (image-as-clip) for consuming the generated PNG.
- BL-DRAFT-bl513 for the four pre-built shapes — they cover 80% of cases that BL-514 generalises.
- BL-505 render-graph for full consumption.

## Cross-cutting ACs (per codex `18`)

- **PyO3/stub workflow:** the parser ships as a Rust crate with PyO3-visible synthesise function. The PR:
  - Adds PyO3 bindings in the same feature.
  - Regenerates the stub via `cargo run --bin stub_gen`.
  - Updates `src/stoat_ferret_core/_core.pyi` **append-only** (never overwrites with the generated output).
  - Runs `uv run python scripts/verify_stubs.py` and that passes.
- **OpenAPI freshness:** PR includes regenerated `gui/openapi.json` + `gui/src/generated/api-types.ts` if any API schema changes.

## Risks / open questions

- ~~Licence choice~~ — RESOLVED (Option B).
- **Safety budget** — pathological expressions still need clear API-boundary rejection (depth + step budget) in addition to eval-time clamping. The spike validates the step budget aborts cleanly.
- **Per-pixel cost** — measured in the spike (see `bespoke-spike/notes.md`).
- **Future-proof:** if BL-514 users want more language features later (e.g. user-defined functions, loops), the bespoke parser is extensible. Document the grammar as a stable contract that v083 ships.

## Evidence pointers

- `poc-work/poc-1-parser-langfit/language-fit.md` — language-fit matrix
- `poc-work/poc-1-parser-langfit/bespoke-spike/notes.md` — feasibility spike + measured perf + safety probes
- `poc-work/poc-1-parser-langfit/bespoke-spike/src/main.rs` — the 352-line reference implementation
- `13-response-to-codex-review-12.md` (mentions mexe disqualification)

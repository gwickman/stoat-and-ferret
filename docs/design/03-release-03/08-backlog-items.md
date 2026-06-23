# Release 3 — Backlog Items

**Audience:** auto-dev orchestrator, backlog reviewer.
**Status:** drafts. **Nothing has been filed into MCP yet.**

The full BL drafts live in `backlog/`. This document is the index + filing plan + complete filing ledger.

## Project key

The auto-dev MCP project key is **`stoat-and-ferret`** (codex review `18` Section "Scope reviewed" confirmed `snf` is an alias in the description; `stoat-and-ferret` is the canonical key used by all `mcp__auto-dev-mcp__*` calls).

## Filing ledger (complete)

This ledger covers EVERY draft in `backlog/`. Every draft is assigned exactly one disposition: amend (existing BL), create (new BL), or no-op. There are no stranded drafts.

### Disposition codes

- **AMEND** — call `mcp__auto-dev-mcp__update_backlog_item(project="stoat-and-ferret", item_id="BL-NNN", ...)` with the corrected scope, ACs, notes from the draft.
- **CREATE** — call `mcp__auto-dev-mcp__add_backlog_item(project="stoat-and-ferret", title=..., priority=..., description=..., acceptance_criteria=..., notes=..., size=..., tags=..., ...)` with a new item. **No `parent_item_id` parameter exists in the MCP tool schema (codex 18 Blocker 2 verified)** — instead, relationships to existing BLs are expressed via the `notes` field and a `relationship:parent=BL-NNN` tag.
- **NO-OP** — live BL already matches the draft's scope, with evidence; do not file.

### Ledger

| Draft file | Live BL | Disposition | Filing detail |
|---|---|---|---|
| `BL-DRAFT-bl499-path-policy.md` | BL-499 (open) | **AMEND** | Path-escape policy + `emit_filter_option_path` helper + apostrophe rejection |
| `BL-DRAFT-bl502-opacity-redesign.md` | BL-502 (open) | **AMEND** | Runtime redesign via `geq` with uppercase T; three proofs |
| `BL-DRAFT-bl505-render-graph.md` | BL-505 (open) | **AMEND existing + CREATE 2 siblings.** Amend BL-505 to be the umbrella scope statement. Create new items `BL-505A render preflight truthfulness`, `BL-505B render-graph translator (Rust)`, `BL-505C worker integration` as siblings (titles include "BL-505A/B/C"; notes carry `relationship:parent=BL-505`). | 1 update + 2 creates from this draft |
| `BL-DRAFT-bl506-tech-render-evidence.md` | (none — sibling under BL-506) | **CREATE** | Title: `Persist render evidence artefact for completed jobs (BL-506-tech)`. Notes include the parent reference. Tag `relationship:parent=BL-506`. |
| `BL-DRAFT-bl507-zoompan.md` | BL-507 (open) | **AMEND** | Zoompan; `fps,settb` pin mandatory; non-T classification correction |
| `BL-DRAFT-bl508-curves.md` | BL-508 (open) | **AMEND** | Curves preset + KneeString value-kind |
| `BL-DRAFT-bl509-vignette.md` | BL-509 (open) | **AMEND** | Vignette with simpler position+offset surface |
| `BL-DRAFT-bl510-hue-rotation.md` | BL-510 (open) | **AMEND** | Single-quote wrapping; apostrophe rejection |
| `BL-DRAFT-bl511-image-as-clip.md` | BL-511 (open) | **AMEND** | clip_type=image with source_asset_id; argv path (no escape) |
| `BL-DRAFT-bl512-timeline-windows.md` | BL-512 (open) | **AMEND** | Reframe to renderer consumption of existing WindowSpec + per-builder timeline-T flag |
| `BL-DRAFT-bl513-procedural-shapes.md` | BL-513 (open) | **AMEND** | All 4 shapes verified; image=0.25 dep |
| `BL-DRAFT-bl514-procedural-image.md` | BL-514 (open) | **AMEND** | Bespoke parser (not evalexpr); 352-line spike validated |
| `BL-DRAFT-bl515-asset-library.md` | BL-515 (open) | **AMEND** | Full library with security ACs; STOAT_ASSETS_DIR + STOAT_ASSETS_MAX_SIZE_BYTES owned here |
| `BL-DRAFT-bl516-tts.md` | BL-516 (open) | **AMEND** | TTS cue model (per codex `18` Blocker 5); Piper local default + Kokoro cloud; STOAT_OPENROUTER_API_KEY + backend-selection vars owned here |
| `BL-DRAFT-bl517-multitrack-audio.md` | BL-517 (open) | **AMEND** | `ducked_track_id`/`sidechain_track_id`; verified defaults |
| `BL-DRAFT-bl518-subtitle-script.md` | BL-518 (open) | **AMEND** | Subtitle script helper via drawtext chain |
| `BL-DRAFT-bl519-burned-subtitles.md` | BL-519 (open) | **AMEND** | SRT + ASS only (VTT deferred); force_style escape AC |
| `BL-DRAFT-bl520-soft-subtitles.md` | BL-520 (open) | **AMEND** | BCP-47 → ISO-639 mapping; argv path clarification |

### New items NOT in the `backlog/` folder (also CREATE)

Per `02-architecture.md` Section 10 and "Wave V":

| Proposed item | Disposition | Filing detail |
|---|---|---|
| **EffectBuilderValueEscaping** | **CREATE** | Title: `Per-value-kind escape policy + escape_for_filter migration`. Tag `kind:cross-cutting`. Size m. Notes reference BL-499 (path), BL-510 (expression), BL-499 helper. |
| **doc-hygiene STATUS.md dedup** | **CREATE** | Title: `Resolve duplicate STATUS.md (root vs docs/) — docs/STATUS.md canonical`. Size xs. Notes reference T7d in the PoC chain. |

### Counts (reconciled)

| Operation | Count |
|---|---|
| AMEND calls | 17 (one per BL-499/502/505/507-520 except 506 which has no draft for BL-506 itself) |
| CREATE calls from `BL-DRAFT-bl505-render-graph.md` siblings | 2 (BL-505A, BL-505B note: B includes the translator; BL-505C is the third — see below) |
| CREATE for BL-505C | 1 |
| CREATE for BL-506-tech (sibling of BL-506) | 1 |
| CREATE for EffectBuilderValueEscaping | 1 |
| CREATE for STATUS.md dedup | 1 |
| **Total MCP operations** | **23** (17 updates + 6 creates) |
| **Net new backlog items added to the live MCP** | **6** |
| **Net updates to existing items** | **17** |
| **NO-OP drafts** | 0 |
| **Drafts stranded on disk** | 0 |

(Codex `18` Blocker 3 noted my earlier "~20" was hand-wavy. The exact count is 17 updates + 6 creates = 23 operations producing 6 new items.)

## Filing sequencing

Order matters because some drafts reference others:

1. **AMEND BL-499 first.** Renaming the helper to `emit_filter_option_path` is referenced by BL-511, BL-515, BL-519, BL-520, BL-505B, and the EffectBuilderValueEscaping cross-cutting item.
2. **AMEND BL-502 second.** The composition-ordering finding affects BL-505B's design.
3. **AMEND BL-505 + CREATE BL-505A/B/C third.** Splits the umbrella into three filed items.
4. **CREATE BL-506-tech** alongside the BL-505 split.
5. **CREATE EffectBuilderValueEscaping** before the builder amendments (BL-508/509/510 depend on the policy being clear).
6. **AMEND the remaining 14** in any order (independent).
7. **CREATE doc-hygiene STATUS.md dedup last** (xs, isolated).

## Tool-call schema reference

For each operation, the actual MCP tool call signature (from `mcp__auto-dev-mcp__add_backlog_item` / `update_backlog_item` schemas):

### add_backlog_item

Fields (per codex `18` Blocker 2):
- `project: "stoat-and-ferret"` (required)
- `title: str`
- `priority: enum`
- `description: str`
- `quality_assertion: str`
- `size: enum`
- `tags: list[str]`
- `acceptance_criteria: list[str]`
- `notes: str`
- `use_case: str`

**No `parent_item_id`.** Parent-child relationships are expressed via:
- `tags: ["relationship:parent=BL-NNN"]`
- `notes: "Parent item: BL-NNN. <reason>."`
- Title prefix when applicable (`BL-NNN-tech: ...`).

If first-class parent-child support is later desired, that becomes its own backlog item against `auto-dev-mcp`, separate from this release.

### update_backlog_item

Updates the fields above on an existing item. Use for AMEND operations.

## Wave + version mapping

| Version | Waves landed | Estimated BL operations in that version |
|---|---|---|
| v083 | Wave 0 (carry-forwards BL-499 + BL-502) + Wave 1 (BL-505A preflight + BL-506-tech evidence) | 2 amends + 2 creates |
| v084 | Wave 2 (BL-505B + BL-505C) + Wave V (EffectBuilderValueEscaping create) | 2 creates + 1 create |
| v085 | Wave 3a (5 builders: BL-507/508/509/510/513) + Wave 4 (BL-512) | 6 amends |
| v086 | Wave 3b (BL-515 + BL-511) + Wave G (BL-514) | 3 amends |
| v087 | Wave 5 (BL-517) + Wave 6 (BL-516) | 2 amends |
| v088 | Wave 7 (BL-518 + BL-519 + BL-520) + Wave T/D wrap-up + STATUS.md dedup create | 3 amends + 1 create + doc work |

Six versions total. Each version's MCP operations are a strict subset of the ledger above. Auto-dev refines the wave-to-version mapping based on capacity at design time.

## What auto-dev needs to know per item

Each draft contains the information auto-dev needs to translate the BL into a version plan:

- **Acceptance criteria** — testable outcomes.
- **Out of scope** — what NOT to build.
- **Unit test seeds** — code-level test patterns the implementer extends.
- **Dependencies** — which other BLs must land first.
- **Risks / open questions** — what's still uncertain at design time.

## Index of full drafts

All drafts under `backlog/` use a consistent template. See `backlog/README.md` for the index.

## Open questions for the review pass

Before filing, the user should confirm:

1. The wave structure in `01-roadmap.md` and the version mapping (v083-v088).
2. The product calls in `03-capabilities-and-requirements.md` Section "Open product / scope questions".
3. The CREATE titles for the new items (`BL-506-tech`, `BL-505A/B/C`, `EffectBuilderValueEscaping`, STATUS.md dedup).
4. Whether VTT subtitle support is genuinely deferred to v084+ or should be in-scope.
5. Whether the cross-cutting `EffectBuilderValueEscaping` ships before or after the four single-filter wraps (BL-508/509/510 depend on the policy).
6. Whether `parent_item_id` should become a separate auto-dev-mcp feature ticket (independent of this release).

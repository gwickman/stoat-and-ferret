# Release 3 — Backlog drafts

These are the **complete BL drafts** for Release 3. **Nothing has been filed into auto-dev MCP yet.** That step happens only after user approval of the design package.

## File index

| File | Live BL | Action |
|---|---|---|
| `BL-DRAFT-bl499-path-policy.md` | BL-499 (open) | Amend (Batch 1) |
| `BL-DRAFT-bl502-opacity-redesign.md` | BL-502 (open) | Amend (Batch 1) |
| `BL-DRAFT-bl505-render-graph.md` | BL-505 (open) | Amend + split into A/B/C |
| `BL-DRAFT-bl506-tech-render-evidence.md` | (none) | **New sibling** under live BL-506 (Batch 2) |
| `BL-DRAFT-bl507-zoompan.md` | BL-507 (open) | Amend |
| `BL-DRAFT-bl508-curves.md` | BL-508 (open) | Amend |
| `BL-DRAFT-bl509-vignette.md` | BL-509 (open) | Amend |
| `BL-DRAFT-bl510-hue-rotation.md` | BL-510 (open) | Amend |
| `BL-DRAFT-bl511-image-as-clip.md` | BL-511 (open) | Amend |
| `BL-DRAFT-bl512-timeline-windows.md` | BL-512 (open) | Amend (reframe; live wording overlaps with v080 WindowSpec) |
| `BL-DRAFT-bl513-procedural-shapes.md` | BL-513 (open) | Amend |
| `BL-DRAFT-bl514-procedural-image.md` | BL-514 (open) | Amend |
| `BL-DRAFT-bl515-asset-library.md` | BL-515 (open) | Amend |
| `BL-DRAFT-bl516-tts.md` | BL-516 (open) | Amend |
| `BL-DRAFT-bl517-multitrack-audio.md` | BL-517 (open) | Amend |
| `BL-DRAFT-bl518-subtitle-script.md` | BL-518 (open) | Amend |
| `BL-DRAFT-bl519-burned-subtitles.md` | BL-519 (open) | Amend |
| `BL-DRAFT-bl520-soft-subtitles.md` | BL-520 (open) | Amend |

## Draft template

Each draft follows the same template:

- **Status** — draft or filed
- **Supersedes / amends** OR **Relationship to BL-XXX** — supersession / amendment / sibling status
- **Evidence** — PoC paths and prior-review references
- **Why now** — justification for the change
- **Problem statement**
- **Proposed acceptance criteria** — testable outcomes
- **Out of scope**
- **Unit test seeds** — code-level test patterns the implementer extends
- **Dependencies** — which other BLs must land first
- **Risks / open questions**
- **Evidence pointers** — links into the PoC chain

## Codex review state

These drafts have been through codex reviews 14 (BL set review) and 16 (response review). Three residual fixes from review 16 were applied:

1. BL-515 config-doc paths corrected to `docs/setup/04_configuration.md` + `docs/manual/configuration-reference.md`.
2. BL-519 v1 scope tightened to SRT + ASS only; VTT explicitly deferred (no residual VTT references in v1 ACs).
3. BL-520 AC #4 ("Asset escape: same BL-499 path policy") removed; replaced with the argv-vs-filter-option distinction. AC numbering corrected.

The drafts are filing-ready.

## NEW items not in this folder

Two items are referenced in the design but don't have a draft here because they're cross-cutting and small:

- **EffectBuilderValueEscaping** — the per-value-kind escape policy ticket. See `02-architecture.md` Section 10. Sized as m. Best filed as a new BL with `add_backlog_item` after BL-499 is amended (it references the helper from BL-499).
- **doc-hygiene STATUS.md dedup** — resolve duplicate STATUS.md. See the closing note in `<gw-test>/snf-showcase-20260614/gaps-identified/00-BACKLOG-ITEMS.md`. Size xs.

Both are flagged in `../08-backlog-items.md` Section "Batch 2".

## How auto-dev should consume these

For each draft:

1. Read the "Proposed acceptance criteria" → translate into version feature ACs.
2. Read "Out of scope" → ensure feature scope doesn't drift.
3. Read "Unit test seeds" → seed the test author's work.
4. Read "Dependencies" → confirm prerequisite BLs are already worked or being worked.
5. Read "Risks / open questions" → surface to the design pass for that BL if any open.

The auto-dev process typically buckets BLs into versions per the wave structure in `../01-roadmap.md`. The wave structure already accounts for dependencies; auto-dev's version-execution phase fills in implementation details.

## Audit trail

Drafts were authored 2026-06-13 — 2026-06-15 over an extended PoC + review chain. Source artefacts and the full chain of review documents live at `<gw-test>/snf-showcase-20260614/gaps-identified/`. The repo-side authoritative state is this folder.

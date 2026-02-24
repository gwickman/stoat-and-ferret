# Design v012 — Document Drafts

Complete document drafts for v012 (API Surface & Bindings Cleanup): 2 themes, 5 features. All documents are lean, referencing the design artifact store at `comms/outbox/versions/design/v012/` for detailed analysis.

## Document Inventory

| Document | Location |
|----------|----------|
| manifest.json | `drafts/manifest.json` |
| VERSION_DESIGN.md | `drafts/VERSION_DESIGN.md` |
| THEME_INDEX.md | `drafts/THEME_INDEX.md` |
| Theme 01 Design | `drafts/rust-bindings-cleanup/THEME_DESIGN.md` |
| Feature 01-001 Requirements | `drafts/rust-bindings-cleanup/execute-command-removal/requirements.md` |
| Feature 01-001 Impl Plan | `drafts/rust-bindings-cleanup/execute-command-removal/implementation-plan.md` |
| Feature 01-002 Requirements | `drafts/rust-bindings-cleanup/v001-bindings-trim/requirements.md` |
| Feature 01-002 Impl Plan | `drafts/rust-bindings-cleanup/v001-bindings-trim/implementation-plan.md` |
| Feature 01-003 Requirements | `drafts/rust-bindings-cleanup/v006-bindings-trim/requirements.md` |
| Feature 01-003 Impl Plan | `drafts/rust-bindings-cleanup/v006-bindings-trim/implementation-plan.md` |
| Theme 02 Design | `drafts/workshop-and-docs-polish/THEME_DESIGN.md` |
| Feature 02-001 Requirements | `drafts/workshop-and-docs-polish/transition-gui/requirements.md` |
| Feature 02-001 Impl Plan | `drafts/workshop-and-docs-polish/transition-gui/implementation-plan.md` |
| Feature 02-002 Requirements | `drafts/workshop-and-docs-polish/api-spec-corrections/requirements.md` |
| Feature 02-002 Impl Plan | `drafts/workshop-and-docs-polish/api-spec-corrections/implementation-plan.md` |

**Total**: 1 manifest + 1 version design + 1 theme index + 2 theme designs + 10 feature docs = **15 documents**

## Reference Pattern

All documents follow a lean reference pattern:
- Feature requirements and implementation plans reference the design artifact store for evidence rather than duplicating research findings
- Theme designs reference `006-critical-thinking/` for risk analysis
- Version design references all 5 artifact store subdirectories
- Specific file paths and line numbers are cited from `004-research/codebase-patterns.md` and `004-research/evidence-log.md`

## Completeness Check

All 5 backlog items are covered:

| Backlog | Feature | Theme |
|---------|---------|-------|
| BL-061 | execute-command-removal | rust-bindings-cleanup |
| BL-066 | transition-gui | workshop-and-docs-polish |
| BL-067 | v001-bindings-trim | rust-bindings-cleanup |
| BL-068 | v006-bindings-trim | rust-bindings-cleanup |
| BL-079 | api-spec-corrections | workshop-and-docs-polish |

## Format Verification

- THEME_INDEX.md: 5 feature lines validated against parser regex `- \d{3}-[\w-]+: .+`
- manifest.json: Valid JSON with all required fields (version, description, backlog_ids, context, themes)
- No placeholder text found in any document
- No theme/feature slug starts with digit prefix
- All "Files to Modify" paths verified against codebase
- No MCP tool call instructions in feature documents

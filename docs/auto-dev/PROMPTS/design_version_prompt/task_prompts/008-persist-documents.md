# Task 008: Persist Documents

Read AGENTS.md first and follow all instructions there.

## Objective

Call the MCP design tools to persist all drafted documents to the inbox folder structure.

## Context

This is Phase 3 (Document Drafts & Persistence) for `${PROJECT}` version `${VERSION}`.

Task 007 created all document drafts. Now persist them using MCP tools.

**WARNING:** Do NOT modify any files in `comms/outbox/versions/design/${VERSION}/`. These are the reference artifacts. If you find errors, document them and STOP.

## CRITICAL: Machine-Parseable Format Requirements

The following files are machine-parsed and require EXACT format preservation:

### THEME_INDEX.md - Feature List Format

**Parser regex:** `- (\d+)-([\w-]+):`

**REQUIRED format for feature lists:**
```
**Features:**

- 001-feature-name: Brief description text here
- 002-another-feature: Another description text
```

**FORBIDDEN formats that break parser:**
- Numbered lists: `1.` `2.` `3.`
- Bold feature identifiers: `**001-feature-name**`
- Metadata before colon: `001-feature (BL-123, P0, XL)`
- Multi-line feature entries
- Missing colon after feature name

## Tasks

### 1. Read Task 007 Output

Read the manifest and individual draft files from Task 007:

```
drafts_dir = comms/outbox/exploration/design-${VERSION}-007-drafts/drafts/
```

1. Read `{drafts_dir}/manifest.json` — contains version metadata, theme/feature
   numbering, goals, backlog IDs, and context
2. Read `{drafts_dir}/VERSION_DESIGN.md`
3. Read `{drafts_dir}/THEME_INDEX.md`
4. For each theme in manifest: read `{drafts_dir}/{theme_slug}/THEME_DESIGN.md`
5. For each feature in manifest: read `{drafts_dir}/{theme_slug}/{feature_slug}/requirements.md`
   and `{drafts_dir}/{theme_slug}/{feature_slug}/implementation-plan.md`

**CRITICAL — Use Slugs from Manifest:**
- Pass `theme["slug"]` as the `theme_name` parameter to `design_theme` and in the themes array for `design_version`
- Pass `feature["slug"]` as the feature `name` parameter
- Do NOT add number prefixes — the MCP tools add them automatically
- Passing pre-numbered names like `"01-config-and-guidance"` causes double-numbering bugs

**Error Handling:** If any file referenced by the manifest is missing:
1. List all missing files
2. Report which themes/features are affected
3. STOP without calling any MCP tools
4. Recommend re-running Task 007

### 2. Prepare Context Object

Read the context object directly from `manifest.json`:

```python
manifest = read_json(f"{drafts_dir}/manifest.json")
context = manifest["context"]
```

### 3. Prepare Themes Array

Build the themes structure from the manifest. Use slugs (NOT numbered names):

```python
manifest = read_json(f"{drafts_dir}/manifest.json")
themes = [
    {
        "name": theme["slug"],          # slug only, tool adds prefix
        "goal": theme["goal"],
        "features": [
            {"name": f["slug"], "goal": f["goal"]}
            for f in theme["features"]
        ]
    }
    for theme in manifest["themes"]
]
```

**CRITICAL:** Verify structure:
- [ ] `themes` is a list (not a string)
- [ ] Each theme `name` is a slug WITHOUT number prefix
- [ ] Each feature `name` is a slug WITHOUT number prefix
- [ ] Each theme has `name`, `goal`, `features` keys
- [ ] Each feature has `name`, `goal` keys

### 4. Call design_version

```python
design_version(
    project="${PROJECT}",
    version=manifest["version"],
    description=manifest["description"],
    themes=themes,
    backlog_ids=manifest["backlog_ids"],
    context=manifest["context"],
    overwrite=false
)
```

Document the result (success or error).

### 5. Call design_theme for Each Theme

For EACH theme, use a manifest-driven loop:

```python
for theme in manifest["themes"]:
    theme_design = read_file(f"{drafts_dir}/{theme['slug']}/THEME_DESIGN.md")
    features = []
    for f in theme["features"]:
        req = read_file(f"{drafts_dir}/{theme['slug']}/{f['slug']}/requirements.md")
        plan = read_file(f"{drafts_dir}/{theme['slug']}/{f['slug']}/implementation-plan.md")
        features.append({
            "number": f["number"],
            "name": f["slug"],              # slug only, tool adds prefix
            "goal": f.get("goal"),           # for THEME_INDEX.md feature descriptions
            "requirements": req,
            "implementation_plan": plan      # underscore, not hyphen
        })

    design_theme(
        project="${PROJECT}",
        version=manifest["version"],
        theme_number=theme["number"],
        theme_name=theme["slug"],           # slug only, tool adds prefix
        theme_design=theme_design,
        features=features,
        mode="full"
    )
```

**CRITICAL - Feature Object Required Fields:**
Each feature dict MUST contain ALL of these fields:
- `number` (int): Feature number within the theme, 1-indexed sequential
- `name` (str): Feature slug WITHOUT number prefix (e.g., "feature-name", NOT "001-feature-name")
- `goal` (str | None): Feature goal from manifest for THEME_INDEX.md descriptions (omit or None to use placeholder fallback)
- `requirements` (str): Full requirements.md markdown content
- `implementation_plan` (str): Full implementation-plan.md markdown content (NOTE: underscore, not hyphen)

Missing the `number` field or using `implementation-plan` instead of `implementation_plan` will cause a KeyError.

### 6. Validate Design Completeness

Call `validate_version_design`:

```python
validate_version_design(
    project="${PROJECT}",
    version="${VERSION}"
)
```

Expected: All documents exist, no missing files.

## Output Requirements

Create in `comms/outbox/exploration/design-${VERSION}-008-persist/`:

### README.md (required)

First paragraph: Summary of persistence operation (success/failure, documents created).

Then:
- **Design Version Call**: Result and any errors
- **Design Theme Calls**: Result for each theme
- **Validation Result**: Output from validate_version_design
- **Missing Documents**: Any documents not created (should be none)

### persistence-log.md

Detailed log of all MCP calls:

```markdown
## design_version Call
**Parameters**: project, version, themes count, backlog_ids count
**Result**: [success/error]
**Output**: [tool output]

---

## design_theme Call - Theme 01
**Parameters**: theme_number, theme_name, features count
**Result**: [success/error]
**Output**: [tool output]

[Repeat for all themes]

---

## validate_version_design Call
**Result**: [success/error]
**Output**: [tool output]
**Missing Documents**: [list or "None"]
```

### verification-checklist.md

Document existence verification:
- [ ] `comms/inbox/versions/execution/${VERSION}/VERSION_DESIGN.md` exists
- [ ] `comms/inbox/versions/execution/${VERSION}/THEME_INDEX.md` exists
- [ ] [... all documents listed]

Use `read_document` to verify each file exists.

## Allowed MCP Tools

- `read_document`
- `design_version`
- `design_theme`
- `validate_version_design`
- `list_product_requests`
- `get_product_request`
- `add_product_request`
- `update_product_request`
- `upvote_item`

## Guidelines

- ALL backlog items from PLAN.md are MANDATORY — verify all items appear in persisted documents before completing
- Verify array structure before calling design_version (see Step 3)
- Content passed to MCP tools should be the lean referenced versions from Task 007
- If any MCP call fails, document the error clearly and STOP
- Validate that ALL documents were created successfully
- Do NOT modify the design artifact store

## Error Handling

If any MCP call fails:
1. Document the exact error message
2. Document parameters used in the failing call
3. Do NOT continue to subsequent calls
4. Mark exploration as requiring manual intervention

## When Complete

```bash
git add comms/outbox/exploration/design-${VERSION}-008-persist/
git commit -m "exploration: design-${VERSION}-008-persist - documents persisted to inbox"
git push
```

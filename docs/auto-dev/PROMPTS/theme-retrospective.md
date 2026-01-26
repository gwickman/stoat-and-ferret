# Theme Retrospective Prompt

## Context

You are creating a retrospective for a completed theme.

**Version:** {{version}}
**Theme:** {{theme}}
**Theme Path:** {{theme_path}}

## Input Documents

Review these before writing the retrospective:

1. **Theme Definition:** `{{theme_path}}/theme.md`
2. **Progress:** `{{theme_path}}/progress.md` or `progress.json`
3. **Feature Completion Reports:** `{{theme_path}}/*/completion-report.md`
4. **Feature Quality Gaps:** `{{theme_path}}/*/quality-gaps.md`

## Process Document

Follow: `docs/auto-dev/PROCESS/generic/06.1-THEME-RETROSPECTIVE.md`

## Retrospective Structure

Create `{{theme_path}}/retrospective.md` with:

1. **Theme Summary** - What the theme accomplished
2. **Feature Results** - Table of features with outcomes
3. **Key Learnings** - Patterns discovered, what worked
4. **Technical Debt** - Consolidated from feature quality-gaps.md
5. **Recommendations** - For future similar themes

## Completion Criteria

- [ ] retrospective.md created in theme directory
- [ ] All features' outcomes summarized
- [ ] Learnings extracted and consolidated
- [ ] Tech debt documented for backlog consideration

## Output

Single file: `{{theme_path}}/retrospective.md`

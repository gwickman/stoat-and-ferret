Investigate whether the recommendation "Track Descoped Items as Backlog During Design" is addressing a current process gap or a historical one that has already been fixed.

## Context

The RCA synthesis recommended adding instructions to the auto-dev design script to track descoped items as backlog. But there may already be strong rules in the current auto-dev-mcp design process that PREVENT backlog items or acceptance criteria from being descoped during design. If so, adding "track descoped items" language could inadvertently normalize descoping when the process is supposed to prevent it entirely.

## Your Task

### 1. Examine the current design scripts for anti-descoping rules

Read the full design prompt chain thoroughly:
- docs/auto-dev/PROMPTS/design_version_prompt/ — read ALL task prompts, especially those covering requirements writing, backlog analysis, critical thinking, and document drafts
- docs/auto-dev/PROMPTS/design_theme_prompt/ — if it exists, read all task prompts
- Look for ANY language about: preventing descoping, mandatory acceptance criteria, backlog item commitment, scope protection, or similar

Read the CLAUDE.md / AGENTS.md for any rules about descoping.

### 2. Trace when the descoping actually happened

For each of the three issues the RCAs attributed to "descoped without backlog":
- **Cancellation** (rca-no-cancellation says descoped at v004 requirements.md:32)
- **Progress reporting** (rca-no-progress says stubbed without wiring)  
- **Clip management** (rca-clip-management says implicit deferral via phasing)

Find the EXACT version design documents and requirements where the descoping occurred. Read them. Determine:
- Was the descoped item actually a committed backlog item with acceptance criteria, or was it never in the backlog?
- If it was in the backlog, was the AC changed/weakened during design?
- What version was this? (v003? v004? v005?)

### 3. Check whether later versions had the same problem

Specifically examine v007, v008, and v009 designs:
- Read their VERSION_DESIGN.md, THEME_INDEX.md, and requirements.md files
- Were any backlog items descoped or had acceptance criteria weakened?
- Were any "Out of Scope" sections present that dropped design-doc features without tracking?

### 4. Check when anti-descoping rules were introduced

Look at git history, learnings, or process changes that might indicate when stronger anti-descoping rules were added to the design scripts. Check:
- Learnings that mention descoping, scope protection, commitment, or mandatory items
- Any auto-dev-mcp changelog or version history
- The design script files themselves for any comments or metadata indicating when they were last updated

### 5. Determine: Is recommendation 1A solving a current problem or a historical one?

Based on all evidence, answer:
- Do the current design scripts already prevent the class of failure that caused these three RCA issues?
- If yes, would adding "track descoped items" language weaken the existing anti-descoping stance?
- What is the RIGHT recommendation given the current state of the process?

Do NOT create any items or make any changes. Analysis only.

## Output Requirements

Create findings in comms/outbox/exploration/descoping-investigation/:

### README.md (required)
Clear answer: is recommendation 1A addressing a current gap or a historical one? What should actually be done?

### design-script-analysis.md
What the current design scripts say about descoping, with exact quotes and file paths.

### descoping-timeline.md
When each descoping event happened, what version it was, and whether the current process would have prevented it.

### revised-recommendation.md
What the recommendation should actually be, given the evidence. This might be "1A as stated", "modified 1A", "not needed", or something different entirely.

## Guidelines
- Keep each document under 250 lines
- Quote exact text from design scripts — don't paraphrase rules about descoping
- Be thorough with the version-by-version examination of v007-v009
- Distinguish between "backlog item descoped" and "design-doc feature never made it to backlog"

## When Complete
git add comms/outbox/exploration/descoping-investigation/
git commit -m "exploration: descoping-investigation complete"

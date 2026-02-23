You have access to six completed RCA explorations. Your job is to critically review their findings, challenge their conclusions where warranted, and produce an actionable remediation plan that correctly identifies WHERE each fix belongs.

## Phase 1: Read All RCA Results

Read every document from these explorations (use read_document on their outbox paths):
- comms/outbox/exploration/rca-ffprobe-blocking/
- comms/outbox/exploration/rca-no-progress/
- comms/outbox/exploration/rca-no-cancellation/
- comms/outbox/exploration/rca-clip-management/
- comms/outbox/exploration/rca-no-browse-button/
- comms/outbox/exploration/rca-no-env-example/

Read ALL files in each (README.md, evidence-trail.md, recommendations.md).

## Phase 2: Understand the Auto-Dev Process

Before you can determine where fixes belong, you need to understand the process machinery. Read these to understand what IMPACT_ASSESSMENT.md and VERSION_CLOSURE.md are, and how the design and retrospective processes work:

- Look in docs/auto-dev/PROMPTS/ for the design and retrospective prompt scripts. Read the task prompts to understand what each step does.
- Look for templates or references to IMPACT_ASSESSMENT.md and VERSION_CLOSURE.md — understand their purpose and when they're generated.
- Read the current CLAUDE.md or AGENTS.md if they exist.
- Check docs/auto-dev/ for any process documentation.

Also review the auto-dev-mcp project's process by looking at what learnings and product requests already exist that might overlap with the RCA recommendations.

## Phase 3: Critical Review

For each RCA's findings and recommendations, ask:
- Is the evidence actually sufficient for the conclusion, or is the RCA speculating?
- Are the recommended fixes proportionate to the problem, or over-engineered?
- Would the recommended fix actually have prevented the issue, or is it theatre?
- Are there simpler alternatives the RCA didn't consider?
- Did any RCA contradict another, or make inconsistent assumptions?
- Are any recommendations solving a problem that only happened once and is unlikely to recur?

Be honest. If a recommendation is good, say so. If it's weak or wouldn't actually help, say that too.

## Phase 4: Remediation Plan

For each recommendation that survives your critical review, determine where it belongs:

1. **auto-dev-mcp process change** — A general improvement to the orchestration system that would benefit ALL projects. This would become a product request (PR) or backlog item on auto-dev-mcp.
2. **stoat-and-ferret IMPACT_ASSESSMENT.md** — Project-specific configuration that shapes how auto-dev runs against this particular project.
3. **stoat-and-ferret VERSION_CLOSURE.md** — Project-specific closure criteria.
4. **stoat-and-ferret code/config** — A concrete code change to the project itself (like the lint rule or a test).
5. **stoat-and-ferret backlog** — A backlog item for future version work.
6. **Not worth doing** — Explain why.

Some fixes may need a bit of both (e.g. a general process improvement in auto-dev-mcp AND a project-specific configuration). Be specific about the split.

Do NOT create any backlog items, product requests, learnings, or make any changes. Analysis only.

## Output Requirements

Create findings in comms/outbox/exploration/rca-synthesis/:

### README.md (required)
Executive summary: which RCA findings hold up, which don't, and the overall remediation strategy.

### critical-review.md
Issue-by-issue critique of each RCA's evidence quality, conclusions, and recommendations. Be direct about what's strong and what's weak.

### remediation-plan.md
The actionable plan. For each surviving recommendation: what it is, where it belongs, why there, and what the concrete next step would be (without actually doing it). Group by target (auto-dev-mcp, IMPACT_ASSESSMENT, VERSION_CLOSURE, stoat-and-ferret code, not worth doing).

### process-analysis.md
Your understanding of how IMPACT_ASSESSMENT.md, VERSION_CLOSURE.md, and the design/retro scripts work, and how the recommendations map to them.

## Guidelines
- Keep each document under 300 lines (this is a larger synthesis)
- Cite specific evidence from the RCAs and from the process docs you read
- If you disagree with an RCA finding, explain why with evidence
- Be concrete — "add a check" is not actionable; "add X check to Y step in Z file" is

## When Complete
git add comms/outbox/exploration/rca-synthesis/
git commit -m "exploration: rca-synthesis complete"

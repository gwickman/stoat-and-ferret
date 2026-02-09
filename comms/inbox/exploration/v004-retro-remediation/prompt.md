Read AGENTS.md first and follow all instructions there.

## Objective
Execute all remediation actions from the Stage 1 proposals document for stoat-and-ferret v004 retrospective.

## Input
Read: comms/outbox/versions/retrospective/v004/007-proposals/proposals.md

## Tasks
The proposals document identifies 1 immediate fix action:

1. **Stale branch cleanup**: Delete local branch `at/pyo3-bindings-clean` and its remote tracking branch `origin/feat/pyo3-bindings-clean`.
   - Run: `git branch -d at/pyo3-bindings-clean`
   - Run: `git push origin --delete feat/pyo3-bindings-clean`

For each action:
1. Read the action description
2. Execute the action exactly as specified
3. Document the result

## Output Requirements
Save outputs to comms/outbox/exploration/v004-retro-remediation/:

### README.md (required)
First paragraph: Summary of remediation actions executed.
Then: Table of each action, its status, and any notes.

Do NOT commit — the calling prompt handles commits. Results folder: v004-retro-remediation.
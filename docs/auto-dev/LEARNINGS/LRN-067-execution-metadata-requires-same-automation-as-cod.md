## Context

During version execution, multiple metadata artifacts track progress: state files recording feature completion counts, progress tracking documents, and quality gap records. When these require manual updates, they consistently fall out of sync with actual progress.

## Learning

Execution metadata (progress files, state files, quality gap records) drifts when it depends on manual updates. If an artifact is referenced by the process definition but requires a manual step to create or update, it will be skipped under time pressure. Either automate the metadata updates (triggered by PR merge or feature completion) or remove the metadata requirement from the process definition. The gap between "process says do X" and "X requires a manual step" is where drift originates.

## Evidence

Two consecutive themes in the same version both skipped progress.md creation despite the theme definition referencing it. A state file tracking feature completion counts remained at zero despite all features being complete and merged. Neither feature in the second theme produced quality-gaps.md files. The retrospectives for both themes independently flagged the same gaps, confirming it was systematic rather than accidental.

## Application

1. Audit process artifacts: identify which ones require manual creation/updates
2. For each manual artifact, decide: automate it, or remove it from the process
3. If automation isn't feasible, add the step to a checklist that gates the next action (e.g., "update state file before starting next feature")
4. If an artifact is consistently skipped across multiple iterations, it's a signal to either automate or drop the requirement
5. Distinguish between "nice to have" metadata and "required for next step" metadata — only enforce the latter
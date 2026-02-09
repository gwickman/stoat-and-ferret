## Context

When addressing code quality issues (coverage exclusions, lint suppressions, tech debt), there's a temptation to make blanket changes or remove all suppressions at once.

## Learning

Audit first, then fix only what needs fixing. Catalogue all instances, evaluate each for justification, and only remediate the unjustified ones. This prevents unnecessary churn and ensures that legitimate suppressions are preserved and documented.

## Evidence

- v004 Theme 05 Feature 003 (coverage-gap-fixes): Audited 21 exclusions (`pragma: no cover`, `type: ignore`, `noqa`). Only 1 of 21 needed remediation (the `pragma: no cover` on ImportError fallback). The other 20 were properly justified.
- Added group-level justification comments to document why existing suppressions are correct.
- The retrospective explicitly called this out as a discovered pattern.

## Application

- Before removing lint/coverage suppressions, catalogue them all first.
- Evaluate each suppression for justification.
- Add documentation to justified suppressions if they lack explanation.
- Only remediate unjustified suppressions — don't create unnecessary churn.
- This approach applies to any codebase cleanup: tech debt, deprecated API usage, security warnings.
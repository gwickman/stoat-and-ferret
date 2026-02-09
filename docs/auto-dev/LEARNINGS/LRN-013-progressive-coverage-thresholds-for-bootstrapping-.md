## Context

When adding coverage enforcement to a codebase for the first time (especially for a secondary language like Rust in a polyglot project), setting the target threshold immediately may cause false CI failures if the actual baseline is unknown.

## Learning

Set an initial progressive threshold below the target, then ratchet it up once CI confirms the actual baseline. Document both the current threshold and the target clearly. This avoids blocking development with false failures while still establishing the enforcement mechanism.

## Evidence

- v004 Theme 05 Feature 002 (rust-coverage): Rust coverage threshold set to 75% initially with documented target of 90%. Investigation estimated baseline at 75-90% but exact value needed CI confirmation.
- The retrospective explicitly noted this as a follow-up action: ratchet to 90% after 2-3 CI runs confirm the baseline.

## Application

- When adding coverage enforcement to a new codebase or language, start with a conservative threshold.
- Document the current threshold, target threshold, and the plan to ratchet up.
- Ratchet thresholds upward after confirming the baseline over several CI runs.
- This applies to any CI-enforced metric (coverage, lint score, performance budget).
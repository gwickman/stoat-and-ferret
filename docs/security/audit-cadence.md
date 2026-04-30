# Security Audit Cadence

## Purpose

Formalize the recurring security audit schedule and triggers for stoat-and-ferret.

## Cadence Triggers

The security audit is triggered by:

1. **Quarterly Review** — Every three months (on a schedule TBD per team calendar)
2. **Python Major Version Upgrade** — When upgrading Python to a new major release (e.g., 3.13, 3.14)
3. **FFmpeg Major Version Upgrade** — When upgrading FFmpeg to a new major release (e.g., 7.x, 8.x)
4. **PyO3 Major Version Upgrade** — When upgrading PyO3 to a new major release (e.g., 0.22+)

## Audit Scope

Each audit covers:

- **Endpoint Inventory** — Verify all HTTP/WebSocket endpoints are documented and checked against OpenAPI spec
- **Dependency Audit** — Review all direct and transitive dependencies for CVEs (via pip-audit or safety)
- **Configuration Drift** — Verify STOAT_* environment variables are documented per dual-doc rule (docs/setup/04_configuration.md + docs/manual/configuration-reference.md)
- **Allowlist Validation** — Verify security allowlists (KNOWN_UNDOCUMENTED_SETTINGS_VARS in tests/security/test_audit.py) are at zero or explicitly justified
- **FFmpeg Sanitizer Review** — Inspect FFmpeg filter generation code for injection vulnerabilities; verify regex patterns are correct

## Audit Deliverables

Audit findings are filed as follows:

- **P0/P1 (Critical/High):** File as blocking backlog items (BL-XXX) that must be resolved before the next release
- **P2/P3 (Medium/Low):** Annotate in the audit doc (docs/security/review-phase6.md or successor) with rationale for deferral

Findings must be filed using the BL-filing pattern established in v043:

- Clear title and impact statement
- Link to the audit trigger and date
- Concrete acceptance criteria
- Estimated effort and priority

## Review Schedule

- **First Quarterly Audit:** [Team to schedule; suggested: 2026-07-30 (Q3)]
- **Subsequent Audits:** Every 90 days unless triggered early by dependency upgrade
- **Maintenance Trigger:** Document review and update in FRAMEWORK_CONTEXT.md if audit scope expands (e.g., new FFmpeg features, new STOAT_* variables)

## References

- v043 security audit retro (v043/01-security-audit) — Initial cadence and findings
- AGENTS.md — Command guidelines and recurring processes
- FRAMEWORK_CONTEXT.md — Framework decisions and constraints

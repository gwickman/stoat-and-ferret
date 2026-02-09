## Context

When adding restrictive configuration settings to an existing system (e.g., allowed paths, permitted origins, enabled features), choosing the right default behavior is critical for backwards compatibility.

## Learning

Use the convention "empty list = unrestricted" for allowlist-style configuration settings. This preserves backwards compatibility for existing deployments while letting production environments explicitly lock down access. Document this convention clearly and recommend restrictive configuration for production.

## Evidence

- v004 Theme 04 Feature 001 (security-audit): `ALLOWED_SCAN_ROOTS = []` defaults to "all paths allowed", avoiding breakage for existing users. Production deployments are advised to configure specific roots.
- The retrospective noted this as a reusable pattern for future restrictive settings.

## Application

- For any new allowlist setting, default to empty = unrestricted.
- Document the security implication of the default clearly.
- Provide recommended production values in deployment documentation.
- Consider logging a warning at startup when running with the unrestricted default in non-development environments.
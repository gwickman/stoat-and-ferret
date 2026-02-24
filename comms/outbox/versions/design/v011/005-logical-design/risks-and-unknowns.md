# Risks and Unknowns: v011

## Risk: BL-075 `label` field mismatch between AC and schema

- **Severity:** medium
- **Description:** BL-075 AC3 references a "label" property for clip editing, but no `label` field exists in the backend's `ClipCreate` or `ClipUpdate` Pydantic schemas. The form cannot display a field the backend doesn't support.
- **Investigation needed:** Confirm whether `label` was intended as a future enhancement or an AC error. Check if any other clip data model references labels.
- **Current assumption:** (UNVERIFIED) AC3's mention of "label" is an error inherited from an earlier design iteration. The logical design drops `label` from the form and uses the backend schema as authoritative. If label support is desired, it requires a backend schema migration first — out of scope for v011.

## Risk: Directory listing security — path traversal

- **Severity:** high
- **Description:** The new `GET /api/v1/filesystem/directories` endpoint exposes server filesystem contents. If `allowed_scan_roots` validation has gaps or path traversal (`../`) bypasses the check, an attacker could enumerate arbitrary directories.
- **Investigation needed:** Review the existing `allowed_scan_roots` validation in `videos.py:194-200` for path traversal resistance. Ensure the new endpoint uses the same validation with `os.path.realpath()` to resolve symlinks and `../` before checking against allowed roots.
- **Current assumption:** The existing scan endpoint's security pattern is adequate when applied consistently. The new endpoint must use `os.path.realpath()` normalization before any `allowed_scan_roots` comparison.

## Risk: BL-075 scope creep — source video selection UX

- **Severity:** medium
- **Description:** The Add Clip form requires selecting a `source_video_id`. The current library page lists videos, but there's no "pick a video" widget designed for embedding in a modal form. This could expand the feature scope into building a video picker component.
- **Investigation needed:** Check if an existing video list/dropdown pattern exists that can be reused. Determine if a simple `<select>` dropdown of library videos is sufficient or if a richer picker is needed.
- **Current assumption:** (UNVERIFIED) A simple dropdown populated from `GET /api/v1/videos` is sufficient for v011. If the library is very large, pagination or search may be needed — defer to a future version.

## Risk: BL-070 UX when `allowed_scan_roots` is empty

- **Severity:** medium
- **Description:** The default value for `allowed_scan_roots` is an empty list (`[]`). If empty means "no restrictions," the directory browser shows the entire filesystem. If empty means "nothing allowed," the browse feature is non-functional until configured.
- **Investigation needed:** Check how the existing scan endpoint interprets an empty `allowed_scan_roots` — does it allow all paths or deny all?
- **Current assumption:** (UNVERIFIED) Empty `allowed_scan_roots` likely means "allow all" based on typical security patterns where an empty allowlist disables the restriction. The directory browser should handle both interpretations correctly.

## Risk: Clip CRUD refresh race condition

- **Severity:** low
- **Description:** After a clip mutation (add/edit/delete), the clip list needs to refresh. If the user rapidly performs multiple operations, concurrent fetches could result in stale list state.
- **Investigation needed:** Check how existing Zustand stores handle rapid sequential mutations (e.g., effect stack operations).
- **Current assumption:** The established Zustand async pattern with `isLoading` guards is sufficient. Rapid mutations are an edge case unlikely in normal GUI interaction. The store's `set()` calls are synchronous state updates, so the last fetch always wins.

## Risk: IMPACT_ASSESSMENT.md format not machine-parseable

- **Severity:** low
- **Description:** BL-076 creates a file consumed by auto-dev Task 003 (a Claude Code agent). If the format doesn't match what the agent expects, the checks won't execute correctly. There's no formal schema — the agent reads markdown and interprets it.
- **Investigation needed:** Review `docs/auto-dev/PROMPTS/design_version_prompt/task_prompts/003-impact-assessment.md` for any format expectations beyond "structured check sections."
- **Current assumption:** The recommended format (check name heading + what/why/example subsections) is sufficient for agent consumption. The auto-dev framework gracefully handles the file's absence, so a format issue degrades to "checks not executed" rather than a hard failure.

## Risk: Theme 2 feature 003 dependency on feature 001

- **Severity:** low
- **Description:** The impact assessment's "settings documentation check" verifies that .env.example is updated when Settings fields change. If 003-impact-assessment is implemented before 001-env-example, the concrete example in the check would reference a file that doesn't exist yet.
- **Investigation needed:** None — this is a known ordering constraint.
- **Current assumption:** The execution order already accounts for this: 001-env-example precedes 003-impact-assessment within Theme 2. This is documented in PLAN.md and the logical design's execution order.

Investigate the clip management capabilities in the GUI to understand what's currently implemented and what's missing.

Reported issue: There appears to be no way to manage clips within a project - specifically no Add, Update, or Remove buttons in the GUI for clip management.

## Investigation Areas

1. **Current GUI clip components**: What clip-related UI components exist? Find all React/Svelte components related to clips. What can users currently do with clips in the GUI?
2. **Backend clip CRUD endpoints**: What API endpoints exist for clip management (create, read, update, delete)? Are they fully implemented?
3. **Gap analysis**: Compare what the backend supports vs what the GUI exposes. Are there backend endpoints that the GUI simply doesn't call yet?
4. **Design intent**: Check design documents (docs/design/) for what clip management was specified to include. Was this an intentional omission for a later version, or was it supposed to be implemented?
5. **Current clip display**: How are clips currently displayed? Is there a clip list/panel? What information is shown?

## Output Requirements

Create findings in comms/outbox/exploration/clip-management-gaps/:

### README.md (required)
First paragraph: Summary of what clip management exists vs what's missing.
Then: Overview linking to detailed findings.

### gui-clip-components.md
Inventory of existing clip-related GUI components, what they do, and what's missing.

### api-clip-endpoints.md
Inventory of clip CRUD endpoints - which exist, which are missing, which are implemented but not wired to the GUI.

### gap-analysis.md
Comparison of design specs vs current implementation, with recommendations for what needs to be built.

## Guidelines
- Keep each document under 200 lines
- Include file paths for all components and endpoints found
- Reference design document sections where relevant
- Clearly distinguish between "not implemented" and "implemented but not exposed in GUI"

## When Complete
git add comms/outbox/exploration/clip-management-gaps/
git commit -m "exploration: clip-management-gaps complete"

# Recommendations: Preventing UX Specification Gaps

## Problem Pattern

Standard UX patterns (file pickers, confirmation dialogs, keyboard shortcuts, drag-and-drop) can be omitted from specs because they seem "obvious" to a human user but are invisible to an AI agent that builds exactly what is specified. The design doc wireframe showed a `[Scan Directory]` button but never detailed the modal's interior, leaving the implementation plan to fill in the gap — which it did with the simplest interpretation (text input).

## Already Addressed

- **BL-070** exists as an open P2 to add the browse button
- **BL-073** and **BL-074** address related scan UX gaps (progress, cancellation)
- The retrospective process caught several technical debt items but not this UX gap

## Recommended Changes

### 1. Design Documents: Add Modal/Dialog Wireframes

**Gap:** `08-gui-architecture.md` includes wireframes for pages (Dashboard, Library, Projects) but not for modals (Scan, New Project). The scan modal's interior was left unspecified.

**Recommendation:** For any design doc that references a modal or dialog, include an ASCII wireframe showing its contents, input fields, and interactive elements. The scan modal should have looked like:

```
Scan Directory
Directory Path: [/path/to/videos     ] [Browse]
[x] Scan subdirectories
[Cancel]                        [Start Scan]
```

### 2. Backlog Items: UX-Specific Acceptance Criteria

**Gap:** BL-033 AC #4 says "Scan modal triggers directory scan and shows progress feedback" — this describes the workflow outcome but not the interaction pattern.

**Recommendation:** When a backlog item involves user input, acceptance criteria should specify the input mechanism, not just the outcome. For path selection: "User can enter a path manually OR use a browse dialog to select a directory."

### 3. Implementation Plans: Reference Standard UX Patterns

**Gap:** The implementation plan specified "directory path input, submit button" without questioning whether a text-only input is sufficient for path selection.

**Recommendation:** Implementation plans for UI features should include a "UX Patterns" section that explicitly lists which standard patterns apply (file picker, autocomplete, drag-and-drop, keyboard shortcuts) and which are intentionally excluded with rationale.

### 4. Version Design: UX Checklist for GUI Themes

**Gap:** The version design process focuses on technical architecture and feature decomposition but doesn't include a UX review step.

**Recommendation:** For versions containing GUI themes, the design phase should include a brief UX checklist:
- Does every user input have an appropriate input mechanism?
- Are file/folder paths selected via browser dialogs (not just text entry)?
- Do destructive actions have confirmation dialogs?
- Are long-running operations cancellable?
- Is progress feedback real (not placeholder)?

### 5. Retrospectives: UX Gap Detection

**Gap:** The v005 Theme 03 retrospective listed technical debt (WebSocket duplication, client-side sorting) but did not flag the missing browse button as a UX gap.

**Recommendation:** Retrospective templates should include a "UX completeness" check: compare delivered interaction patterns against common desktop/web conventions for the feature type. For file management features, a folder browser is a baseline expectation.

## Priority

These are process improvements, not code changes. The most impactful change is #1 (modal wireframes in design docs), as it would have prevented this specific gap and similar ones for any future modal-based features.

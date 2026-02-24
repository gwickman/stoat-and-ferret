# Backlog Details: v011

## BL-075 — Add clip management controls (Add/Edit/Delete) to project GUI

- **Priority:** P1 | **Size:** L | **Tags:** gui, clips, crud, wiring-gap, user-feedback
- **Description:**
  > The GUI currently displays clips in a read-only table on the ProjectDetails page but provides no controls to add, edit, or remove clips. The backend API has full CRUD support for clips (POST, PATCH, DELETE on `/api/v1/projects/{id}/clips`) — all implemented and integration-tested — but the frontend never calls the write endpoints. Users must use the API directly to manage clips, which defeats the purpose of having a GUI. This was deferred from v005 (Phase 1 delivered read-only display) but is now a significant gap in the user workflow.
- **Acceptance Criteria:**
  1. ProjectDetails page includes an Add Clip button that opens a form to create a new clip (selecting from library videos, setting in/out points)
  2. Each clip row in the project clips table has Edit and Delete action buttons
  3. Edit button opens an inline or modal form pre-populated with current clip properties (in/out points, label)
  4. Delete button prompts for confirmation then removes the clip via DELETE endpoint
  5. Add/Edit forms validate input and display errors from the backend (e.g. invalid time ranges)
  6. Clip list refreshes after any add/update/delete operation
- **Use Case:** When building a project in the GUI, users need to add video clips from their library, adjust clip boundaries, and remove clips without switching to API calls or external tools.
- **Complexity Assessment:** High. Touches multiple layers: React components (forms, modals, table actions), API client (3 new endpoint calls), state management (clip list refresh), and error handling (backend validation display). Deferred since v005 indicates non-trivial scope.

---

## BL-076 — Create IMPACT_ASSESSMENT.md with project-specific design checks

- **Priority:** P1 | **Size:** L | **Tags:** process, auto-dev, impact-assessment, rca
- **Description:**
  > stoat-and-ferret has no IMPACT_ASSESSMENT.md, so the auto-dev design phase runs no project-specific checks. RCA analysis identified four recurring issue patterns that project-specific impact assessment checks would catch at design time: (1) blocking subprocess calls in async context (caused the ffprobe event-loop freeze), (2) Settings fields added without .env.example updates (9 versions without .env.example), (3) features consuming prior-version backends without verifying they work (progress bar assumed v004 progress worked — it didn't), (4) GUI features with text-only input where richer mechanisms are standard (scan directory path with no browse button).
- **Acceptance Criteria:**
  1. IMPACT_ASSESSMENT.md exists at docs/auto-dev/IMPACT_ASSESSMENT.md
  2. Contains async safety check: flag features that introduce or modify subprocess.run/call/check_output or time.sleep inside files containing async def
  3. Contains settings documentation check: if a version adds or modifies Settings fields, verify .env.example is updated
  4. Contains cross-version wiring assumptions check: when features depend on behavior from prior versions, list assumptions explicitly
  5. Contains GUI input mechanism check: for GUI features accepting user input, verify appropriate input mechanisms are specified
  6. Each check section includes what to look for, why it matters, and a concrete example from project history
- **Notes:** IMPACT_ASSESSMENT.md is project-specific, not an auto-dev process artifact. Treat as project code.
- **Use Case:** During version design, the auto-dev impact assessment step reads this file and executes project-specific checks, catching recurring issue patterns before they reach implementation.
- **Complexity Assessment:** Medium-high. Primarily documentation but requires careful articulation of each check pattern with concrete project-history examples. No code changes, but content must be precise enough for automated consumption.

---

## BL-070 — Add Browse button for scan directory path selection

- **Priority:** P2 | **Size:** M | **Tags:** gui, ux, library, user-feedback
- **Description:**
  > Currently the Scan Directory feature requires users to manually type or paste a directory path. There is no file/folder browser dialog to help users navigate to and select the target directory. This creates friction — users must know the exact path and type it correctly, which is error-prone and a poor UX pattern for desktop-style file selection.
- **Acceptance Criteria:**
  1. Scan Directory UI includes a Browse button next to the path input field
  2. Clicking Browse opens a folder selection dialog that allows navigating the filesystem
  3. Selecting a folder in the dialog populates the path input field with the chosen path
  4. Users can still manually type a path as an alternative to browsing
- **Use Case:** When a user wants to scan a media directory, they need to navigate to it visually rather than remembering and typing the full path, especially on systems with deep directory hierarchies.
- **Complexity Assessment:** Medium. Requires a browser-compatible folder picker (likely the File System Access API or a backend-assisted directory listing endpoint). The React component work is straightforward, but the folder browsing mechanism may need a backend API since browser-native folder pickers have limited support.

---

## BL-071 — Add .env.example file for environment configuration template

- **Priority:** P2 | **Size:** M | **Tags:** devex, documentation, onboarding, user-feedback
- **Description:**
  > The project has no .env.example file to guide new developers or users through environment configuration. Anyone setting up the project must reverse-engineer which environment variables are needed by reading source code. This is a common onboarding friction point — without a template, users may miss required configuration and encounter confusing startup failures.
- **Acceptance Criteria:**
  1. A .env.example file exists in the project root with all required/optional environment variables documented
  2. Each variable includes a comment explaining its purpose and acceptable values
  3. The file contains sensible defaults or placeholder values (not real secrets)
  4. README or setup documentation references .env.example as part of the getting-started workflow
- **Use Case:** When a new developer or user clones the repo, they need a clear reference for what environment variables to configure before the application will start correctly.
- **Complexity Assessment:** Low-medium. Requires auditing the Settings class and any env var references in the codebase to enumerate all variables. The file itself is simple but completeness is critical — missing a variable defeats the purpose.

---

## BL-019 — Add Windows bash /dev/null guidance to AGENTS.md and nul to .gitignore

- **Priority:** P3 | **Size:** M | **Tags:** windows, agents-md, gitignore
- **Description:**
  > Add Windows bash null redirect guidance to AGENTS.md. In bash contexts on Windows (Git Bash / MSYS2), /dev/null is correctly translated to the Windows null device. However, using bare 'nul' — the native Windows convention — creates a literal file named 'nul' in the working directory because MSYS interprets it as a filename rather than a device. This has already caused git noise in the project (nul was added to .gitignore as a workaround). AGENTS.md should document this pitfall so developers and AI agents avoid it. The .gitignore half is already done; this item covers only the AGENTS.md documentation.
- **Acceptance Criteria:**
  1. AGENTS.md contains a 'Windows (Git Bash)' section under Commands or a new top-level section
  2. Section documents that /dev/null is correct for output redirection in Git Bash on Windows
  3. Section warns against using bare 'nul' which creates a literal file in MSYS/Git Bash
  4. Section includes correct and incorrect usage examples
- **Notes:** The .gitignore half is already done (nul added to .gitignore). Remaining scope: add Windows bash /dev/null redirect guidance to AGENTS.md.
- **Use Case (formulaic — noted in assessment):** When a developer working on Windows in Git Bash needs to redirect command output to null, they may instinctively use 'nul'. Clear guidance prevents the literal file creation issue.
- **Complexity Assessment:** Low. Single documentation addition to an existing file. No code changes required. Scope is well-defined and partially complete.

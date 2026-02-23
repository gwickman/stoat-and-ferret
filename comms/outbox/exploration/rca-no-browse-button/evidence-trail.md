# Evidence Trail: Scan Directory Browse Button Gap

## Chronological Trace

### 1. Design Phase (pre-v005)

**`docs/design/08-gui-architecture.md`**
- Line 164: Library Browser wireframe shows `[Scan Directory]` button in header
- Lines 187-193: Features list says "Scan directory button with progress modal"
- Lines 539-544: Phase 1 milestone M1.11 says "Create scan directory modal with progress"
- **No wireframe** of the scan modal interior is provided
- **No mention** of browse/file-picker/folder-selection anywhere in the document

**`docs/design/03-prototype-design.md`**
- Lines 49-51: GUI Must Have table lists "Library Browser" with "Video grid with search and thumbnails"
- Line 587-600: Scan Directory API spec shows `POST /videos/scan` with `{"path": "/home/user/videos"}`
- **No mention** of how users select the path in the GUI

**`docs/design/01-roadmap.md`**
- Lines 140-141: Milestone 1.11 says "Create scan directory modal with progress indicator"
- **No UX detail** on path selection mechanism

### 2. Backlog Phase

**BL-033** (created 2026-02-08, completed 2026-02-09)
- Title: "Build library browser with video grid, search, and scan UI"
- AC #4: "Scan modal triggers directory scan and shows progress feedback"
- Use case: "...click the Scan button to add videos from a new directory. The scan modal shows progress..."
- **No acceptance criterion** mentions browse, file picker, or folder selection
- **No mention** in description or notes of how path entry works

### 3. Version Design Phase (v005)

**`docs/versions/v005/VERSION_DESIGN.md`**
- Theme 03 goal: "Build the four main GUI panels"
- No additional UX detail on scan modal behavior

**`docs/versions/v005/THEME_INDEX.md`**
- Feature 003-library-browser listed with no description detail

### 4. Implementation Plan Phase

**`comms/inbox/.../003-library-browser/requirements.md`**
- FR-004: "Scan modal triggers directory scan via the jobs API and shows progress feedback"
- AC: "Scan modal allows entering a directory path and triggers a scan job; progress is shown"
- **Explicitly says "entering a directory path"** — implies manual text entry, not browsing

**`comms/inbox/.../003-library-browser/implementation-plan.md`**
- Stage 3, step 1: "Create ScanModal.tsx: directory path input, submit button triggering POST /api/v1/jobs"
- **Explicitly specifies "directory path input"** — a text input field

### 5. Implementation Phase

**`gui/src/components/ScanModal.tsx`** (delivered in v005)
- Line 24: `const [directory, setDirectory] = useState('')`
- Lines 121-131: Plain `<input type="text">` with placeholder "/path/to/videos"
- **No browse button**, no file dialog, no `showDirectoryPicker()` API usage
- **Matches spec exactly**: text input + submit button + progress feedback

### 6. Test Phase

**`gui/src/components/__tests__/ScanModal.test.tsx`**
- Tests text input, submit, API call, completion, and error states
- No test for any browse capability (because none was specified)

**`gui/e2e/scan.spec.ts`**
- Line 19: `page.getByTestId("scan-directory-input").fill("/tmp/test-videos")`
- E2E test fills path via text — no browse interaction tested

### 7. Retrospective Phase

**`docs/versions/v005/03-gui-components_retrospective.md`**
- Lists "Scan modal with progress" as Complete (line 34)
- Does not flag missing browse capability
- Technical debt items focus on WebSocket, sorting, polling — not UX gaps

**`docs/versions/v005/04-e2e-testing_retrospective.md`**
- Scan test described as accepting "any feedback state" (progress/complete/error)
- No mention of browse capability gap

### 8. Post-Delivery (2026-02-23)

**BL-070** created: "Add Browse button for scan directory path selection" (P2, open)
- First recognition in the backlog that a browse capability is needed
- Created same day as this exploration prompt

## Verdict

The browse button was **never specified** at any point in the design-to-delivery pipeline. This is a design omission, not an implementation oversight. The spec chain consistently described "scan modal with progress" without specifying the path selection UX, and the implementation plan explicitly called for a "directory path input" (text field).

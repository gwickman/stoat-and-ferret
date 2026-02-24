# Test Strategy: v011

## Theme 1: 01-scan-and-clip-ux

### Feature 001-browse-directory (BL-070)

#### Unit Tests

**Backend (pytest):**
- Directory listing endpoint: valid path returns subdirectory list
- Directory listing endpoint: invalid/non-existent path returns 404/400
- Directory listing endpoint: path outside `allowed_scan_roots` returns 403
- Directory listing endpoint: path pointing to a file (not directory) returns 400
- Security: path traversal attempts (e.g., `../`) are rejected

**Frontend (Vitest):**
- `DirectoryBrowser.tsx`: renders loading state, directory list, empty state
- `DirectoryBrowser.tsx`: selecting a directory calls the onSelect callback with correct path
- `DirectoryBrowser.tsx`: navigating into a subdirectory triggers new API fetch
- `ScanModal.tsx`: browse button renders and opens DirectoryBrowser
- `ScanModal.tsx`: selecting a directory in browser populates the path input

#### System/Golden Scenarios
- End-to-end: Open ScanModal → click Browse → navigate directories → select → path appears in input → scan succeeds

#### Parity Tests
- New `GET /api/v1/filesystem/directories` endpoint: request/response schema validation

#### Contract Tests
- Directory listing response DTO: round-trip serialization (path strings, directory names)

#### Replay Fixtures
- Not applicable (no complex execution flows)

---

### Feature 002-clip-crud-controls (BL-075)

#### Unit Tests

**Frontend (Vitest):**
- `clipStore.ts`: createClip action calls POST endpoint and updates store state
- `clipStore.ts`: updateClip action calls PATCH endpoint and updates store state
- `clipStore.ts`: deleteClip action calls DELETE endpoint and removes clip from state
- `clipStore.ts`: error handling sets error state on API failure
- `ClipFormModal.tsx`: renders empty form for Add mode
- `ClipFormModal.tsx`: renders pre-populated form for Edit mode
- `ClipFormModal.tsx`: validates required fields before submission
- `ClipFormModal.tsx`: displays backend validation errors (e.g., invalid time ranges)
- `ClipFormModal.tsx`: disabled submit button during submission
- `ProjectDetails.tsx`: renders Add Clip button
- `ProjectDetails.tsx`: renders Edit/Delete buttons per clip row
- `ProjectDetails.tsx`: delete triggers confirmation dialog
- API client: `createClip()`, `updateClip()`, `deleteClip()` functions with mock fetch

#### System/Golden Scenarios
- End-to-end: Add clip → see in table → Edit in_point → see updated → Delete → confirm → clip removed
- Error scenario: Add clip with invalid time range → backend error displayed in form

#### Parity Tests
- Not applicable (using existing backend endpoints — no API changes)

#### Contract Tests
- Not applicable (existing Pydantic models unchanged)

#### Replay Fixtures
- Not applicable (frontend-only changes)

---

## Theme 2: 02-developer-onboarding

### Feature 001-env-example (BL-071)

#### Unit Tests
- Not applicable (configuration file, no executable code)

#### System/Golden Scenarios
- Manual verification: `cp .env.example .env` → application starts with defaults
- Completeness check: all 11 Settings fields present with STOAT_ prefix

#### Parity Tests
- Not applicable

#### Contract Tests
- Not applicable

#### Replay Fixtures
- Not applicable

---

### Feature 002-windows-dev-guidance (BL-019)

#### Unit Tests
- Not applicable (documentation only)

#### System/Golden Scenarios
- Manual verification: AGENTS.md Windows section renders correctly in markdown preview

#### Parity Tests
- Not applicable

#### Contract Tests
- Not applicable

#### Replay Fixtures
- Not applicable

---

### Feature 003-impact-assessment (BL-076)

#### Unit Tests
- Not applicable (documentation/process artifact, no executable code)

#### System/Golden Scenarios
- Structural verification: IMPACT_ASSESSMENT.md has all 4 required check sections
- Format verification: each check section has "What to look for", "Why it matters", and "Concrete example" subsections
- Consumption verification: auto-dev Task 003 can read and process the file format

#### Parity Tests
- Not applicable

#### Contract Tests
- Not applicable

#### Replay Fixtures
- Not applicable

---

## Test Coverage Summary

| Feature | pytest | Vitest | Manual | New Test Files |
|---------|--------|--------|--------|----------------|
| 001-browse-directory | 5 tests | 5 tests | 0 | `tests/api/test_filesystem.py`, `gui/src/components/__tests__/DirectoryBrowser.test.tsx` |
| 002-clip-crud-controls | 0 | 13 tests | 0 | `gui/src/stores/__tests__/clipStore.test.ts`, `gui/src/components/__tests__/ClipFormModal.test.tsx` |
| 001-env-example | 0 | 0 | 2 checks | None |
| 002-windows-dev-guidance | 0 | 0 | 1 check | None |
| 003-impact-assessment | 0 | 0 | 3 checks | None |
| **Total** | **5** | **18** | **6** | **4 new files** |

### Existing Tests Affected

- `gui/src/components/__tests__/ProjectDetails.test.tsx` — update for new Add/Edit/Delete buttons
- `gui/src/components/__tests__/ScanModal.test.tsx` — update for browse button

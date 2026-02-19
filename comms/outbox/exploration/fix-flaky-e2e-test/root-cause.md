# Root Cause Analysis

## The Flaky Assertion

```typescript
// line 31 (original)
await expect(page.getByTestId("create-project-modal")).toBeHidden();
```

## Modal Close Lifecycle

The `CreateProjectModal` component controls visibility via a conditional render:

```tsx
// CreateProjectModal.tsx:121
if (!open) return null
```

The `open` prop is driven by `createModalOpen` in a Zustand store (`useProjectStore`). The modal only sets this to `false` **after** the API call completes:

```tsx
// CreateProjectModal.tsx:104-113
try {
  await createProject({ ... })   // POST /api/v1/projects
  resetForm()
  onCreated()                    // triggers project list refetch
  onClose()                      // -> setCreateModalOpen(false)
} catch (err) {
  setSubmitError(...)            // modal stays OPEN on error
} finally {
  setSubmitting(false)
}
```

## Why It's Flaky

1. **Click "Create"** triggers `handleSubmit` which starts `await createProject(...)`.
2. While the POST is in-flight, the modal stays visible showing "Creating...".
3. The `toBeHidden()` assertion starts its countdown (default 5000ms).
4. **In CI** (GitHub Actions runners), backend response time is variable due to shared infrastructure and cold-start effects.
5. If the POST takes >5s, the assertion times out while the modal is still waiting for the response.

The test is timing-dependent: it races the assertion timeout against the backend's response time. Locally this almost always passes (fast I/O), but CI introduces enough variability to cause intermittent failures.

## Key Observation

The modal doesn't use animations or CSS transitions for show/hide. It uses conditional rendering (`return null`), so once `open` flips to `false`, the DOM element is removed immediately. The entire delay is the API round-trip.

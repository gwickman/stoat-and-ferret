# Fix Details

## File Changed

`gui/e2e/project-creation.spec.ts`

## Before

```typescript
// Submit
await page.getByTestId("btn-create").click();

// Modal closes and project appears in the list
await expect(page.getByTestId("create-project-modal")).toBeHidden();
await expect(page.getByText(projectName)).toBeVisible({ timeout: 5000 });
```

The click fires the POST request, then immediately asserts `toBeHidden()` with a default timeout. If the POST takes too long, the assertion fails.

## After

```typescript
// Submit and wait for the API response before checking modal state.
// The modal only closes after the POST completes; in CI the backend
// can be slow, so the default assertion timeout is not enough.
const created = page.waitForResponse(
  (resp) =>
    resp.url().includes("/api/v1/projects") &&
    resp.request().method() === "POST",
);
await page.getByTestId("btn-create").click();
await created;

// Modal closes and project appears in the list
await expect(page.getByTestId("create-project-modal")).toBeHidden();
await expect(page.getByText(projectName)).toBeVisible({ timeout: 5000 });
```

## How It Works

1. `page.waitForResponse(...)` registers a listener **before** the click, so the response can't be missed.
2. The click triggers the POST.
3. `await created` blocks until the POST response arrives, regardless of how long the backend takes.
4. After the response, `handleSubmit` runs `onClose()` synchronously, which removes the modal from the DOM.
5. `toBeHidden()` now succeeds almost instantly since the element is already gone (or will be within one React render cycle).

## Alternatives Considered

- **Increase timeout on `toBeHidden()`**: Masks the problem; would need an arbitrarily large timeout to be safe.
- **Add `afterEach` to reset Zustand store**: Wouldn't help since the store state isn't the issue (each test gets a fresh page context).
- **Mock the API in E2E**: Would change the nature of the test from end-to-end to partially mocked.

The `waitForResponse` approach is the correct fix because it synchronizes on the actual event that causes the modal to close.

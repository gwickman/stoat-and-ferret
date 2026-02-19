# Fix Details

## Change 1: New Alembic Migration

**File**: `alembic/versions/1e895699ad50_add_transitions_and_effects_json_columns.py`

Adds the two missing nullable TEXT columns that the repository code already
references.

### Upgrade

```python
def upgrade() -> None:
    op.execute("ALTER TABLE projects ADD COLUMN transitions_json TEXT")
    op.execute("ALTER TABLE clips ADD COLUMN effects_json TEXT")
```

### Downgrade

Uses the SQLite table-rebuild pattern (required for SQLite < 3.35.0 which
lacks `DROP COLUMN`):

```python
def downgrade() -> None:
    # Recreate projects without transitions_json
    op.execute("CREATE TABLE projects_backup (...without transitions_json...)")
    op.execute("INSERT INTO projects_backup SELECT ... FROM projects")
    op.execute("DROP TABLE projects")
    op.execute("ALTER TABLE projects_backup RENAME TO projects")
    # Same pattern for clips without effects_json
    ...
```

### Rationale

The `schema.py` file defines the complete table schema including these
columns, and the repository code (both `project_repository.py` and
`clip_repository.py`) references them in INSERT/UPDATE/SELECT statements.
The original migrations that created the `projects` and `clips` tables
simply omitted these columns.

## Change 2: E2E Test Cleanup

**File**: `gui/e2e/project-creation.spec.ts`

### Before

```typescript
// Submit and wait for the API response before checking modal state.
// The modal only closes after the POST completes; in CI the backend
// can be slow, so the default assertion timeout is not enough.
const created = page.waitForResponse(...);
await page.getByTestId("btn-create").click();
await created;

// Modal closes and project appears in the list.
// The modal close depends on React re-render after the POST response;
// in CI the server can be slow, so use an explicit timeout (BL-055).
await expect(page.getByTestId("create-project-modal")).toBeHidden({
  timeout: 10000,
});
await expect(page.getByText(projectName)).toBeVisible({ timeout: 5000 });
```

### After

```typescript
// Submit and wait for the API response before checking modal state.
const created = page.waitForResponse(...);
await page.getByTestId("btn-create").click();
await created;

// Modal closes and project appears in the list.
await expect(page.getByTestId("create-project-modal")).toBeHidden();
await expect(page.getByText(projectName)).toBeVisible();
```

### Rationale

The inflated timeouts and "slow backend" comments were red herrings from
earlier fix attempts that misidentified the problem as a timing issue.
The `waitForResponse` synchronization is still valuable as a best practice,
but the extended timeouts masked the real problem and are no longer needed.

# Implementation Plan: Migration CI Verification

## Step 1: Update CI Workflow
Edit `.github/workflows/ci.yml`, add after "Install dependencies" step:

```yaml
      - name: Verify migrations reversible
        run: |
          uv run alembic -x sqlalchemy.url=sqlite:///:memory: upgrade head
          uv run alembic -x sqlalchemy.url=sqlite:///:memory: downgrade base
          uv run alembic -x sqlalchemy.url=sqlite:///:memory: upgrade head
```

## Step 2: Verify Existing Migrations
Existing migrations confirmed reversible per exploration:
- `c3687b3b7a6a_initial_schema.py` - Has downgrade
- `44c6bfb6188e_add_audit_log.py` - Has downgrade

Source: `comms/outbox/exploration/alembic-verification/current-state.md`

## Verification
- Push to branch, verify CI passes
- Break a migration temporarily, verify CI fails
# Migration CI Verification (BL-015)

## Goal
Add CI step to verify Alembic migrations are fully reversible.

## Requirements

### FR-001: Migration Verification Step
Add step to `.github/workflows/ci.yml` that runs:
```bash
alembic upgrade head
alembic downgrade base
alembic upgrade head
```

### FR-002: In-Memory Database
Use in-memory SQLite for speed:
```bash
alembic -x sqlalchemy.url=sqlite:///:memory: upgrade head
```

### FR-003: Fail on Error
CI must fail if any migration command fails.

## Acceptance Criteria
- [ ] CI workflow includes migration verification step
- [ ] Step runs after "Install dependencies"
- [ ] Uses in-memory SQLite
- [ ] Fails if migration not reversible
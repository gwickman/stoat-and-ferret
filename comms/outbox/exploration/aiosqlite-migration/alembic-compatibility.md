# Alembic + aiosqlite Compatibility

## Overview

Alembic fully supports async database engines, including aiosqlite for SQLite databases. The key is using SQLAlchemy's async engine capabilities with Alembic's `run_sync()` bridge.

## Does Alembic Work with aiosqlite?

**Yes**, with configuration. Alembic's migration operations are inherently synchronous, but SQLAlchemy provides a `run_sync()` method that bridges async connections to sync code.

## Configuration Options

### Option 1: Async-First (Recommended for v003)

Use async migrations from the start, matching the runtime async pattern.

#### Initialize with Async Template

```bash
alembic init -t async migrations
```

This creates an `env.py` configured for async engines.

#### alembic.ini Configuration

```ini
[alembic]
script_location = migrations
sqlalchemy.url = sqlite+aiosqlite:///stoat_ferret.db
```

#### env.py for aiosqlite

```python
"""Alembic migration environment for async SQLite."""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from stoat_ferret.db.models import Base  # If using SQLAlchemy ORM

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata  # Or None for raw SQL migrations


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    Generates SQL script without connecting to database.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """Run migrations using the provided connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create async engine and run migrations."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

### Option 2: Sync Migrations, Async Runtime

Keep Alembic using sync sqlite3, use aiosqlite only at runtime.

#### alembic.ini

```ini
[alembic]
sqlalchemy.url = sqlite:///stoat_ferret.db  # Sync driver
```

#### Standard env.py (no changes needed)

Use default Alembic template.

**Advantages**:
- Simpler configuration
- No async complexity in migrations

**Disadvantages**:
- Two database URL configurations to maintain
- Potential confusion about which driver to use

### Option 3: Programmatic Migrations in FastAPI

Run migrations during application startup using the same async connection.

```python
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import AsyncEngine


async def run_migrations(engine: AsyncEngine) -> None:
    """Run pending migrations programmatically."""
    alembic_cfg = Config("alembic.ini")

    async with engine.connect() as connection:
        await connection.run_sync(
            lambda conn: command.upgrade(alembic_cfg, "head", sql=False)
        )
```

**Note**: This requires careful handling of the Alembic config and connection passing.

## Recommended Pattern for stoat-and-ferret

Given the existing sync schema.py (`create_tables()`), recommend a phased approach:

### Phase 1: Keep Schema Creation Sync

Current `schema.py` uses raw sqlite3. For initial v003:

```python
# In FastAPI startup
import sqlite3

def create_tables_sync(db_path: str) -> None:
    """Create tables using sync connection, then close."""
    conn = sqlite3.connect(db_path)
    create_tables(conn)  # Existing function
    conn.close()
```

Then use aiosqlite for all runtime operations.

### Phase 2: Introduce Alembic (Later)

When schema versioning becomes necessary:

1. Add Alembic with async template
2. Create initial migration from current schema
3. Use `sqlite+aiosqlite:///` URL
4. Run `alembic upgrade head` during deployment

## Migration Script Example

```python
"""Create videos table.

Revision ID: 001
Create Date: 2025-01-28
"""

from alembic import op
import sqlalchemy as sa

revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'videos',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('path', sa.String(1024), nullable=False, unique=True),
        sa.Column('filename', sa.String(256), nullable=False),
        sa.Column('duration_frames', sa.Integer, nullable=False),
        sa.Column('frame_rate_numerator', sa.Integer, nullable=False),
        sa.Column('frame_rate_denominator', sa.Integer, nullable=False),
        sa.Column('width', sa.Integer, nullable=False),
        sa.Column('height', sa.Integer, nullable=False),
        sa.Column('video_codec', sa.String(32)),
        sa.Column('audio_codec', sa.String(32)),
        sa.Column('file_size', sa.Integer, nullable=False),
        sa.Column('thumbnail_path', sa.String(1024)),
        sa.Column('created_at', sa.String(32), nullable=False),
        sa.Column('updated_at', sa.String(32), nullable=False),
    )

    # FTS5 virtual table - use raw SQL
    op.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS videos_fts USING fts5(
            filename, path, content='videos', content_rowid='rowid'
        )
    """)

    # FTS triggers
    op.execute("""
        CREATE TRIGGER videos_ai AFTER INSERT ON videos BEGIN
            INSERT INTO videos_fts(rowid, filename, path)
            VALUES (new.rowid, new.filename, new.path);
        END
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS videos_ai")
    op.execute("DROP TABLE IF EXISTS videos_fts")
    op.drop_table('videos')
```

## Dependencies

```toml
[project.dependencies]
alembic = ">=1.13"
sqlalchemy = ">=2.0"  # Required for async support
aiosqlite = ">=0.19"
```

## Summary

| Scenario | Recommendation |
|----------|----------------|
| v003 initial | Keep sync schema.py, async runtime |
| Schema versioning needed | Add Alembic with async template |
| Production deployment | `alembic upgrade head` in CI/CD |
| Testing | Use in-memory databases, skip migrations |

## References

- [Alembic Cookbook: Running with Async](https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic)
- [SQLAlchemy Async Documentation](https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html)

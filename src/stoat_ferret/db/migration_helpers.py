# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Shared helpers for idempotent schema migrations (BL-657).

Consolidates two patterns that were duplicated across the codebase:

- `schema.py` repeated the same "ADD COLUMN, ignore if it already exists"
  try/except in sixteen `_alter_*` / `_alter_*_async` functions.
- `MigrationService` (api/services/migrations.py) repeated the same
  "already at the target revision, treat as a no-op" comparison in both
  `apply_pending_sync` and `rollback_sync`.
"""

from __future__ import annotations

import sqlite3

import aiosqlite

# SQLite's error text for `ALTER TABLE ... ADD COLUMN` against a column
# that already exists. `_add_columns_idempotent[_async]` swallow only this
# specific error and re-raise anything else.
_DUPLICATE_COLUMN_ERROR = "duplicate column name"


def _classify_db_error(error: sqlite3.OperationalError) -> str:
    """Classify an `OperationalError` raised by an idempotent ADD COLUMN.

    Returns ``"duplicate_column"`` when `error` matches SQLite's
    duplicate-column error text (safe to ignore during an idempotent add),
    else ``"fatal"``.
    """
    if _DUPLICATE_COLUMN_ERROR in str(error):
        return "duplicate_column"
    return "fatal"


def _add_columns_idempotent(
    conn: sqlite3.Connection, table: str, columns: list[tuple[str, str]]
) -> None:
    """Add each (name, type) column to `table`, ignoring duplicate-column errors.

    Args:
        conn: SQLite database connection.
        table: Target table name.
        columns: List of (column_name, column_type_and_constraints) pairs.
    """
    for col, col_type in columns:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError as e:
            if _classify_db_error(e) != "duplicate_column":
                raise


async def _add_columns_idempotent_async(
    db: aiosqlite.Connection, table: str, columns: list[tuple[str, str]]
) -> None:
    """Async equivalent of `_add_columns_idempotent`."""
    for col, col_type in columns:
        try:
            await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError as e:
            if _classify_db_error(e) != "duplicate_column":
                raise


def _migration_safety_check(current_revision: str | None, target_revision: str | None) -> bool:
    """Return True when `current_revision` already matches `target_revision`.

    Used by `MigrationService` to short-circuit `apply_pending_sync` /
    `rollback_sync` as a no-op when the database is already at the
    requested revision.
    """
    return current_revision == target_revision


__all__ = [
    "_DUPLICATE_COLUMN_ERROR",
    "_add_columns_idempotent",
    "_add_columns_idempotent_async",
    "_classify_db_error",
    "_migration_safety_check",
]

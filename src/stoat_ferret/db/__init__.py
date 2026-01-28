"""Database package for stoat-ferret."""

from stoat_ferret.db.async_repository import (
    AsyncInMemoryVideoRepository,
    AsyncSQLiteVideoRepository,
    AsyncVideoRepository,
)
from stoat_ferret.db.audit import AuditLogger
from stoat_ferret.db.models import AuditEntry, Clip, ClipValidationError, Project, Video
from stoat_ferret.db.project_repository import (
    AsyncInMemoryProjectRepository,
    AsyncProjectRepository,
    AsyncSQLiteProjectRepository,
)
from stoat_ferret.db.repository import (
    InMemoryVideoRepository,
    SQLiteVideoRepository,
    VideoRepository,
)
from stoat_ferret.db.schema import create_tables

__all__ = [
    "AuditEntry",
    "AuditLogger",
    "Clip",
    "ClipValidationError",
    "Project",
    "Video",
    "VideoRepository",
    "SQLiteVideoRepository",
    "InMemoryVideoRepository",
    "AsyncVideoRepository",
    "AsyncSQLiteVideoRepository",
    "AsyncInMemoryVideoRepository",
    "AsyncProjectRepository",
    "AsyncSQLiteProjectRepository",
    "AsyncInMemoryProjectRepository",
    "create_tables",
]

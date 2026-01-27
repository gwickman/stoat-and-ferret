"""Database package for stoat-ferret."""

from stoat_ferret.db.audit import AuditLogger
from stoat_ferret.db.models import AuditEntry, Video
from stoat_ferret.db.repository import (
    InMemoryVideoRepository,
    SQLiteVideoRepository,
    VideoRepository,
)
from stoat_ferret.db.schema import create_tables

__all__ = [
    "AuditEntry",
    "AuditLogger",
    "Video",
    "VideoRepository",
    "SQLiteVideoRepository",
    "InMemoryVideoRepository",
    "create_tables",
]

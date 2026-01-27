"""Database package for stoat-ferret."""

from stoat_ferret.db.models import Video
from stoat_ferret.db.repository import (
    InMemoryVideoRepository,
    SQLiteVideoRepository,
    VideoRepository,
)
from stoat_ferret.db.schema import create_tables

__all__ = [
    "Video",
    "VideoRepository",
    "SQLiteVideoRepository",
    "InMemoryVideoRepository",
    "create_tables",
]

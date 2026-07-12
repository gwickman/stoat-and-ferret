# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Stoat and Ferret - AI-driven video editor."""

from __future__ import annotations

try:
    from importlib.metadata import PackageNotFoundError
    from importlib.metadata import version as _metadata_version

    __version__: str = _metadata_version("stoat-ferret")
except PackageNotFoundError:
    __version__ = "0.0.0"  # package not installed (e.g., running from source without install)

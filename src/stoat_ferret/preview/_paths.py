# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""Path confinement helper for preview session directories."""

from __future__ import annotations

from pathlib import Path


def confine_child_path(base_dir: Path, child: str) -> Path:
    """Resolve child under base_dir, raising ValueError if it escapes the base.

    Args:
        base_dir: The base directory the resolved path must stay within.
        child: The child path segment (e.g. a session ID) to join to base_dir.

    Returns:
        The resolved absolute path of base_dir/child.

    Raises:
        ValueError: If the resolved candidate escapes base_dir via traversal,
            absolute override, or symlink, or if it resolves to base_dir itself.
    """
    base_resolved = base_dir.resolve()
    candidate = (base_dir / child).resolve()
    if candidate == base_resolved or not candidate.is_relative_to(base_resolved):
        raise ValueError(f"path escapes base directory: {child!r}")
    return candidate

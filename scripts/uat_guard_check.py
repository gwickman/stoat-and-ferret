# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""PYTHONOPTIMIZE guard check — validates if/raise guards survive python -O."""

condition = False
if not condition:
    raise RuntimeError("guard check: element not visible under PYTHONOPTIMIZE=1")

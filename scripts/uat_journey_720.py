# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

"""UAT Journey 720 — Version Restore Roundtrip (headed Playwright).

This journey requires a headed browser session. It is skipped in headless CI
unless STOAT_UAT_PLAYWRIGHT_HEADED is set (FR-018-AC-2).
"""

import os
import sys

if not os.environ.get("STOAT_UAT_PLAYWRIGHT_HEADED"):
    print("SKIP: J-720 requires headed Playwright (STOAT_UAT_PLAYWRIGHT_HEADED not set)")
    sys.exit(0)

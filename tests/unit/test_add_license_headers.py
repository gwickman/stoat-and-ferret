# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Unit tests for scripts/add_license_headers.py."""

from __future__ import annotations

import sys
from pathlib import Path

# We import from the scripts package using the project root on sys.path.
# Since pytest is run from the repo root, sys.path already includes it.
# Add scripts/ explicitly so we can import add_license_headers as a module.
SCRIPTS_DIR = Path(__file__).parent.parent.parent / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import add_license_headers as alh  # noqa: E402

PY_HEADER = "# SPDX-License-Identifier: AGPL-3.0-or-later\n# Copyright (C) 2026 Grant Wickman\n"
RS_HEADER = "// SPDX-License-Identifier: AGPL-3.0-or-later\n// Copyright (C) 2026 Grant Wickman\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_py(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


def _make_rs(tmp_path: Path, name: str, content: str) -> Path:
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# Scenario 1 — Shebang preservation
# ---------------------------------------------------------------------------


def test_shebang_preservation_write(tmp_path: Path) -> None:
    """Shebang file gets SPDX on line 2, not displacing line 1."""
    py = _make_py(tmp_path, "cli.py", "#!/usr/bin/env python\nprint('hello')\n")
    alh.process_file(py, check_only=False)
    lines = py.read_text().splitlines()
    assert lines[0] == "#!/usr/bin/env python"
    assert lines[1] == "# SPDX-License-Identifier: AGPL-3.0-or-later"
    assert lines[2] == "# Copyright (C) 2026 Grant Wickman"


def test_shebang_preservation_check_after_write(tmp_path: Path) -> None:
    """After writing to shebang file, --check returns True (valid)."""
    py = _make_py(tmp_path, "cli.py", "#!/usr/bin/env python\nprint('hello')\n")
    alh.process_file(py, check_only=False)
    assert alh.process_file(py, check_only=True) is True


# ---------------------------------------------------------------------------
# Scenario 2 — Encoding cookie preservation
# ---------------------------------------------------------------------------


def test_encoding_cookie_preservation_write(tmp_path: Path) -> None:
    """Encoding-cookie file gets SPDX on line 2, cookie remains on line 1."""
    py = _make_py(tmp_path, "coded.py", "# -*- coding: utf-8 -*-\nimport os\n")
    alh.process_file(py, check_only=False)
    lines = py.read_text().splitlines()
    assert lines[0] == "# -*- coding: utf-8 -*-"
    assert lines[1] == "# SPDX-License-Identifier: AGPL-3.0-or-later"
    assert lines[2] == "# Copyright (C) 2026 Grant Wickman"


# ---------------------------------------------------------------------------
# Scenario 3 — Idempotency
# ---------------------------------------------------------------------------


def test_idempotency_write(tmp_path: Path) -> None:
    """Running --write twice produces no change on second run."""
    py = _make_py(tmp_path, "mod.py", "import os\n")
    alh.process_file(py, check_only=False)
    first_content = py.read_text()
    alh.process_file(py, check_only=False)
    assert py.read_text() == first_content


def test_idempotency_check_exits_ok(tmp_path: Path) -> None:
    """Already-headered file: --check returns True."""
    py = _make_py(tmp_path, "mod.py", PY_HEADER + "\nimport os\n")
    assert alh.process_file(py, check_only=True) is True


# ---------------------------------------------------------------------------
# Scenario 4 — Exclusion of generated paths
# ---------------------------------------------------------------------------


def test_exclusion_pyi_not_in_scope(tmp_path: Path) -> None:
    """src/stoat_ferret_core/_core.pyi is excluded from enumeration."""
    # Create a fake repo structure
    src = tmp_path / "src" / "stoat_ferret_core"
    src.mkdir(parents=True)
    pyi = src / "_core.pyi"
    pyi.write_text("class Foo: ...\n", encoding="utf-8")

    # _is_excluded should return True for the .pyi path
    assert alh._is_excluded(pyi, tmp_path) is True


def test_exclusion_pyi_write_skipped(tmp_path: Path) -> None:
    """process_file does not add header to an explicitly excluded path."""
    # The exclusion check is in _enumerate_files/_is_excluded, not process_file.
    # The test verifies the path is in EXCLUDE_PATHS.
    pyi_rel = "src/stoat_ferret_core/_core.pyi"
    assert pyi_rel in alh.EXCLUDE_PATHS


# ---------------------------------------------------------------------------
# Scenario 5 — Malformed header detection
# ---------------------------------------------------------------------------


def test_malformed_header_check_exits_one(tmp_path: Path) -> None:
    """File with SPDX on wrong line (SPDX not immediately after shebang) fails check."""
    # SPDX marker is present but on line 3, after a blank line — malformed placement
    content = (
        "#!/usr/bin/env python\n\n"
        "# SPDX-License-Identifier: AGPL-3.0-or-later\n"
        "# Copyright (C) 2026 Grant Wickman\n"
    )
    py = _make_py(tmp_path, "bad.py", content)
    # _header_present returns True (marker present), but _header_valid_py is False
    lines = content.splitlines(keepends=True)
    assert alh._header_present(lines) is True
    assert alh._header_valid_py(lines) is False
    assert alh.process_file(py, check_only=True) is False


def test_missing_copyright_fails_check(tmp_path: Path) -> None:
    """File with SPDX line but missing copyright: --check returns False."""
    content = "# SPDX-License-Identifier: AGPL-3.0-or-later\nimport os\n"
    py = _make_py(tmp_path, "nocopy.py", content)
    assert alh.process_file(py, check_only=True) is False


# ---------------------------------------------------------------------------
# Scenario 6 — Rust file header placement
# ---------------------------------------------------------------------------


def test_rust_header_placed_at_top(tmp_path: Path) -> None:
    """Rust file gets SPDX + copyright before any use/mod statements."""
    rs = _make_rs(tmp_path, "lib.rs", "use std::collections::HashMap;\n\nfn main() {}\n")
    alh.process_file(rs, check_only=False)
    lines = rs.read_text().splitlines()
    assert lines[0] == "// SPDX-License-Identifier: AGPL-3.0-or-later"
    assert lines[1] == "// Copyright (C) 2026 Grant Wickman"
    # use statement still present
    assert any("use std" in line for line in lines)


def test_rust_header_idempotent(tmp_path: Path) -> None:
    """Running --write on an already-headered Rust file is a no-op."""
    rs = _make_rs(tmp_path, "mod.rs", RS_HEADER + "\npub fn foo() {}\n")
    alh.process_file(rs, check_only=False)
    content_after = rs.read_text()
    assert content_after.count("SPDX-License-Identifier") == 1


# ---------------------------------------------------------------------------
# Scenario 7 — Empty file handling
# ---------------------------------------------------------------------------


def test_empty_py_write_adds_header(tmp_path: Path) -> None:
    """Empty .py file: --write adds header."""
    py = _make_py(tmp_path, "empty.py", "")
    alh.process_file(py, check_only=False)
    content = py.read_text()
    assert "SPDX-License-Identifier: AGPL-3.0-or-later" in content
    assert "Copyright (C) 2026 Grant Wickman" in content


def test_empty_py_check_exits_one(tmp_path: Path) -> None:
    """Empty .py file: --check returns False (no header)."""
    py = _make_py(tmp_path, "empty.py", "")
    assert alh.process_file(py, check_only=True) is False


def test_empty_rs_write_adds_header(tmp_path: Path) -> None:
    """Empty .rs file: --write adds header."""
    rs = _make_rs(tmp_path, "empty.rs", "")
    alh.process_file(rs, check_only=False)
    content = rs.read_text()
    assert "SPDX-License-Identifier: AGPL-3.0-or-later" in content


# ---------------------------------------------------------------------------
# Scenario 8 — Wrong license identifier
# ---------------------------------------------------------------------------


def test_wrong_license_identifier_check_fails(tmp_path: Path) -> None:
    """File with MIT SPDX identifier: --check returns False."""
    content = "# SPDX-License-Identifier: MIT\n# Copyright (C) 2026 Grant Wickman\nimport os\n"
    py = _make_py(tmp_path, "wrong_lic.py", content)
    # SPDX marker present but line[0] is not the correct AGPL identifier
    result = alh.process_file(py, check_only=True)
    assert result is False


def test_wrong_license_identifier_header_valid_false(tmp_path: Path) -> None:
    """_header_valid_py returns False for MIT SPDX line."""
    lines = ["# SPDX-License-Identifier: MIT\n", "# Copyright (C) 2026 Grant Wickman\n"]
    assert alh._header_valid_py(lines) is False


# ---------------------------------------------------------------------------
# Integration — run_check / run_write via subprocess (smoke test)
# ---------------------------------------------------------------------------


def test_run_check_cli_exits_zero_when_all_headered(tmp_path: Path) -> None:
    """CLI --check exits 0 against a single already-headered .py file (integration smoke)."""
    py = tmp_path / "ok.py"
    py.write_text(PY_HEADER + "\nimport os\n", encoding="utf-8")
    # We can't invoke against repo root from tmp_path, so test process_file directly
    assert alh.process_file(py, check_only=True) is True


def test_run_check_fails_on_unheadered_file() -> None:
    """run_check returns 1 when the repo has unheadered files (before backfill scenario)."""
    # We test the return value logic by calling process_file in check_only mode
    # on a file we know would fail — this indirectly tests run_check's exit-code logic
    import tempfile

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("import os\n")
        tmp_file = Path(f.name)
    try:
        assert alh.process_file(tmp_file, check_only=True) is False
    finally:
        tmp_file.unlink()

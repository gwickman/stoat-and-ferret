# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman
"""Regression guard: C4 Location: citations must resolve to actual symbol line numbers."""

import re
from pathlib import Path

import pytest

MAIN_C4 = Path(__file__).parents[2] / "docs" / "C4-Documentation"

PRODUCT_SRC = Path(__file__).parents[2] / "src" / "stoat_ferret"

# (c4_doc_relative, source_file_relative_to_src, symbol_pattern)
SYMBOLS = [
    # c4-code-stoat-ferret-render.md
    (
        "c4-code-stoat-ferret-render.md",
        "render/executor.py",
        r"class RenderExecutor",
    ),
    (
        "c4-code-stoat-ferret-render.md",
        "render/service.py",
        r"class RenderService",
    ),
    (
        "c4-code-stoat-ferret-render.md",
        "render/worker.py",
        r"def _maybe_route_filter_to_file",
    ),
    # c4-code-stoat-ferret-api.md
    (
        "c4-code-stoat-ferret-api.md",
        "api/app.py",
        r"def lifespan",
    ),
    (
        "c4-code-stoat-ferret-api.md",
        "api/app.py",
        r"def create_app",
    ),
    # c4-code-stoat-ferret-api-services.md
    (
        "c4-code-stoat-ferret-api-services.md",
        "api/services/scan.py",
        r"def validate_scan_path",
    ),
    (
        "c4-code-stoat-ferret-api-services.md",
        "api/services/scan.py",
        r"def make_scan_handler",
    ),
    (
        "c4-code-stoat-ferret-api-services.md",
        "api/services/scan.py",
        r"def scan_directory",
    ),
    (
        "c4-code-stoat-ferret-api-services.md",
        "api/services/scan.py",
        r"def _auto_queue_proxies",
    ),
]


def _find_doc_line(doc_path: Path, source_file: str, symbol_pattern: str) -> int | None:
    """Return the start line number cited in the C4 doc for the given source file and symbol.

    Handles two citation formats:
      - ``Location`` field: ``Location``, ``**Location**:``, or ``- Location:`` followed by path:N
      - Inline paren/backtick: ``(`basename:N`)``
    """
    basename = Path(source_file).name
    text = doc_path.read_text(encoding="utf-8")

    symbol_name_m = re.search(r"def (\w+)|class (\w+)", symbol_pattern)
    if not symbol_name_m:
        return None
    name = symbol_name_m.group(1) or symbol_name_m.group(2)

    # Combined pattern: "Location" with optional markdown bold decoration + any chars to
    # basename:N on the same line, OR inline (`basename:N`) backtick-paren form.
    loc_re = re.compile(
        r"Location[^:\n]*:.*?" + re.escape(basename) + r":(\d+)"
        r"|"
        r"\([`']?" + re.escape(basename) + r":(\d+)[`']?\)"
    )

    # Find symbol entry as a section header or bullet-entry start.
    # Must be first significant token on the line to exclude references in description text.
    candidates: list[int] = []
    for m in re.finditer(re.escape(name), text):
        pos = m.start()
        line_start = text.rfind("\n", 0, pos) + 1
        line_end = text.find("\n", pos)
        line_text = text[line_start : line_end if line_end != -1 else len(text)]
        stripped = line_text.strip()
        # Accept only genuine entry-header forms (section header or bullet opener)
        is_header = bool(re.match(r"#{1,6}\s+" + re.escape(name) + r"\b", stripped))
        is_bullet = stripped.startswith(f"`{name}") or stripped.startswith(f"- `{name}")
        if not (is_header or is_bullet):
            continue
        # Skip dependency/import lines
        if re.search(r"Dependencies:|Implementations:|stoat_ferret\.", stripped):
            continue
        candidates.append(pos)

    if not candidates:
        # Fallback: use any occurrence
        idx = text.find(name)
        if idx == -1:
            return None
        candidates = [idx]

    # From each candidate, find nearest following location citation and take the closest
    best: int | None = None
    best_dist = float("inf")
    for pos in candidates:
        lm = loc_re.search(text, pos)
        if lm:
            dist = lm.start() - pos
            if dist < best_dist:
                best_dist = dist
                # group(1) for Location: form, group(2) for inline form
                raw = lm.group(1) or lm.group(2)
                best = int(raw)

    return best


def _find_source_line(src_path: Path, symbol_pattern: str) -> int | None:
    """Return the 1-based line number of the first match of symbol_pattern in src_path."""
    lines = src_path.read_text(encoding="utf-8").splitlines()
    compiled = re.compile(symbol_pattern)
    for i, line in enumerate(lines, start=1):
        if compiled.search(line):
            return i
    return None


@pytest.mark.parametrize("doc_name,source_rel,symbol_pattern", SYMBOLS)
def test_c4_location_matches_source(doc_name: str, source_rel: str, symbol_pattern: str) -> None:
    """Assert that each C4 Location: citation matches the actual symbol line in source."""
    doc_path = MAIN_C4 / doc_name
    src_path = PRODUCT_SRC / source_rel

    assert doc_path.exists(), f"C4 doc not found: {doc_path}"
    assert src_path.exists(), f"Source file not found: {src_path}"

    doc_line = _find_doc_line(doc_path, source_rel, symbol_pattern)
    assert doc_line is not None, f"No Location: citation for '{symbol_pattern}' in {doc_name}"

    actual_line = _find_source_line(src_path, symbol_pattern)
    assert actual_line is not None, f"Symbol '{symbol_pattern}' not found in {source_rel}"

    assert doc_line == actual_line, (
        f"{doc_name}: Location '{source_rel}:{doc_line}' cited for '{symbol_pattern}' "
        f"but symbol is actually at line {actual_line}. Update the C4 doc."
    )

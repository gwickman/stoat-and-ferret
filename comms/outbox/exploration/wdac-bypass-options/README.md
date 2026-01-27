# WDAC Bypass Options for pytest

## Problem

Windows Defender Application Control (WDAC) is blocking Python executables in the `.venv` directory, preventing local test execution with pytest.

## Environment

| Component | Location | Status |
|-----------|----------|--------|
| .venv Python | `.venv/Scripts/python.exe` | BLOCKED |
| .venv pytest | `.venv/Scripts/pytest.exe` | BLOCKED |
| uv | `~/.local/bin/uv.exe` | BLOCKED |
| System Python 3.12 | `AppData/Local/Programs/Python/Python312` | ALLOWED |
| WSL | Not installed | N/A |
| Docker | Not installed | N/A |

## Findings Summary

### What's Blocked

- All executables in `.venv/Scripts/` (Python, pytest, maturin, etc.)
- All executables in `~/.local/bin/` (uv, uvx)
- Generally: any executable in user-writable directories

### What Works

- Python 3.12 from official installer (`AppData/Local/Programs/Python/Python312`)
- The Python launcher (`py.exe`) when pointing to system Python
- Pre-built binaries in system-trusted locations

### Key Insight

The Rust extension (`_core.pyd`) was built for Python 3.13 (the venv version). System Python is 3.12, so the extension won't load even though Python itself can run.

## Recommended Solution

**Install Python 3.13 system-wide** using the official python.org installer.

This requires no admin privileges and places Python in an allowed location.

See [recommended-solution.md](./recommended-solution.md) for detailed steps.

## Documentation

- [System Python Option](./system-python-option.md) - Using official installer Python
- [uv Tool Option](./uv-tool-option.md) - Why uv tool run doesn't work
- [Containerization Option](./containerization-option.md) - WSL/Docker alternatives
- [Recommended Solution](./recommended-solution.md) - Implementation guide

## Quick Reference

```bash
# After installing Python 3.13 from python.org:
"C:\Users\grant\AppData\Local\Programs\Python\Python313\python.exe" -m pip install --user pytest pytest-cov

# Run tests
cd C:\Users\grant\Documents\projects\stoat-and-ferret
PYTHONPATH=src "C:\Users\grant\AppData\Local\Programs\Python\Python313\python.exe" -m pytest tests/ -v
```

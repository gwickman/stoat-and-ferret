# System Python Option

## Overview

Using a system-wide Python installation (installed via official installer to `AppData\Local\Programs`) instead of the .venv Python.

## Findings

### Available System Python

- **Location**: `C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe`
- **Version**: Python 3.12.10
- **Status**: WDAC ALLOWS EXECUTION

### Test Results

```bash
# This works - not blocked by WDAC
/c/Users/grant/AppData/Local/Programs/Python/Python312/python.exe --version
# Output: Python 3.12.10

# Installed pytest and pytest-cov successfully
python.exe -m pip install --user pytest pytest-cov
# Successfully installed pytest-9.0.2 pytest-cov-7.0.0

# Test collection works
python.exe -m pytest tests/ --collect-only
# Collected 77 tests
```

### Blockers

1. **Python Version Mismatch**: The venv uses Python 3.13, but the system Python is 3.12
2. **Rust Extension Incompatibility**: The `_core.pyd` was built for Python 3.13 and won't load in Python 3.12
3. **Maturin Blocked**: Cannot rebuild the extension because `maturin.exe` itself is blocked by WDAC

```bash
# Attempting to rebuild fails
python.exe -m maturin develop
# OSError: [WinError 4551] An Application Control policy has blocked this file
```

### What Would Be Needed

To make this approach work:

1. Install Python 3.13 system-wide (official installer to `AppData\Local\Programs`)
2. Or downgrade the project to Python 3.12 and rebuild all extensions

## Viability Assessment

**Status: PARTIALLY VIABLE**

- System Python 3.12 is allowed by WDAC
- Would need Python 3.13 installed system-wide to match venv
- Installation packages must go to user locations (`pip install --user`) since Scripts directory may also be blocked

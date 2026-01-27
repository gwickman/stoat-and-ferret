# uv Tool Run Option

## Overview

Using `uv tool run` or `uvx` to run pytest without activating the venv.

## Findings

### uv Location

- **Location**: `C:\Users\grant\.local\bin\uv.exe`
- **Version**: Unknown (cannot execute)
- **Status**: BLOCKED BY WDAC

### Test Results

```bash
# uv.exe is blocked
uv --version
# Exit code 126: Permission denied

# uvx is just a shim that calls uv.exe
uvx pytest
# Also blocked
```

### Why It's Blocked

- `uv.exe` is installed in `~/.local/bin/`, a user-writable directory
- WDAC policies typically block executables in user directories
- Same applies to `uvx.exe` and `uvw.exe`

### What Would Be Needed

To make this approach work:

1. Install uv to a system-trusted location (e.g., `C:\Program Files\uv\`)
2. Or get IT/admin to whitelist the `.local\bin` directory in WDAC policy
3. Or code-sign uv.exe with a trusted certificate

## Viability Assessment

**Status: NOT VIABLE**

- uv.exe itself is blocked by WDAC
- No workaround without admin intervention to either:
  - Whitelist the directory
  - Move uv to a trusted location

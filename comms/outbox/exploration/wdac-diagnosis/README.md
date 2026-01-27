# WDAC Diagnosis Summary

## Problem
Windows Application Control (WDAC) policy blocks execution of unsigned executables from user directories, preventing:
- Python from `.venv/Scripts/python.exe` (unsigned)
- uv package manager from `~/.local/bin/uv.exe` (unsigned)
- All pip-installed tools (pytest.exe, mypy.exe, maturin.exe, etc.)

## Root Cause
The system has an enterprise WDAC policy (Policy ID: `{0283ac0f-fff1-49ae-ada1-8a933130cad6}`) that requires executables to meet "Enterprise signing level requirements." Executables in virtual environments and user tool directories are typically unsigned.

## Blocked Executables
| Executable | Location | Signing Status |
|------------|----------|----------------|
| python.exe | .venv/Scripts/ | NotSigned |
| uv.exe | ~/.local/bin/ | NotSigned |
| pytest.exe | .venv/Scripts/ | NotSigned |
| mypy.exe | .venv/Scripts/ | NotSigned |
| maturin.exe | .venv/Scripts/ | NotSigned |

## Working Alternatives
| Tool | Location | Signing Status | Works? |
|------|----------|----------------|--------|
| Python 3.12 | C:\Users\grant\AppData\Local\Programs\Python\Python312\ | Valid (PSF signed) | Yes |
| cargo | ~/.cargo/bin/ | Works via PowerShell | Yes |

## Test Results

### Rust Tests (cargo test)
**Status: PASS** - 201 unit tests + 83 doc tests all pass

### Python Tests (pytest)
**Status: BLOCKED** - The stoat_ferret_core module cannot be built/installed because:
1. maturin.exe (the build tool) is blocked by WDAC
2. Even if built elsewhere, the compiled .pyd file would need to be loaded

## Recommendations

### Short-term Workarounds
1. **Use signed system Python for non-PyO3 tests** - Pure Python tests can run via `C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe -m pytest`
2. **Run CI in an environment without WDAC** - GitHub Actions, Docker, or a dev VM
3. **Request IT exception** - Add the project's `.venv` directory to an allowed path list

### Long-term Solutions
1. **WDAC path rule exception** - Configure policy to allow executables from trusted development directories
2. **Developer mode machine** - Use a machine without enterprise WDAC policy for local development
3. **Pre-built wheels** - Build maturin wheels in CI and install pre-built artifacts locally (still may be blocked depending on policy)

## Impact on Development
- **Rust development**: Unaffected - cargo test works normally
- **Python development**: Blocked locally; must use CI for testing PyO3 bindings
- **Continuous Integration**: Should work (GitHub Actions doesn't have WDAC)

# UV.exe SAC Blocking Workarounds

## Summary

Windows Smart App Control (SAC) blocks uv.exe and all unsigned executables in uv-created virtual environments. This exploration found a complete workaround using the system Python installation.

## Root Cause

Smart App Control is enabled (`SmartAppControlState: On`) and blocks:
- `uv.exe` - The Astral uv package manager (unsigned)
- `.venv/Scripts/python.exe` - Venv Python created by uv (unsigned copy)
- `.venv/Scripts/*.exe` - All venv scripts including pytest, mypy, ruff

## Working Solution

**Use the Windows Python Launcher (`py`) with system Python 3.12:**

```bash
# Run tests (Python)
PYTHONPATH=src py -3.12 -m pytest tests/ -v --no-cov

# Run tests (Rust)
cargo test

# Build Rust extension for Python
cd rust/stoat_ferret_core
PYO3_PYTHON="C:/Users/grant/AppData/Local/Programs/Python/Python312/python.exe" cargo build --release
cp target/release/stoat_ferret_core.dll ../../src/stoat_ferret_core/_core.pyd
```

## Why This Works

1. **py.exe is signed** - The Windows Python Launcher is code-signed by Python Software Foundation
2. **System Python is signed** - python.exe from python.org installer is signed
3. **cargo.exe works** - Installed via rustup, appears to be trusted by SAC
4. **PYO3_PYTHON override** - Tells pyo3 to use signed Python instead of blocked venv Python

## Test Results

| Approach | Result |
|----------|--------|
| `uv run pytest` | **BLOCKED** |
| `py -3.12 -m pytest` | **SUCCESS** (77/77 tests) |
| `cargo test` | **SUCCESS** (83/83 tests) |
| `cargo build` (with PYO3_PYTHON) | **SUCCESS** |

## Files in This Exploration

- `README.md` - This summary
- `test-results.md` - Detailed test results for each approach
- `recommended-fix.md` - Specific steps to fix auto-dev execution

## Implications for Auto-Dev

The MCP server should:
1. Detect SAC state via PowerShell
2. Use alternative commands when SAC is enabled
3. Skip coverage collection (requires instrumented extension)
4. Use `py -3.12` instead of `uv run python`

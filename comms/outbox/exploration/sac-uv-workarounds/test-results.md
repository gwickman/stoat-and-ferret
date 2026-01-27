# Test Results: UV.exe SAC Blocking Workarounds

## Environment

- **OS**: Windows 10.0.26200.7623
- **Smart App Control State**: ON
- **AppLocker Policy**: Empty (SAC only, no WDAC policies)

## Test Results

### 1. Direct CMD/PowerShell Execution of uv

| Shell | Command | Result |
|-------|---------|--------|
| Git Bash | `uv run pytest tests/ -v` | **BLOCKED** - Permission denied (exit code 126) |
| PowerShell | `& 'C:\Users\grant\.local\bin\uv.exe' --version` | **BLOCKED** - "An Application Control policy has blocked this file" |
| CMD | `C:\Users\grant\.local\bin\uv.exe --version` | **BLOCKED** - Silent failure (no output) |

**Conclusion**: uv.exe is blocked in ALL shells, not just Git Bash. The error manifests differently:
- Git Bash: "Permission denied"
- PowerShell: Explicit Application Control error
- CMD: Silent failure

### 2. py Launcher Approach

| Command | Result |
|---------|--------|
| `py -3.12 --version` | **SUCCESS** - Python 3.12.10 |
| `py -3.12 -m pytest --version` | **SUCCESS** - pytest 9.0.2 |
| `py -3.12 -m pytest tests/ -v --no-cov` | **SUCCESS** - 77/77 tests passed |

**Conclusion**: The Windows Python Launcher (`py.exe`) and system Python work because they are **code-signed by Python Software Foundation**.

### 3. Code Signature Analysis

| Executable | Signed | Status |
|------------|--------|--------|
| uv.exe | **NOT SIGNED** | Blocked by SAC |
| .venv/Scripts/python.exe | **NOT SIGNED** | Blocked by SAC (created by uv) |
| .venv/Scripts/pytest.exe | **NOT SIGNED** | Blocked by SAC |
| .venv/Scripts/maturin.exe | **NOT SIGNED** | Blocked by SAC |
| cargo.exe | **NOT SIGNED** | **WORKS** (trusted install path?) |
| C:\...\Python312\python.exe | **SIGNED** (PSF) | Works |
| C:\...\Launcher\py.exe | **SIGNED** (PSF) | Works |

**Interesting Finding**: cargo.exe is unsigned but works. This suggests SAC has a trusted location list or cargo was previously approved during installation.

### 4. Alternative Package Managers

| Approach | Result |
|----------|--------|
| System Python pip | **BLOCKED** - venv pip is unsigned |
| py -3.12 -m pip | **SUCCESS** - System pip works |
| maturin (bundled binary) | **BLOCKED** - Internal binary unsigned |

### 5. Rust Build Tests

| Command | Result |
|---------|--------|
| `cargo test` | **SUCCESS** - 83/83 tests pass |
| `cargo build --release` (default venv) | **FAILED** - pyo3 tried to use blocked venv python |
| `PYO3_PYTHON=<system-python> cargo build --release` | **SUCCESS** - Full build works |

### 6. Full Workaround Test

Complete end-to-end Python test execution:

```bash
# Build Rust extension with system Python
cd rust/stoat_ferret_core
PYO3_PYTHON="C:/Users/grant/AppData/Local/Programs/Python/Python312/python.exe" cargo build --release

# Copy extension to src directory
cp target/release/stoat_ferret_core.dll ../../src/stoat_ferret_core/_core.pyd

# Run tests with system Python
cd ../..
PYTHONPATH=src py -3.12 -m pytest tests/ -v --no-cov
```

**Result**: **SUCCESS** - 77/77 tests passed

## Key Findings

1. **Root Cause**: Smart App Control blocks ALL unsigned executables, including:
   - uv.exe (the package manager)
   - All executables inside .venv/Scripts/ created by uv
   - Bundled binaries in Python packages (e.g., maturin's internal binary)

2. **Code Signatures Matter**: Only executables signed by trusted publishers work:
   - Python.exe from python.org (signed by PSF)
   - py.exe Windows Launcher (signed by PSF)

3. **venv Python is Unsigned**: uv creates venvs with unsigned copies of python.exe, which are blocked.

4. **Cargo Works Despite No Signature**: Likely due to being installed via rustup which SAC may trust as an "installer".

5. **Complete Workaround Exists**: Using system Python 3.12 with py launcher and setting PYO3_PYTHON for Rust builds allows full development workflow.

# Working Alternatives

## What Works

### 1. Cargo / Rust Tests
**Status: Fully Working**

```bash
cargo test --manifest-path rust/stoat_ferret_core/Cargo.toml
```

Result: 201 unit tests + 83 doc tests pass

Cargo and the Rust toolchain work normally because:
- Rust binaries are generally signed or in allowed paths
- The compiled test executables run from target/debug/ which may be treated differently

### 2. Signed System Python
**Status: Working (but limited)**

```bash
"C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe" -c "print('hello')"
# Output: hello

"C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe" -m pytest --version
# Output: pytest 9.0.2
```

The officially installed Python 3.12 from python.org is signed with a valid certificate:
- Signer: Python Software Foundation
- Certificate: DE01DAAE82D04F466A576E178F6B07A839238953
- Status: Valid

**Limitation:** Cannot test stoat_ferret_core because the module isn't installed in this Python, and maturin (needed to build it) is blocked.

## What Doesn't Work

### 1. Virtual Environment Python
```bash
.venv/Scripts/python.exe -c "print('hello')"
# Permission denied
```

### 2. uv Package Manager
```bash
uv run pytest tests/
# Permission denied
```

### 3. Any pip-installed tool
- pytest.exe - blocked
- mypy.exe - blocked
- maturin.exe - blocked
- ruff.exe - blocked

## Workarounds for Python Testing

### Option A: CI-Only Testing
Run all Python/PyO3 binding tests in CI (GitHub Actions), which doesn't have WDAC restrictions.

### Option B: Install pytest globally in signed Python
```powershell
& "C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe" -m pip install pytest
```
This would allow running pure Python tests, but still can't test PyO3 bindings without building the Rust extension.

### Option C: Pre-built wheel from CI
1. Build wheel in CI
2. Download the .whl artifact
3. Install into signed Python: `pip install stoat_ferret_core-*.whl`
4. Run tests with signed Python

**Note:** This may still fail if the compiled .pyd file is blocked by WDAC.

### Option D: Development VM/Container
Use a virtual machine or WSL2 container without WDAC restrictions for local development testing.

## Summary Table

| Component | Status | Notes |
|-----------|--------|-------|
| Rust tests | Working | cargo test passes |
| Python (system) | Working | Signed, but no stoat_ferret_core |
| Python (.venv) | Blocked | NotSigned |
| uv | Blocked | NotSigned |
| maturin | Blocked | NotSigned |
| pytest (.venv) | Blocked | NotSigned |
| CI testing | Should work | No WDAC on GitHub Actions |

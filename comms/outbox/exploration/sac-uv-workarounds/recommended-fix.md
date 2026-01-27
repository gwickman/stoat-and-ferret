# Recommended Fix: Auto-Dev Execution on SAC-Enabled Windows

## Problem Summary

Smart App Control (SAC) blocks all unsigned executables including uv.exe and all binaries in uv-created virtual environments. This prevents the standard `uv run pytest` workflow.

## Recommended Solution: System Python Workflow

### Prerequisites

- Python 3.12+ installed from python.org (not via uv/pipx/scoop)
- pytest, coverage, and other dev dependencies installed in system Python
- Rust toolchain installed via rustup

### Step-by-Step Execution

```bash
# 1. Build Rust extension (if PyO3 bindings exist)
cd rust/stoat_ferret_core
PYO3_PYTHON="C:/Users/grant/AppData/Local/Programs/Python/Python312/python.exe" cargo build --release

# 2. Copy extension to correct location
cp target/release/stoat_ferret_core.dll ../../src/stoat_ferret_core/_core.pyd

# 3. Run Python tests
cd ../..
PYTHONPATH=src py -3.12 -m pytest tests/ -v --no-cov

# 4. Run Rust tests (no changes needed)
cd rust/stoat_ferret_core
cargo test

# 5. Run Rust linting
cargo clippy -- -D warnings
```

### Environment Variables

Set these in the shell or add to CLAUDE.md for auto-dev:

```bash
export PYO3_PYTHON="C:/Users/grant/AppData/Local/Programs/Python/Python312/python.exe"
export PYTHONPATH="src"
```

### Commands Comparison

| Standard (uv) | SAC-Safe Alternative |
|---------------|---------------------|
| `uv sync` | Pre-install deps in system Python |
| `uv run pytest` | `PYTHONPATH=src py -3.12 -m pytest --no-cov` |
| `uv run mypy src/` | `PYTHONPATH=src py -3.12 -m mypy src/` |
| `uv run ruff check .` | `py -3.12 -m ruff check .` |
| `maturin develop` | See Rust build steps above |

### Why --no-cov?

Coverage collection requires instrumenting the Rust extension which isn't possible without the full maturin install. Skip coverage for local SAC-constrained environments. CI (GitHub Actions) doesn't have SAC and can collect coverage normally.

## Alternative Solutions (Not Recommended)

### 1. Disable Smart App Control
- **Pros**: Everything works
- **Cons**: Reduces system security, SAC cannot be re-enabled without Windows reset

### 2. Use Signed uv Installation
- uv may offer signed binaries in the future
- Currently no official signed release exists

### 3. Create Admin Exception Rules
- Requires WDAC policy management
- Complex to maintain
- Not recommended for individual dev machines

## Implementation for Auto-Dev MCP

Update the MCP server to detect SAC and use alternative commands:

```python
# Detection
def is_sac_enabled() -> bool:
    result = subprocess.run(
        ["powershell.exe", "-Command",
         "Get-MpComputerStatus | Select-Object -ExpandProperty SmartAppControlState"],
        capture_output=True, text=True
    )
    return result.stdout.strip() == "On"

# Command mapping
if is_sac_enabled():
    PYTHON_CMD = "py -3.12"
    PYTEST_CMD = f"PYTHONPATH=src {PYTHON_CMD} -m pytest --no-cov"
else:
    PYTHON_CMD = "uv run python"
    PYTEST_CMD = "uv run pytest"
```

## Verification

After implementing fixes, verify with:

```bash
# Should output Python version
py -3.12 --version

# Should output pytest version
py -3.12 -m pytest --version

# Should pass all tests
PYTHONPATH=src py -3.12 -m pytest tests/ -v --no-cov
```

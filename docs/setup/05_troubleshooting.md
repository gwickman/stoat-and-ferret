# Troubleshooting

This document covers common issues encountered when setting up and developing stoat-and-ferret, along with their solutions.

## Rust / maturin Build Failures

### `maturin develop` Must Run from Project Root

**Symptom:** After running `maturin develop`, importing `stoat_ferret_core` raises `ImportError` or you get a conflicting package.

**Cause:** `maturin develop` was run from the `rust/` subdirectory or with `--manifest-path` instead of from the project root.

**Fix:** Always run maturin from the project root:

```bash
# Correct - from project root
cd /path/to/stoat-and-ferret
uv run maturin develop

# WRONG - do not do this
cd rust/stoat_ferret_core && maturin develop
# WRONG - do not do this
maturin develop --manifest-path rust/stoat_ferret_core/Cargo.toml
```

The `pyproject.toml` at the project root contains `[tool.maturin]` configuration that tells maturin where to find the Rust source. Running from elsewhere bypasses this and creates a conflicting package in site-packages.

If you already ran maturin from the wrong location, clean up and rebuild:

```bash
# Remove potentially conflicting packages from the virtual environment
uv run pip uninstall stoat-ferret stoat_ferret_core -y
uv sync
uv run maturin develop
```

### Windows: Linker Errors (Visual Studio Build Tools)

**Symptom:** `maturin develop` fails with errors like:

```
LINK : fatal error LNK1181: cannot open input file 'python3.lib'
error: linker `link.exe` not found
```

**Cause:** The Visual Studio Build Tools with C++ workload are not installed.

**Fix:** Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/):

1. Download the installer.
2. Select the **"Desktop development with C++"** workload.
3. Ensure the **Windows SDK** component is checked (it usually is by default).
4. Complete the installation and restart your terminal.

### Linux: Missing Build Dependencies

**Symptom:** Rust compilation fails with errors about missing headers or `cc` not found.

**Cause:** Build essentials and pkg-config are not installed.

**Fix:**

```bash
# Debian / Ubuntu
sudo apt update
sudo apt install build-essential pkg-config

# Fedora
sudo dnf groupinstall "Development Tools"
sudo dnf install pkg-config

# Arch
sudo pacman -S base-devel pkg-config
```

### macOS: Missing Xcode Command Line Tools

**Symptom:** Compilation fails with `xcrun: error: invalid active developer path`.

**Fix:**

```bash
xcode-select --install
```

## PyO3 / Import Errors

### `RuntimeError: stoat_ferret_core native extension not built`

**Symptom:** Running the application or tests raises:

```
RuntimeError: stoat_ferret_core native extension not built. Run 'maturin develop' to build the Rust component.
```

**Cause:** The Rust extension has not been compiled, or it was compiled for a different Python version or virtual environment.

**Fix:**

```bash
uv run maturin develop
```

Verify the build succeeded:

```bash
uv run python -c "from stoat_ferret_core import health_check; print(health_check())"
```

### `ImportError: DLL load failed` (Windows)

**Symptom:** Importing the Rust extension raises `ImportError: DLL load failed while importing _core`.

**Cause:** The `.pyd` file was compiled for a different Python version, or the Visual C++ Redistributable is missing.

**Fix:**

1. Ensure you are using the same Python version that was active when you ran `maturin develop`.
2. Rebuild the extension: `uv run maturin develop`
3. If the error persists, install the [Visual C++ Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist).

## Windows Smart App Control

**Symptom:** Running compiled executables or `.pyd` files shows "This app has been blocked for your protection" or similar security warnings.

**Cause:** Windows 11's Smart App Control blocks unsigned locally-built binaries.

**Fix:**

1. Open **Windows Security** > **App & browser control** > **Smart App Control settings**.
2. Set Smart App Control to **Off**.

> **Warning:** Smart App Control cannot be re-enabled after being turned off without resetting Windows. Consider this before disabling it.

Alternatively, for individual files:
1. Right-click the blocked file.
2. Select **Properties**.
3. Check **Unblock** at the bottom of the General tab (if present).

## FFmpeg Issues

### FFmpeg Not Found in PATH

**Symptom:** Video processing operations fail with `FileNotFoundError: [Errno 2] No such file or directory: 'ffmpeg'` or tests marked `requires_ffmpeg` fail.

**Cause:** FFmpeg is not installed or not available on the system `PATH`.

**Fix:**

```bash
# Verify FFmpeg is accessible
ffmpeg -version

# If not found, install it:
# Windows: winget install Gyan.FFmpeg
# Linux:   sudo apt install ffmpeg
# macOS:   brew install ffmpeg
```

On Windows, if FFmpeg is installed but not in `PATH`, add its `bin` directory to your system or user `PATH` environment variable.

## Database / Alembic Issues

### Migration Errors on `alembic upgrade head`

**Symptom:** Running `uv run alembic upgrade head` fails with SQL errors or "target database is not up to date."

**Fix:**

For a fresh start (development only -- this deletes all data):

```bash
# Remove the existing database
rm -f stoat_ferret.db data/stoat.db

# Re-run migrations
mkdir -p data
uv run alembic upgrade head
```

If you need to check the current migration state:

```bash
uv run alembic current
uv run alembic history
```

### `sqlalchemy.exc.OperationalError: unable to open database file`

**Symptom:** Alembic or the application cannot create/open the database file.

**Cause:** The parent directory for the database file does not exist.

**Fix:**

```bash
mkdir -p data
```

## GUI / Frontend Issues

### `npm ci` Fails

**Symptom:** `npm ci` in the `gui/` directory fails with dependency resolution errors.

**Fix:**

1. Ensure you are using Node.js 22+ (`node --version`).
2. Delete `node_modules` and retry:

```bash
cd gui
rm -rf node_modules
npm ci
```

3. If `package-lock.json` is outdated or corrupt, regenerate it:

```bash
rm package-lock.json
npm install
```

### `npm run build` Fails with TypeScript Errors

**Symptom:** The build command (`tsc -b && vite build`) fails during TypeScript compilation.

**Cause:** TypeScript version mismatch or missing type definitions.

**Fix:**

```bash
cd gui
rm -rf node_modules
npm ci
npm run build
```

If errors persist, check that your Node.js version matches what CI uses (Node.js 22).

## Python 3.10 Compatibility

### `asyncio.TimeoutError` vs `TimeoutError`

**Symptom:** Tests pass on Python 3.11+ but fail on Python 3.10 with unhandled `TimeoutError` from async operations.

**Cause:** In Python 3.10, `asyncio.TimeoutError` and the built-in `TimeoutError` are **different classes**. They were unified in Python 3.11+. Catching `TimeoutError` does not catch `asyncio.TimeoutError` on Python 3.10.

**Fix:** When catching timeouts from `asyncio.wait_for()` or similar async operations, always use `asyncio.TimeoutError`:

```python
import asyncio

try:
    await asyncio.wait_for(some_coroutine(), timeout=5.0)
except asyncio.TimeoutError:  # NOT except TimeoutError
    handle_timeout()
```

This works correctly on all supported Python versions (3.10, 3.11, 3.12).

## Ruff Lint Failures

### Import Ordering (I001)

**Symptom:** Ruff reports `I001 Import block is un-sorted or un-formatted`.

**Fix:** Let ruff auto-fix the import ordering:

```bash
uv run ruff check --fix src/ tests/
```

Ruff enforces [isort-compatible](https://docs.astral.sh/ruff/rules/unsorted-imports/) import ordering. The standard order is: standard library, third-party, first-party, with blank lines separating each group.

### contextlib.suppress (SIM105)

**Symptom:** Ruff reports `SIM105 Use contextlib.suppress(...) instead of try-except-pass`.

**Fix:** Replace bare `try/except/pass` blocks with `contextlib.suppress`:

```python
# Before (triggers SIM105)
try:
    os.remove(path)
except FileNotFoundError:
    pass

# After
import contextlib

with contextlib.suppress(FileNotFoundError):
    os.remove(path)
```

### Auto-fixing All Lint Issues

```bash
# Fix linting issues
uv run ruff check --fix src/ tests/

# Fix formatting issues
uv run ruff format src/ tests/
```

Ruff is configured with `line-length=100` and `target-version="py310"` and selects rules: `E` (pycodestyle errors), `F` (pyflakes), `I` (isort), `UP` (pyupgrade), `B` (bugbear), `SIM` (simplify).

## Still Stuck?

If you encounter an issue not covered here:

1. Check the [CI workflow](../../.github/workflows/ci.yml) to see exactly how the project is built and tested in CI.
2. Look at the `Dockerfile` to see how a clean build environment is configured.
3. Search existing issues in the project repository.
4. Ensure all [prerequisites](01_prerequisites.md) are correctly installed and on your PATH.

# Prerequisites

This document lists all tools required to build and develop stoat-and-ferret. Install everything listed here before proceeding to [Development Setup](02_development-setup.md).

## Required Tools

### Python 3.10+

The project targets Python >= 3.10 and CI tests across Python 3.10, 3.11, and 3.12. Any of these versions will work.

> **Note:** Some design documents in the repository reference Python 3.11+ or 3.12+, but the actual `pyproject.toml` specifies `requires-python = ">=3.10"` and the CI matrix confirms 3.10 support.

- **Windows:** Download from [python.org](https://www.python.org/downloads/) or install via `winget install Python.Python.3.12`. Ensure "Add to PATH" is checked during installation.
- **Linux:** Use your distribution's package manager (e.g., `sudo apt install python3.12 python3.12-venv`) or [pyenv](https://github.com/pyenv/pyenv).
- **macOS:** Use [Homebrew](https://brew.sh/) (`brew install python@3.12`) or [pyenv](https://github.com/pyenv/pyenv).

Verify with:

```bash
python3 --version   # or `python --version` on Windows
```

### Rust Toolchain (stable)

The Rust core (`stoat_ferret_core`) is compiled via PyO3 with the `abi3-py310` feature, targeting the CPython stable ABI for Python 3.10+.

Install via [rustup](https://rustup.rs/):

```bash
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh
```

On Windows, download and run `rustup-init.exe` from [rustup.rs](https://rustup.rs/).

The CI also uses the `clippy` and `rustfmt` components:

```bash
rustup component add clippy rustfmt
```

Verify with:

```bash
rustc --version
cargo --version
```

### Node.js 22+

The frontend GUI uses React 19, Vite 7, and TypeScript 5.9. Node.js 22 or later is required (CI uses Node.js 22).

- **All platforms:** Use [nvm](https://github.com/nvm-sh/nvm) (Linux/macOS) or [nvm-windows](https://github.com/coreybutler/nvm-windows), or download from [nodejs.org](https://nodejs.org/).

```bash
nvm install 22
nvm use 22
```

Verify with:

```bash
node --version    # should be v22.x or later
npm --version
```

### FFmpeg

FFmpeg is used for video processing operations. It must be available on your `PATH`.

- **Windows:** Download from [ffmpeg.org](https://ffmpeg.org/download.html) or install via `winget install Gyan.FFmpeg`. Add the `bin` directory to your `PATH`.
- **Linux:** `sudo apt install ffmpeg` (Debian/Ubuntu) or equivalent for your distribution.
- **macOS:** `brew install ffmpeg`

Verify with:

```bash
ffmpeg -version
```

> **Note:** Some tests are marked with `@pytest.mark.requires_ffmpeg` and will be skipped if FFmpeg is not installed.

### uv (Python Package Manager)

The project uses [uv](https://docs.astral.sh/uv/) for fast, deterministic Python dependency management.

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"

# Or via pip (any platform)
pip install uv
```

Verify with:

```bash
uv --version
```

### maturin

[maturin](https://www.maturin.rs/) builds the PyO3 Rust extension into a Python-importable module. It is listed as a dev dependency and will be installed by `uv sync`, but you can also install it globally:

```bash
pip install maturin
```

Verify with:

```bash
maturin --version
```

## OS-Specific Notes

### Windows

#### Visual Studio Build Tools

Building the Rust/PyO3 extension on Windows requires the **Visual Studio Build Tools** with the following components:

- **"Desktop development with C++" workload** (includes MSVC compiler)
- **Windows SDK** (typically included with the C++ workload)

Download from [Visual Studio Build Tools](https://visualstudio.microsoft.com/visual-cpp-build-tools/). During installation, select "Desktop development with C++" from the Workloads tab.

Without these, `maturin develop` will fail with linker errors like `LINK : fatal error LNK1181: cannot open input file 'python3.lib'` or `error: linker 'link.exe' not found`.

#### Smart App Control

Windows 11's **Smart App Control** feature may block locally compiled executables (including the Rust extension `.pyd` file) from running, showing errors like "This app has been blocked for your protection."

If you encounter this:

1. Open **Windows Security** > **App & browser control** > **Smart App Control settings**.
2. Set Smart App Control to **Off**. Note that this cannot be turned back on without resetting Windows.
3. Alternatively, right-click the blocked file, select **Properties**, and check **Unblock** if available.

### Linux

Install the essential build tools and pkg-config:

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

### macOS

Install Xcode Command Line Tools, which provide the C compiler and linker needed for Rust builds:

```bash
xcode-select --install
```

If you already have Xcode installed, this step is not needed.

## Summary Checklist

| Tool | Minimum Version | Verify Command |
|------|----------------|----------------|
| Python | 3.10 | `python3 --version` |
| Rust | stable | `rustc --version` |
| Node.js | 22 | `node --version` |
| FFmpeg | any recent | `ffmpeg -version` |
| uv | latest | `uv --version` |
| maturin | 1.0+ | `maturin --version` |

Once all prerequisites are installed, proceed to [Development Setup](02_development-setup.md).

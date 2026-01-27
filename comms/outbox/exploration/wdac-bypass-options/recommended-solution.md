# Recommended Solution

## Summary

After testing all options, the most practical immediate solution is to **install Python 3.13 system-wide** using the official installer.

## Recommended Approach: System Python 3.13

### Why This Works

1. The official Python installer places Python in `AppData\Local\Programs\Python\Python3XX`
2. This location is ALLOWED by WDAC (tested with Python 3.12)
3. Installing matching version (3.13) allows using the pre-built Rust extension

### Implementation Steps

1. **Download Python 3.13 from python.org**
   - https://www.python.org/downloads/release/python-3130/
   - Choose "Windows installer (64-bit)"

2. **Install with these options**:
   - Check "Add Python to PATH" (optional, may conflict with venv)
   - Check "Install for all users" if admin, OR "Install just for me"
   - Default location: `C:\Users\grant\AppData\Local\Programs\Python\Python313`

3. **Install test dependencies**:
   ```bash
   "C:\Users\grant\AppData\Local\Programs\Python\Python313\python.exe" -m pip install --user pytest pytest-cov
   ```

4. **Run tests**:
   ```bash
   cd C:\Users\grant\Documents\projects\stoat-and-ferret
   PYTHONPATH=src "C:\Users\grant\AppData\Local\Programs\Python\Python313\python.exe" -m pytest tests/ -v
   ```

5. **Add to pyproject.toml or script** (optional):
   Create a `run-tests.bat`:
   ```batch
   @echo off
   set PYTHONPATH=%~dp0src
   "C:\Users\grant\AppData\Local\Programs\Python\Python313\python.exe" -m pytest tests/ %*
   ```

### Alternative: Downgrade to Python 3.12

If installing Python 3.13 is not desired:

1. Modify pyproject.toml to use Python 3.12
2. Delete .venv and recreate with Python 3.12
3. Rebuild Rust extension with `maturin develop` (if maturin can run)

Note: This may not work if maturin is also blocked.

## Longer-Term Solutions

### Option A: Request WDAC Exception (Admin Required)

Ask IT to add a publisher rule for Python-related executables:
- Python Software Foundation signed binaries
- Rust/Cargo binaries (for maturin)
- Or path rule for `.venv` directory (less secure)

### Option B: Install WSL2 (Admin Required)

```powershell
wsl --install
```

Then develop inside WSL where WDAC doesn't apply.

### Option C: Use GitHub Actions for Testing

Bypass local WDAC entirely by running tests in CI:
- Push code, let GitHub Actions run tests
- Use `gh run watch` to monitor results
- Good for PR workflows, less ideal for rapid iteration

## Summary Table

| Option | Viable Now? | Admin Required? | Notes |
|--------|-------------|-----------------|-------|
| System Python 3.13 | YES | No | Recommended |
| uv tool run | NO | Yes | uv.exe blocked |
| WSL | NO | Yes | Not installed |
| Docker | NO | Yes | Not installed |
| WDAC Exception | NO | Yes | IT policy change needed |
| GitHub Actions | YES | No | Good for CI, slow for dev |

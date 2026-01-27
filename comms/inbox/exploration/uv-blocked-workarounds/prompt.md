## UV.exe Blocked by Smart App Control - Find Workarounds

Windows Smart App Control is blocking uv.exe when called from Git bash. Error: "can't confirm who published uv.exe that the app tried to load"

### Immediate Tasks - Test Each Approach

1. **Test PowerShell instead of bash**
   Run in PowerShell (not bash):
   ```powershell
   uv run pytest tests/ -v --tb=short 2>&1
   ```
   Does this work? PowerShell may have different execution trust.

2. **Check uv.exe signature**
   ```powershell
   Get-AuthenticodeSignature "C:\Users\grant\.local\bin\uv.exe"
   Get-AuthenticodeSignature "C:\Users\grant\.cargo\bin\uv.exe"  
   where.exe uv
   ```
   Find where uv is installed and check its signature status.

3. **Test direct Python invocation (bypass uv)**
   ```powershell
   # Find the venv Python
   .\.venv\Scripts\python.exe -m pytest tests/ -v --tb=short 2>&1
   ```
   Does calling Python directly work?

4. **Test system Python**
   ```powershell
   where.exe python
   python --version
   py -3 -m pytest tests/ -v --tb=short 2>&1
   ```

5. **Test uvx (uv tool run)**
   ```powershell
   uvx pytest tests/ -v 2>&1
   ```
   This uses a different execution path.

6. **Check Smart App Control status**
   ```powershell
   Get-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy" -ErrorAction SilentlyContinue
   ```

### Document What Works

For each approach, record:
- Exact command used
- Whether it succeeded or failed
- Full error message if failed
- Time to execute if successful

### Output Requirements

Save to: `comms/outbox/exploration/uv-blocked-workarounds/`

Create:
- `README.md` - Summary: what works, what doesn't, recommended approach
- `test-results.md` - Full output of each test
- `recommended-command.md` - The exact command that should be used for pytest

Commit: "docs(exploration): uv.exe blocking workarounds"

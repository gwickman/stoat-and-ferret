## Windows Application Control Diagnosis

Investigate why pytest execution is blocked by Windows Application Control (WDAC) policy.

### Context
- Completion report states: "local execution blocked by Application Control policy preventing execution of binaries from `.venv`"
- This affects the ability to run Python tests during feature development
- Need to understand the exact error and scope of the problem

### Tasks

1. **Reproduce the error**
   - Run `uv run pytest tests/ -v --tb=short` and capture the full error output
   - Try running `uv run python -c "print('hello')"` to see if basic Python works
   - Try running `.venv/Scripts/python.exe -c "print('hello')"` directly

2. **Check Windows event logs for WDAC blocks**
   - Run PowerShell: `Get-WinEvent -LogName "Microsoft-Windows-CodeIntegrity/Operational" -MaxEvents 20 | Format-List`
   - Look for blocked executable paths

3. **Examine the .venv structure**
   - List contents of `.venv/Scripts/` 
   - Check if python.exe and pytest.exe exist and their properties
   - Run `Get-AuthenticodeSignature .venv/Scripts/python.exe` to check signing

4. **Test alternative execution methods**
   - Try `py -m pytest tests/` (system Python)
   - Try `python -m pytest tests/` 
   - Try running cargo test to confirm Rust tests work

5. **Document findings**
   - What exact error message appears?
   - Which executables are blocked?
   - Are there any executables that DO work?

### Output Requirements

Save all findings to: `comms/outbox/exploration/wdac-diagnosis/`

Create these files:
- `README.md` - Summary of findings
- `error-capture.md` - Full error messages captured
- `event-log-analysis.md` - Windows event log findings
- `working-alternatives.md` - What execution methods work

Commit with message: "docs(exploration): WDAC diagnosis for pytest blocking"

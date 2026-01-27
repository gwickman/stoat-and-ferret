# Error Capture

## Error 1: uv run pytest (via bash)

**Command:**
```bash
uv run pytest tests/ -v --tb=short
```

**Error:**
```
Exit code 126
/usr/bin/bash: line 1: /c/Users/grant/.local/bin/uv: Permission denied
```

## Error 2: Direct .venv Python execution (via bash)

**Command:**
```bash
.venv/Scripts/python.exe -c "print('hello')"
```

**Error:**
```
Exit code 126
/usr/bin/bash: line 1: .venv/Scripts/python.exe: Permission denied
```

## Error 3: System Python pytest (module not found)

**Command:**
```bash
"C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe" -m pytest tests/ -v --tb=short
```

**Result:** Pytest runs but all tests fail with:
```
ModuleNotFoundError: No module named 'stoat_ferret_core'
```

This is expected - the module was built into .venv which is blocked, and cannot be rebuilt because maturin.exe is also blocked.

## Error 4: Windows Event Log CodeIntegrity Blocks

Multiple events captured (Event IDs 3033, 3077, 3089):

```
Code Integrity determined that a process (\Device\HarddiskVolume4\Program Files\Git\usr\bin\bash.exe)
attempted to load \Device\HarddiskVolume4\Users\grant\Documents\projects\stoat-and-ferret\.venv\Scripts\python.exe
that did not meet the Enterprise signing level requirements or violated code integrity policy
(Policy ID:{0283ac0f-fff1-49ae-ada1-8a933130cad6}).
```

```
Code Integrity determined that a process (\Device\HarddiskVolume4\Program Files\Git\usr\bin\bash.exe)
attempted to load \Device\HarddiskVolume4\Users\grant\.local\bin\uv.exe
that did not meet the Enterprise signing level requirements or violated code integrity policy
(Policy ID:{0283ac0f-fff1-49ae-ada1-8a933130cad6}).
```

```
Code Integrity determined that a process (\Device\HarddiskVolume4\Windows\System32\WindowsPowerShell\v1.0\powershell.exe)
attempted to load \Device\HarddiskVolume4\Users\grant\Documents\projects\stoat-and-ferret\.venv\Scripts\mypy.exe
that did not meet the Enterprise signing level requirements or violated code integrity policy
(Policy ID:{0283ac0f-fff1-49ae-ada1-8a933130cad6}).
```

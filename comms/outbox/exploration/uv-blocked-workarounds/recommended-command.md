# Recommended Command for Running pytest

## Problem

uv.exe and venv Python are blocked by Windows Smart App Control (unsigned executables).

## Solution

Use the **signed Python312** installation with the venv's packages added to PYTHONPATH.

## Option 1: PowerShell One-Liner

```powershell
$env:PYTHONPATH = "C:\Users\grant\Documents\projects\stoat-and-ferret\.venv\Lib\site-packages;C:\Users\grant\Documents\projects\stoat-and-ferret\src"; & "C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe" -m pytest tests/ -v --tb=short
```

## Option 2: PowerShell Script (run-tests.ps1)

Save this as `run-tests.ps1` in the project root:

```powershell
$projectPath = "C:\Users\grant\Documents\projects\stoat-and-ferret"
$pythonPath = "C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe"

$env:PYTHONPATH = "$projectPath\.venv\Lib\site-packages;$projectPath\src"
Set-Location $projectPath

& $pythonPath -m pytest tests/ -v --tb=short
```

Run with:
```powershell
powershell.exe -ExecutionPolicy Bypass -File run-tests.ps1
```

## Option 3: Python Runner Script

Save this as `run-tests.py` and run with signed Python:

```python
import sys
import os

project_path = r"C:\Users\grant\Documents\projects\stoat-and-ferret"
venv_site_packages = os.path.join(project_path, ".venv", "Lib", "site-packages")

sys.path.insert(0, venv_site_packages)
sys.path.insert(0, os.path.join(project_path, "src"))

os.chdir(project_path)

import pytest
sys.exit(pytest.main(["-v", "--tb=short", "tests/"]))
```

Run with:
```cmd
"C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe" run-tests.py
```

## Key Paths

| Component | Path |
|-----------|------|
| Signed Python | `C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe` |
| venv site-packages | `C:\Users\grant\Documents\projects\stoat-and-ferret\.venv\Lib\site-packages` |
| Project src | `C:\Users\grant\Documents\projects\stoat-and-ferret\src` |

## Notes

- The signed Python312 has a valid Authenticode signature from Python Software Foundation
- The venv packages are still usable - only the venv's python.exe is blocked
- Set both `site-packages` and `src` in PYTHONPATH to ensure all imports work
- This approach may not work for all scenarios (e.g., if packages have compiled extensions that require the specific Python version used to build them)

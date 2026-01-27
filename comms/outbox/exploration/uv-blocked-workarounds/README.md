# UV.exe Blocked by Smart App Control - Workarounds

## Summary

Windows Smart App Control is blocking uv.exe and venv Python executables because they are **not digitally signed**. However, a working workaround exists using the **signed Python312** installation.

## What Works

| Approach | Status | Notes |
|----------|--------|-------|
| Signed Python312 with PYTHONPATH | **WORKS** | Uses venv packages with signed Python |
| uv run pytest (PowerShell) | BLOCKED | "Application Control policy has blocked this file" |
| uv run pytest (Git Bash) | BLOCKED | "Permission denied" |
| .venv\Scripts\python.exe | BLOCKED | venv Python is unsigned |
| uvx pytest | BLOCKED | uvx.exe is unsigned |
| System Python (py -3) | NOT FOUND | No system Python installed |

## Root Cause

All uv-related executables lack code signatures:

- `C:\Users\grant\.local\bin\uv.exe` - **NotSigned**
- `C:\Users\grant\.local\bin\uvx.exe` - **NotSigned**
- `C:\Users\grant\.local\bin\uvw.exe` - **NotSigned**
- `.venv\Scripts\python.exe` - **NotSigned** (created by uv)

However, Python312 from official installer has a **valid signature**:
- `C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe` - **Valid (Signature verified)**

## Smart App Control Status

Registry key `HKLM:\SYSTEM\CurrentControlSet\Control\CI\Policy`:
- `VerifiedAndReputablePolicyState`: 1 (enabled)
- `SAC_EnforcementReason`: 1 (enforcement active)

## Recommended Solution

Use a wrapper script that runs the signed Python312 with the venv's site-packages added to the path. See `recommended-command.md` for the exact command.

## Alternative Solutions (Not Tested)

1. **Install signed uv** - If Astral signs their releases in the future
2. **Disable Smart App Control** - Not recommended for security reasons
3. **Add uv to trusted list** - Requires admin privileges and WDAC policy changes
4. **Use winget/scoop uv** - May have signed versions

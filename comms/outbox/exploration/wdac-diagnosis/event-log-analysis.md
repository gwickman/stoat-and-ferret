# Windows Event Log Analysis

## Log Source
`Microsoft-Windows-CodeIntegrity/Operational`

## Query Command
```powershell
Get-WinEvent -LogName "Microsoft-Windows-CodeIntegrity/Operational" -MaxEvents 20 | Format-List
```

## Key Events Found

### Event ID 3033 - Signing Level Not Met
This is the informational event indicating an executable didn't meet signing requirements.

### Event ID 3077 - Policy Violation Block
This is the blocking event indicating the executable was prevented from running.

### Event ID 3089 - Signature Information
Supplementary event with signature details for correlation.

## Policy Details
- **Policy ID:** `{0283ac0f-fff1-49ae-ada1-8a933130cad6}`
- **Requirement:** Enterprise signing level

## Blocked Paths Observed

| Timestamp | Blocked Path | Parent Process |
|-----------|--------------|----------------|
| 2026-01-27 18:55:12 | .venv\Scripts\python.exe | Git\usr\bin\bash.exe |
| 2026-01-27 18:55:09 | .local\bin\uv.exe | Git\usr\bin\bash.exe |
| 2026-01-27 18:55:06 | .local\bin\uv.exe | Git\usr\bin\bash.exe |
| 2026-01-27 16:28:47 | .venv\Scripts\mypy.exe | WindowsPowerShell\v1.0\powershell.exe |

## Signing Status Verification

```powershell
Get-AuthenticodeSignature .venv\Scripts\python.exe
# Status: NotSigned

Get-AuthenticodeSignature .venv\Scripts\maturin.exe
# Status: NotSigned

Get-AuthenticodeSignature C:\Users\grant\.local\bin\uv.exe
# Status: NotSigned

Get-AuthenticodeSignature C:\Users\grant\AppData\Local\Programs\Python\Python312\python.exe
# Status: Valid
# SignerCertificate: DE01DAAE82D04F466A576E178F6B07A839238953 (Python Software Foundation)
```

## Conclusion
The WDAC policy is correctly enforcing code signing requirements. The blocked executables are legitimately unsigned. The only working Python installation is the officially signed PSF Python 3.12 in the standard installation directory.

# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Grant Wickman

import json, urllib.request

prompt = (
    "Read AGENTS.md first and follow all instructions there.\n\n"
    "Follow the Version Design Orchestrator master prompt at "
    "C:\\Users\\grant\\tools\\auto-dev-mcp\\templates\\docs\\PROMPTS/design_version_prompt/000-master-prompt.md "
    "exactly, for project stoat-and-ferret, version v069. Treat v069 as authoritative - do not re-derive "
    "it from plan.md; use it directly.\n\n"
    "Output path: C:\\Users\\grant\\Documents\\projects\\auto-dev-projects\\stoat-and-ferret/comms/outbox/exploration/design-v069/\n\n"
    "Required output files:\n"
    "- README.md - final design summary\n"
    "- outcome.json - status and abort_reason per shared/outcome-json-schema.md\n\n"
    "Waiting for sub-explores: Do not poll get_exploration_status in a loop. Instead: (1) call start_exploration, "
    "(2) use the Monitor tool with a PowerShell Test-Path loop to watch for the sub-explore's README.md file, "
    "with timeout_ms set to 2 minutes (120000) for the first attempt. The monitor command is: "
    "while (-not (Test-Path '<outbox_path><results_folder>README.md')) { Start-Sleep 5 }; Write-Output 'README.md appeared'. "
    "If this first monitor times out, use get_exploration_status to check it is still alive and take action accordingly. "
    "If the sub-explore is still running, continue to monitor with timeout_ms set to 5 minutes (300000). "
    "When crafting prompts for sub-explores that will themselves launch sub-explores, include this same guidance "
    "in their prompt so the pattern propagates."
)

payload = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {
        "name": "start_exploration",
        "arguments": {
            "project": "stoat-and-ferret",
            "results_folder": "design-v069",
            "parent_exploration_id": "master-v069-orchestrator-1779905750102",
            "prompt": prompt,
            "autoDevToolKey": "26310c4a-747d-415a-bf05-6079193d573d"
        }
    }
}

data = json.dumps(payload).encode("utf-8")
req = urllib.request.Request(
    "http://127.0.0.1:8000/mcp?api_key=1BsQ251zN4Z9bFK1z0qgV6HPOXI-cBW5oVvnZGOuYYY",
    data=data,
    headers={"Content-Type": "application/json"}
)
with urllib.request.urlopen(req, timeout=30) as resp:
    print(resp.read().decode("utf-8"))

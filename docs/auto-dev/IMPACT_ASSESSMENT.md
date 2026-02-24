# Impact Assessment Checks

Project-specific design-time checks for stoat-and-ferret. These checks are executed during auto-dev Task 003 (version design) to catch recurring issue patterns before they reach implementation.

## Async Safety

### What to look for

Features that introduce or modify `subprocess.run`, `subprocess.call`, `subprocess.check_output`, or `time.sleep` inside files containing `async def`.

Grep patterns:
- `subprocess\.(run|call|check_output)` in files with `async def`
- `time\.sleep` in files with `async def`

### Why it matters

Blocking calls in an async context freeze the event loop, preventing concurrent request handling. All WebSocket heartbeats, background tasks, and concurrent API requests stall until the blocking call completes.

### Concrete example

In v009, ffprobe used `subprocess.run()` inside an async endpoint. This blocked all WebSocket heartbeats and concurrent API requests for the duration of the ffprobe call. Fixed in v010 by switching to `asyncio.create_subprocess_exec()`.

## Settings Documentation

### What to look for

Versions that add or modify fields in `src/stoat_ferret/api/settings.py` (the Pydantic BaseSettings class). If Settings fields change, verify `.env.example` is updated to document the new or changed variables.

### Why it matters

Missing `.env.example` entries cause confusing startup failures for new developers who don't know which environment variables to configure. Without documentation, developers must read the settings source code to discover required configuration.

### Concrete example

The project had 11 Settings fields across 9 versions without any `.env.example` file. New developers had to read `settings.py` source code to discover configuration variables. This was finally addressed in v011 with the creation of `.env.example`.

## Cross-Version Wiring Assumptions

### What to look for

Features that depend on behavior from prior versions — especially features that consume endpoints, WebSocket messages, or state structures introduced in earlier versions. When identified, list assumptions explicitly and verify they hold.

### Why it matters

Prior-version features may have bugs, incomplete implementations, or different behavior than assumed. Unverified assumptions cause runtime failures that are difficult to diagnose because the root cause is in a different version's implementation.

### Concrete example

The v010 progress bar feature assumed v004's per-file progress reporting worked correctly. It didn't — the progress data structure was incomplete. The progress bar displayed incorrect data until the underlying reporting was fixed.

## GUI Input Mechanisms

### What to look for

GUI features that accept user input — particularly paths, IDs, or other structured data. Verify the design specifies an appropriate input mechanism (browse dialog, dropdown, autocomplete) rather than defaulting to a plain text input.

### Why it matters

Text-only inputs for structured data are error-prone and create poor UX. Users must know exact values and type them correctly, leading to typos and frustration.

### Concrete example

The scan directory feature (v005-v010) used a plain text input for directory paths. Users had to type full paths manually with no validation or assistance. v011 added a directory browse button — this could have been caught at design time if an input mechanism check existed.

# Live System Validation Framework

## Purpose

Documentation that requires observable validation (curl examples, diagnostic commands, workflow sequences) must be validated against a running application instance. This framework establishes the process, removing ad-hoc validation as a blocker for documentation features.

**Reference**: v040 feature 003 discovered 5 endpoint path corrections during ad-hoc validation that design prose had not caught.

---

## Requirements

### Running Application Instance

The application must be running and responsive before validation begins.

#### Option 1: Docker Compose (if available)

```bash
cd stoat-and-ferret
docker-compose up -d
# Wait for services to be ready
sleep 5
curl http://localhost:8765/health/ready
```

#### Option 2: Local Development Server

```bash
cd stoat-and-ferret

# Install dependencies
uv sync

# Build Rust extension
cd rust/stoat_ferret_core
maturin develop  # MUST run from project root after
cd ../..

# Start server
uvicorn src.stoat_ferret.api.app:app --reload --port 8765

# In another terminal, verify startup:
curl http://localhost:8765/health/ready
# Expected: {"status": "ready"}
```

### Health Check Verification

All validation begins by confirming the application is responsive:

```bash
curl -s http://localhost:8765/health/ready | jq .status
# Expected output: "ready"
```

If health check fails, do not proceed with validation. Diagnose startup issue first.

---

## Validation Process for Documentation Examples

### Step 1: Identify Examples to Validate

For each curl command, workflow sequence, or diagnostic command in documentation:
1. Copy the command verbatim
2. Verify syntax (proper quoting, header format)
3. Identify the endpoint being tested
4. Note the expected response structure

### Step 2: Execute Against Running Application

```bash
# Example: Scan workflow
curl -X POST http://localhost:8765/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/video.mp4"}' 2>/dev/null | jq .

# Example: Get scan status
curl http://localhost:8765/api/v1/scan/scan-12345 2>/dev/null | jq .
```

### Step 3: Capture Actual Response

Record the full JSON response exactly as returned (with sensitive values redacted):

```json
{
  "id": "scan-12345",
  "status": "completed",
  "videos_found": 5,
  "errors": []
}
```

### Step 4: Compare Against Documentation

Check:
- Does the endpoint path match the documented path?
- Do response fields exist and have the documented names?
- Does response type match (string, number, array, object)?
- Are all documented error cases reproducible?

### Step 5: Document Divergences

If actual behavior differs from documentation:

**Option A: Documentation is Stale**
- Update documentation to match actual behavior
- Document the divergence reason (e.g., "API changed in v040 feature 003")
- Commit both changes together

**Option B: Implementation Doesn't Match Design**
- Flag as a design-implementation mismatch
- Do NOT merge documentation until implementation is fixed
- Document the gap in completion report

### Step 6: Evidence Checklist

For each documented workflow/example, include evidence:

```markdown
### Scan Workflow Validation

**Command**: `POST /api/v1/scan`
**Date Validated**: 2026-04-23
**Application Version**: v041-rc1
**Platform**: Ubuntu 22.04, Python 3.10

✅ Endpoint exists and responds with 200
✅ Response includes all documented fields
✅ Long-poll pattern (wait=true) works as documented
✅ Error case (invalid path) produces expected 422 response
```

---

## Validation Process for Diagnostic Commands

### Step 1: Identify Diagnostic Commands

Commands in troubleshooting guides, runbooks, or operational procedures must work when executed against the running system.

**Examples**:
- Health check: `curl http://localhost:8765/health/ready`
- Log location: `cat ~/.stoat-ferret/logs/app.log`
- Database check: `sqlite3 ~/.stoat-ferret/data.db ".tables"`
- Job queue depth: `curl http://localhost:8765/api/v1/system/state | jq '.jobs.queued'`

### Step 2: Execute in Running Environment

```bash
# Run the command as documented
curl http://localhost:8765/health/ready

# Capture output exactly
# {
#   "status": "ready",
#   "checks": {
#     "database": "ok",
#     "rust_core": "ok",
#     "filesystem": "ok"
#   }
# }
```

### Step 3: Verify Output Interpretation

For each diagnostic command, document:
- What the command checks
- What success looks like (output format, expected values)
- What failure looks like (error codes, error messages)
- How to interpret the output

**Example**:
```markdown
### Database Health Check

Command:
```bash
curl http://localhost:8765/health/ready | jq '.checks.database'
```

**Success Response**: `"ok"`

**Failure Response**: `"connection_error"` or `"timeout"`

**Next Steps**:
- If failing: Check database file exists at ~/.stoat-ferret/data.db
- If missing: Run migrations: `alembic upgrade head`
```

### Step 4: Evidence Checklist

```markdown
### Troubleshooting: Health Check Failure

**Diagnostic Command**: `curl http://localhost:8765/health/ready`
**Date Validated**: 2026-04-23
**Application Version**: v041-rc1

✅ Command syntax is valid (curl works, endpoint exists)
✅ Success case (running app): Returns 200 with status="ready"
✅ Failure case (stopped app): Returns 503 with status="unhealthy"
✅ Timeout case (slow app): Returns 504 after 30s timeout
```

---

## Response Payload Documentation

When documenting API responses, include:

### Required Fields

```markdown
### POST /api/v1/render Response

**Status**: 200 OK
**Content-Type**: application/json

Fields:
- `id` (string): Unique job identifier (example: `render-abc123def456`)
- `status` (string): One of `queued`, `running`, `completed`, `failed`
- `progress` (number): 0-100 (example: `45`)
- `output_path` (string, nullable): Path to rendered file or null if not ready
- `error_message` (string, nullable): Error details if status=failed
```

### Response Redaction Guidelines

Redact:
- Absolute file paths (replace with `/path/to/...`)
- UUIDs/IDs (replace with `abc123def456`)
- Timestamps (replace with `2026-04-23T10:00:00Z`)
- API keys/tokens (replace with `[REDACTED]`)

Keep:
- Field names and types
- Response structure
- Error codes
- Status values (e.g., "queued", "completed")

---

## Common Pitfalls

### Pitfall 1: Timeout Assumptions

Long-poll endpoints with `wait=true` may timeout after a default duration. Document:
- Default timeout (e.g., 60 seconds)
- How to set custom timeout (e.g., `wait=90`)
- What happens on timeout (e.g., returns current state with status indication)

### Pitfall 2: State Assumptions

Some workflows depend on prior state (job queues, database migrations). Document:
- Prerequisite state (e.g., "at least one video scanned")
- How to seed test data
- Behavior if prerequisites missing

### Pitfall 3: Transient Failures

Some operations may fail transiently (e.g., render jobs timing out, FFmpeg unavailable). Document:
- Transient vs. permanent failure indicators
- Retry strategy
- When to escalate to operations

### Pitfall 4: Platform Differences

Commands may behave differently on Windows/Mac/Linux. Document:
- Windows-specific notes (e.g., path separators, environment variables)
- Bash vs. PowerShell differences
- Docker vs. bare-metal differences

---

## Validation Before Merge

### Acceptance Criteria for Documentation Features

For BL-281 (API Usage Examples) and BL-282 (Operational Runbook):

- ✅ All curl commands have been executed against running application
- ✅ All responses have been captured and compared to documentation
- ✅ Any divergences have been resolved (docs updated or code fixed)
- ✅ All diagnostic commands have been tested against running system
- ✅ Evidence checklist completed for each workflow/command

### Code Review Checklist

Reviewers must verify:
- [ ] Validation framework has been followed
- [ ] Evidence checklists are complete
- [ ] No placeholder/assumed responses (all captured from actual runs)
- [ ] Sensitive data has been redacted
- [ ] Commands work on the documented platforms (Windows/Mac/Linux)

---

## Example: Complete Validation Report

```markdown
# API Usage Examples — Validation Report (v041 BL-281)

## Scan Workflow

### Command: POST /api/v1/scan

Execution Details:
- Date: 2026-04-23T10:15:00Z
- Environment: Local Ubuntu 22.04, Python 3.10
- Application Version: v041-rc1

Curl Command:
```bash
curl -X POST http://localhost:8765/api/v1/scan \
  -H "Content-Type: application/json" \
  -d '{"path": "/tmp/test-videos/sample.mp4"}'
```

Actual Response (2026-04-23T10:15:02Z):
```json
{
  "id": "scan-20260423-101502",
  "status": "in_progress",
  "videos_found": 0,
  "errors": []
}
```

Documented vs. Actual:
- ✅ Endpoint path matches: `/api/v1/scan`
- ✅ Status code 200 OK (as expected)
- ✅ Response fields all present and match documented types
- ✅ status value "in_progress" matches documented enum
- ⚠️ Actual response doesn't include `completed_at` field (not in design, OK to update docs)

---

## Polling Workflow

### Command: GET /api/v1/scan/{id}?wait=true

Execution Details:
- Date: 2026-04-23T10:15:02Z (continuation of scan workflow)
- Timeout: 60 seconds (default)

Curl Command:
```bash
curl "http://localhost:8765/api/v1/scan/scan-20260423-101502?wait=true"
```

Waiting... (response after 8 seconds):
```json
{
  "id": "scan-20260423-101502",
  "status": "completed",
  "videos_found": 3,
  "videos": [
    {"id": "vid-001", "duration_seconds": 120, "frame_rate": 30.0},
    {"id": "vid-002", "duration_seconds": 90, "frame_rate": 24.0},
    {"id": "vid-003", "duration_seconds": 150, "frame_rate": 60.0}
  ],
  "errors": []
}
```

Validation:
- ✅ Endpoint responds after object completes (8 seconds, within 60s timeout)
- ✅ All fields documented and present
- ✅ Video array matches documented structure
- ✅ Enum values match (status="completed")

---

## Validation Completed By

- Name: Claude Code
- Date: 2026-04-23
- Sign-off: All workflows validated, ready to merge
```

---

## Maintenance

This framework should be updated when:
- New endpoint patterns emerge
- CI infrastructure changes (automated validation possible)
- Transient failure patterns change
- Platform-specific behaviors are discovered

Review and refresh annually or per major version.

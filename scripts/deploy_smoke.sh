#!/bin/bash
# Post-deployment smoke test for stoat-and-ferret.
#
# Polls /health/ready until the server responds or the timeout expires,
# then verifies /api/v1/version returns valid JSON with an app_version field.
#
# FFmpeg is non-critical for production readiness.
# The /health/ready endpoint returns HTTP 200 with status="degraded"
# when FFmpeg is unavailable. This is expected behavior for containers
# deployed without FFmpeg.
#
# Usage:
#   ./scripts/deploy_smoke.sh
#   STOAT_HOST=myhost STOAT_PORT=9000 ./scripts/deploy_smoke.sh
#
# Environment variables:
#   STOAT_HOST  - Host to connect to (default: localhost)
#   STOAT_PORT  - Port to connect to (default: 8765)
#
# Exit codes:
#   0 - Smoke test passed
#   1 - Smoke test failed (readiness timeout or version check failure)

set -euo pipefail

STOAT_HOST="${STOAT_HOST:-localhost}"
STOAT_PORT="${STOAT_PORT:-8765}"
MAX_WAIT=60
INTERVAL=2

BASE_URL="http://${STOAT_HOST}:${STOAT_PORT}"
echo "Waiting for ${BASE_URL} to be ready (max ${MAX_WAIT}s)..."

# Poll /health/ready for readiness (HTTP 200 with status=ok or status=degraded is success)
ELAPSED=0
while [ "${ELAPSED}" -lt "${MAX_WAIT}" ]; do
    if curl -f -s "${BASE_URL}/health/ready" > /dev/null 2>&1; then
        echo "✓ /health/ready returned 200"
        break
    fi
    echo "  Waiting... (${ELAPSED}/${MAX_WAIT}s)"
    sleep "${INTERVAL}"
    ELAPSED=$((ELAPSED + INTERVAL))
done

if [ "${ELAPSED}" -ge "${MAX_WAIT}" ]; then
    echo "✗ /health/ready never returned 200 (timeout after ${MAX_WAIT}s)"
    exit 1
fi

# Verify /api/v1/version returns valid JSON with app_version
echo "Verifying /api/v1/version..."
VERSION_RESPONSE=$(curl -s "${BASE_URL}/api/v1/version")
if echo "${VERSION_RESPONSE}" | grep -q '"app_version"'; then
    echo "✓ /api/v1/version returned valid JSON with app_version"
else
    echo "✗ /api/v1/version did not return expected schema"
    echo "Response: ${VERSION_RESPONSE}"
    exit 1
fi

echo "✓ Deployment smoke test passed"
exit 0

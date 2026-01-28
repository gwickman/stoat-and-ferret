# Implementation Plan: Health Endpoints

## Step 1: Create Health Router
Create `src/stoat_ferret/api/routers/health.py`:

```python
"""Health check endpoints."""

import shutil
import subprocess
import time
from typing import Any

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def liveness() -> dict[str, str]:
    """Liveness probe - server is running."""
    return {"status": "ok"}


@router.get("/ready")
async def readiness(request: Request) -> JSONResponse:
    """Readiness probe - all dependencies healthy."""
    checks: dict[str, dict[str, Any]] = {}
    all_healthy = True

    # Database check
    db_check = await _check_database(request)
    checks["database"] = db_check
    if db_check["status"] != "ok":
        all_healthy = False

    # FFmpeg check
    ffmpeg_check = _check_ffmpeg()
    checks["ffmpeg"] = ffmpeg_check
    if ffmpeg_check["status"] != "ok":
        all_healthy = False

    response = {"status": "ok" if all_healthy else "degraded", "checks": checks}
    status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

    return JSONResponse(content=response, status_code=status_code)


async def _check_database(request: Request) -> dict[str, Any]:
    """Check database connectivity."""
    try:
        start = time.perf_counter()
        cursor = await request.app.state.db.execute("SELECT 1")
        await cursor.fetchone()
        latency_ms = (time.perf_counter() - start) * 1000
        return {"status": "ok", "latency_ms": round(latency_ms, 2)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def _check_ffmpeg() -> dict[str, Any]:
    """Check FFmpeg availability."""
    ffmpeg_path = shutil.which("ffmpeg")
    if not ffmpeg_path:
        return {"status": "error", "error": "ffmpeg not found in PATH"}

    try:
        result = subprocess.run(
            ["ffmpeg", "-version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        # Parse version from first line
        version_line = result.stdout.split("\n")[0]
        version = version_line.split()[2] if len(version_line.split()) > 2 else "unknown"
        return {"status": "ok", "version": version}
    except Exception as e:
        return {"status": "error", "error": str(e)}
```

## Step 2: Register Router
Update `src/stoat_ferret/api/app.py`:

```python
from stoat_ferret.api.routers import health

def create_app() -> FastAPI:
    # ... existing code
    
    app.include_router(health.router)
    
    return app
```

## Step 3: Add Tests
Create `tests/test_api/test_health.py`:

```python
"""Tests for health endpoints."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.api
def test_liveness(client: TestClient):
    """Liveness endpoint returns ok."""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.api
def test_readiness_healthy(client: TestClient):
    """Readiness returns 200 when all checks pass."""
    response = client.get("/health/ready")
    # May be 200 or 503 depending on FFmpeg availability
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert "database" in data["checks"]
    assert "ffmpeg" in data["checks"]
```

## Verification
- `curl http://localhost:8000/health/live` returns `{"status": "ok"}`
- `curl http://localhost:8000/health/ready` returns checks
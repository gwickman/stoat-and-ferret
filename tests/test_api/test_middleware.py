"""Tests for middleware stack."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from stoat_ferret.api.middleware.correlation import (
    correlation_id_var,
    get_correlation_id,
)


class TestCorrelationIdMiddleware:
    """Tests for CorrelationIdMiddleware."""

    @pytest.mark.api
    def test_correlation_id_generated(self, client: TestClient) -> None:
        """Requests without correlation ID get one generated."""
        response = client.get("/health/live")
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        # Should be a valid UUID (36 chars with hyphens)
        assert len(response.headers["X-Correlation-ID"]) == 36

    @pytest.mark.api
    def test_correlation_id_preserved(self, client: TestClient) -> None:
        """Requests with correlation ID have it preserved."""
        test_id = "test-correlation-id-12345"
        response = client.get(
            "/health/live",
            headers={"X-Correlation-ID": test_id},
        )
        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == test_id

    @pytest.mark.api
    def test_correlation_id_unique_per_request(self, client: TestClient) -> None:
        """Each request gets a unique correlation ID if not provided."""
        response1 = client.get("/health/live")
        response2 = client.get("/health/live")

        id1 = response1.headers["X-Correlation-ID"]
        id2 = response2.headers["X-Correlation-ID"]

        assert id1 != id2


class TestGetCorrelationId:
    """Tests for get_correlation_id helper."""

    def test_get_correlation_id_default(self) -> None:
        """Returns empty string when not set."""
        # Reset to default
        correlation_id_var.set("")
        assert get_correlation_id() == ""

    def test_get_correlation_id_returns_set_value(self) -> None:
        """Returns the value that was set."""
        correlation_id_var.set("test-123")
        assert get_correlation_id() == "test-123"


class TestMetricsMiddleware:
    """Tests for MetricsMiddleware."""

    @pytest.mark.api
    def test_metrics_endpoint_exists(self, client: TestClient) -> None:
        """Metrics endpoint returns 200."""
        response = client.get("/metrics")
        assert response.status_code == 200

    @pytest.mark.api
    def test_metrics_endpoint_returns_prometheus_format(self, client: TestClient) -> None:
        """Metrics endpoint returns Prometheus format."""
        # Make a request first to ensure metrics are recorded
        client.get("/health/live")

        response = client.get("/metrics")
        assert response.status_code == 200
        # Check for Prometheus metric names
        assert "http_requests_total" in response.text

    @pytest.mark.api
    def test_metrics_records_request_count(self, client: TestClient) -> None:
        """Request count metric is recorded."""
        # Make a known request
        client.get("/health/live")

        response = client.get("/metrics")
        # Should contain a counter entry for /health/live
        assert "http_requests_total{" in response.text
        assert '"/health/live"' in response.text

    @pytest.mark.api
    def test_metrics_records_duration(self, client: TestClient) -> None:
        """Request duration histogram is recorded."""
        client.get("/health/live")

        response = client.get("/metrics")
        assert "http_request_duration_seconds" in response.text

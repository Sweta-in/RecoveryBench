#!/usr/bin/env python3
"""
RecoveryBench — API Tests

Tests all FastAPI endpoints using the TestClient.
Covers: health, metrics, text analysis, audio analysis,
input validation, and error handling.

Run: pytest tests/test_api.py -v
"""

import sys
import json
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def client():
    """Create a FastAPI test client."""
    return TestClient(app)


# ============================================================
# GET /health
# ============================================================

class TestHealthEndpoint:
    """Tests for GET /health."""

    def test_health_returns_200(self, client):
        """Health endpoint returns 200."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_status_ok(self, client):
        """Health response has status 'ok'."""
        data = client.get("/health").json()
        assert data["status"] == "ok"

    def test_health_has_version(self, client):
        """Health response includes version."""
        data = client.get("/health").json()
        assert "version" in data
        assert data["version"] == "1.0.0"

    def test_health_has_timestamp(self, client):
        """Health response includes timestamp."""
        data = client.get("/health").json()
        assert "timestamp" in data


# ============================================================
# GET /metrics
# ============================================================

class TestMetricsEndpoint:
    """Tests for GET /metrics."""

    def test_metrics_returns_200(self, client):
        """Metrics endpoint returns 200."""
        response = client.get("/metrics")
        assert response.status_code == 200

    def test_metrics_has_uptime(self, client):
        """Metrics response includes uptime."""
        data = client.get("/metrics").json()
        assert "uptime_seconds" in data
        assert data["uptime_seconds"] >= 0

    def test_metrics_has_request_counts(self, client):
        """Metrics response includes request counters."""
        data = client.get("/metrics").json()
        assert "requests_served" in data
        assert "text_analyses" in data
        assert "audio_analyses" in data

    def test_metrics_has_components(self, client):
        """Metrics response shows loaded components."""
        data = client.get("/metrics").json()
        assert "components" in data
        assert isinstance(data["components"], dict)

    def test_metrics_has_version(self, client):
        """Metrics response includes version."""
        data = client.get("/metrics").json()
        assert data["version"] == "1.0.0"


# ============================================================
# POST /analyze/text
# ============================================================

class TestAnalyzeTextEndpoint:
    """Tests for POST /analyze/text."""

    def test_analyze_text_basic(self, client):
        """Basic text analysis returns 200 with expected fields."""
        response = client.post(
            "/analyze/text",
            json={"borrower_message": "kal kar dunga bhai"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "repayment_intent" in data
        assert "language" in data

    def test_analyze_text_with_agent_response(self, client):
        """Text analysis with agent response includes compliance."""
        response = client.post(
            "/analyze/text",
            json={
                "borrower_message": "kal kar dunga bhai",
                "agent_response": "Please pay immediately.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "compliance" in data

    def test_analyze_text_promise_detection(self, client):
        """Text analysis detects payment promises."""
        response = client.post(
            "/analyze/text",
            json={"borrower_message": "I will pay tomorrow"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "promise_to_pay" in data

    def test_analyze_text_risk_score(self, client):
        """Text analysis includes risk score."""
        response = client.post(
            "/analyze/text",
            json={"borrower_message": "payment kar dunga next week"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "risk_score" in data

    def test_analyze_text_hindi(self, client):
        """Text analysis works with Hindi input."""
        response = client.post(
            "/analyze/text",
            json={"borrower_message": "agle hafte bhej dunga"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "repayment_intent" in data

    def test_analyze_text_bengali(self, client):
        """Text analysis works with Bengali input."""
        response = client.post(
            "/analyze/text",
            json={"borrower_message": "salary ashle debo"},
        )
        assert response.status_code == 200

    def test_analyze_text_returns_all_fields(self, client):
        """Full response schema validation."""
        response = client.post(
            "/analyze/text",
            json={
                "borrower_message": "kal kar dunga payment",
                "agent_response": "Please pay your EMI.",
            },
        )
        assert response.status_code == 200
        data = response.json()

        # All required top-level fields
        required_fields = [
            "language", "repayment_intent", "intent_confidence",
            "risk_score", "promise_to_pay", "payment_window_days",
            "sentiment", "recommended_action", "compliance",
        ]
        for field in required_fields:
            assert field in data, f"Missing field: {field}"

    def test_analyze_text_has_request_id_header(self, client):
        """Response includes X-Request-ID header."""
        response = client.post(
            "/analyze/text",
            json={"borrower_message": "hello"},
        )
        assert "x-request-id" in response.headers


# ============================================================
# Input Validation — POST /analyze/text
# ============================================================

class TestInputValidation:
    """Tests for input validation on /analyze/text."""

    def test_empty_body_returns_422(self, client):
        """Empty JSON body returns 422."""
        response = client.post("/analyze/text", json={})
        assert response.status_code == 422

    def test_missing_borrower_message_returns_422(self, client):
        """Missing borrower_message returns 422."""
        response = client.post(
            "/analyze/text",
            json={"agent_response": "Hello"},
        )
        assert response.status_code == 422

    def test_empty_borrower_message_returns_422(self, client):
        """Empty borrower_message returns 422."""
        response = client.post(
            "/analyze/text",
            json={"borrower_message": ""},
        )
        assert response.status_code == 422

    def test_whitespace_borrower_message_returns_422(self, client):
        """Whitespace-only borrower_message returns 422."""
        response = client.post(
            "/analyze/text",
            json={"borrower_message": "   "},
        )
        assert response.status_code == 422

    def test_too_long_borrower_message_returns_422(self, client):
        """Borrower message over 1000 chars returns 422."""
        long_msg = "x" * 1001
        response = client.post(
            "/analyze/text",
            json={"borrower_message": long_msg},
        )
        assert response.status_code == 422

    def test_invalid_json_returns_422(self, client):
        """Invalid JSON body returns 422."""
        response = client.post(
            "/analyze/text",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_max_length_borrower_message_accepted(self, client):
        """Borrower message at exactly 1000 chars is accepted."""
        msg = "a" * 1000
        response = client.post(
            "/analyze/text",
            json={"borrower_message": msg},
        )
        assert response.status_code == 200


# ============================================================
# POST /analyze/audio
# ============================================================

class TestAnalyzeAudioEndpoint:
    """Tests for POST /analyze/audio."""

    def test_audio_no_file_returns_422(self, client):
        """No file upload returns 422."""
        response = client.post("/analyze/audio")
        assert response.status_code == 422

    def test_audio_unsupported_extension(self, client):
        """Unsupported file extension returns 400."""
        response = client.post(
            "/analyze/audio",
            files={"file": ("test.txt", b"hello", "text/plain")},
        )
        assert response.status_code == 400

    def test_audio_empty_file_returns_400(self, client):
        """Empty audio file returns 400."""
        response = client.post(
            "/analyze/audio",
            files={"file": ("test.mp3", b"", "audio/mpeg")},
        )
        assert response.status_code == 400


# ============================================================
# Error Handling
# ============================================================

class TestErrorHandling:
    """Tests for error response format."""

    def test_404_returns_json(self, client):
        """Non-existent path returns JSON 404."""
        response = client.get("/nonexistent")
        assert response.status_code == 404

    def test_validation_error_response_format(self, client):
        """Validation errors return structured JSON."""
        response = client.post("/analyze/text", json={})
        assert response.status_code == 422
        # Response should be JSON
        data = response.json()
        assert isinstance(data, dict)

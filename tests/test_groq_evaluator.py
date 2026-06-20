#!/usr/bin/env python3
"""
RecoveryBench — Groq Evaluator Backend Tests

Tests for the Groq integration in pipeline/evaluator.py, covering:
  - Backend detection and selection
  - Groq client initialization
  - Fallback behavior when Groq is unavailable
  - API endpoint evaluator override (?evaluator=groq)
  - Cost reporting for Groq backend
  - Integration with the rule-based fallback chain

Run: pytest tests/test_groq_evaluator.py -v
"""

import sys
import os
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.evaluator import AgentEvaluator, RUBRIC_WEIGHTS, RUBRIC_NAMES, BACKENDS


# ─── Backend Discovery ───────────────────────────────────────────────

class TestGroqBackendDiscovery:
    """Tests that Groq is correctly discovered in the backend priority chain."""

    def test_groq_in_backends_list(self):
        """'groq' must appear in the BACKENDS priority list."""
        assert "groq" in BACKENDS

    def test_groq_after_claude_in_priority(self):
        """Groq should be tried after Claude (position 3) in the default chain."""
        assert BACKENDS.index("groq") > BACKENDS.index("claude")

    def test_groq_before_rule_based_in_priority(self):
        """Groq should be tried before rule_based (last resort)."""
        assert BACKENDS.index("groq") < BACKENDS.index("rule_based")


# ─── Groq Availability Check ────────────────────────────────────────

class TestGroqAvailabilityCheck:
    """Tests for _check_groq() method."""

    def test_no_groq_api_key_returns_false(self):
        """Without GROQ_API_KEY env var, _check_groq should return False."""
        evaluator = AgentEvaluator.__new__(AgentEvaluator)
        evaluator.backend = None
        evaluator.backend_model = None
        with patch.dict(os.environ, {}, clear=True):
            # Remove GROQ_API_KEY if it exists
            os.environ.pop("GROQ_API_KEY", None)
            result = evaluator._check_groq()
        assert result is False

    def test_groq_import_error_returns_false(self):
        """If 'groq' package is not installed, _check_groq should return False."""
        evaluator = AgentEvaluator.__new__(AgentEvaluator)
        evaluator.backend = None
        evaluator.backend_model = None
        with patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}):
            with patch.dict("sys.modules", {"groq": None}):
                result = evaluator._check_groq()
        assert result is False

    @patch("pipeline.evaluator.os.environ.get")
    def test_groq_with_key_and_package_returns_true(self, mock_env_get):
        """With GROQ_API_KEY set and groq package available, should return True."""
        mock_env_get.side_effect = lambda key, *args: "test-key-123" if key == "GROQ_API_KEY" else None
        mock_groq_module = MagicMock()
        mock_groq_client = MagicMock()
        mock_groq_module.Groq.return_value = mock_groq_client

        evaluator = AgentEvaluator.__new__(AgentEvaluator)
        evaluator.backend = None
        evaluator.backend_model = None

        with patch.dict("sys.modules", {"groq": mock_groq_module}):
            with patch("builtins.__import__", side_effect=lambda name, *a, **kw: mock_groq_module if name == "groq" else __import__(name, *a, **kw)):
                # Directly call the method with the env var set
                with patch.dict(os.environ, {"GROQ_API_KEY": "test-key-123"}):
                    result = evaluator._check_groq()

        assert result is True
        assert evaluator.backend == "groq"
        assert evaluator.backend_model == "llama-3.1-8b-instant"


# ─── Groq Evaluation Flow ───────────────────────────────────────────

class TestGroqEvaluationFlow:
    """Tests for the Groq evaluation path."""

    def test_evaluate_dispatches_to_groq_when_backend_is_groq(self):
        """When backend='groq', evaluate() should call _evaluate_groq."""
        evaluator = AgentEvaluator.__new__(AgentEvaluator)
        evaluator.backend = "groq"
        evaluator.backend_model = "llama-3.1-8b-instant"
        evaluator._api_call_count = 0
        evaluator._total_cost = 0.0
        evaluator._prompt_template = "test {borrower_message} {intent} {confidence} {agent_response}"

        # Mock _evaluate_groq to verify it's called
        mock_result = {
            "intent_accuracy": 7.0,
            "tone_score": 8.0,
            "compliance_score": 9.0,
            "escalation_score": 6.0,
            "overall_score": 7.65,
            "suggested_improvement": "Test suggestion",
        }
        evaluator._evaluate_groq = MagicMock(return_value=mock_result)

        result = evaluator.evaluate(
            borrower_message="kal kar dunga",
            intent="LIKELY_PAY",
            confidence=0.85,
            agent_response="Thank you.",
        )

        evaluator._evaluate_groq.assert_called_once()
        assert result == mock_result

    def test_groq_evaluation_falls_back_on_error(self):
        """If Groq API call fails, should fall back to rule-based."""
        evaluator = AgentEvaluator.__new__(AgentEvaluator)
        evaluator.backend = "groq"
        evaluator.backend_model = "llama-3.1-8b-instant"
        evaluator._api_call_count = 0
        evaluator._total_cost = 0.0
        evaluator._prompt_template = "test {borrower_message} {intent} {confidence:.2f} {agent_response}"

        # Mock Groq client to raise an exception
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API rate limit")
        evaluator._groq_client = mock_client

        result = evaluator._evaluate_groq(
            borrower_message="test message",
            intent="LIKELY_PAY",
            confidence=0.85,
            agent_response="Please pay.",
        )

        # Should still return valid result (from rule-based fallback)
        assert "overall_score" in result
        assert "compliance_score" in result
        assert 0 <= result["overall_score"] <= 10


# ─── Groq Cost Reporting ────────────────────────────────────────────

class TestGroqCostReporting:
    """Tests for Groq cost/stats reporting."""

    def test_groq_cost_per_1000_is_free(self):
        """Groq free tier should report $0.00 cost."""
        evaluator = AgentEvaluator.__new__(AgentEvaluator)
        evaluator.backend = "groq"
        evaluator.backend_model = "llama-3.1-8b-instant"
        evaluator._api_call_count = 0
        evaluator._total_cost = 0.0

        cost = evaluator.get_cost_per_1000()
        assert "$0.00" in cost
        assert "free" in cost.lower() or "Groq" in cost

    def test_groq_stats_include_backend_info(self):
        """get_stats() should report groq backend correctly."""
        evaluator = AgentEvaluator.__new__(AgentEvaluator)
        evaluator.backend = "groq"
        evaluator.backend_model = "llama-3.1-8b-instant"
        evaluator._api_call_count = 5
        evaluator._total_cost = 0.0

        stats = evaluator.get_stats()
        assert stats["backend"] == "groq"
        assert stats["backend_model"] == "llama-3.1-8b-instant"
        assert stats["api_calls"] == 5

    def test_groq_repr_includes_groq(self):
        """repr() should mention groq backend."""
        evaluator = AgentEvaluator.__new__(AgentEvaluator)
        evaluator.backend = "groq"
        evaluator.backend_model = "llama-3.1-8b-instant"
        evaluator._api_call_count = 0

        r = repr(evaluator)
        assert "groq" in r


# ─── API Evaluator Override ──────────────────────────────────────────

class TestAPIEvaluatorOverride:
    """Tests for the ?evaluator=groq query param on POST /analyze/text."""

    @pytest.fixture
    def client(self):
        """Create a FastAPI test client."""
        from fastapi.testclient import TestClient
        from api.main import app
        return TestClient(app)

    def test_evaluator_param_groq_accepted(self, client):
        """POST /analyze/text?evaluator=groq should not return 422."""
        response = client.post(
            "/analyze/text?evaluator=groq",
            json={"borrower_message": "kal kar dunga bhai"},
        )
        # Should succeed (200) regardless of whether Groq is actually available
        # — the API falls back gracefully
        assert response.status_code == 200

    def test_evaluator_param_rule_based_accepted(self, client):
        """POST /analyze/text?evaluator=rule_based should work."""
        response = client.post(
            "/analyze/text?evaluator=rule_based",
            json={
                "borrower_message": "kal kar dunga bhai",
                "agent_response": "Please pay immediately.",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "repayment_intent" in data

    def test_evaluator_param_none_uses_default(self, client):
        """POST /analyze/text without evaluator param uses default chain."""
        response = client.post(
            "/analyze/text",
            json={"borrower_message": "kal kar dunga bhai"},
        )
        assert response.status_code == 200


# ─── CORS Headers ────────────────────────────────────────────────────

class TestCORSHeaders:
    """Tests that CORS middleware is active and permissive."""

    @pytest.fixture
    def client(self):
        """Create a FastAPI test client."""
        from fastapi.testclient import TestClient
        from api.main import app
        return TestClient(app)

    def test_cors_allows_any_origin(self, client):
        """Preflight request with any origin should return Access-Control-Allow-Origin."""
        response = client.options(
            "/analyze/text",
            headers={
                "Origin": "http://localhost:5500",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "Content-Type",
            },
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_on_get_health(self, client):
        """GET /health with Origin header should return CORS headers."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:5500"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

    def test_cors_on_post_analyze(self, client):
        """POST /analyze/text with Origin header should return CORS headers."""
        response = client.post(
            "/analyze/text",
            json={"borrower_message": "test"},
            headers={"Origin": "http://localhost:5500"},
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers

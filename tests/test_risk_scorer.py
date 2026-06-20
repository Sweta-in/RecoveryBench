#!/usr/bin/env python3
"""
RecoveryBench — Risk Scorer Tests

Tests:
  - Model trains and loads without error
  - Score output is in [0, 1] range
  - Ordering check: LIKELY_PAY < NEEDS_REMINDER < VAGUE < DISPUTE < HIGH_RISK
  - Risk bands map correctly
  - Feature extraction helper works
  - Batch scoring works
  - Edge cases: extreme inputs, missing keys
"""

import sys
from pathlib import Path

# Ensure project root is on path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import pytest
import numpy as np


@pytest.fixture(scope="module")
def scorer():
    """Create a RiskScorer instance (trains model if needed)."""
    from pipeline.risk_scorer import RiskScorer
    return RiskScorer()


# ============================================================
# Basic functionality
# ============================================================

class TestRiskScorerBasics:
    """Basic initialization and scoring tests."""

    def test_init(self, scorer):
        """Scorer initializes without error."""
        assert scorer is not None
        assert scorer._model is not None

    def test_model_file_exists(self):
        """Model file is saved to disk."""
        model_path = project_root / "models" / "risk_scorer" / "xgb_model.json"
        assert model_path.exists(), f"Model file not found at {model_path}"

    def test_feature_importance_file(self):
        """Feature importance JSON is saved."""
        path = project_root / "models" / "risk_scorer" / "feature_importance.json"
        assert path.exists()

    def test_score_returns_float(self, scorer):
        """Score returns a float."""
        score = scorer.score({
            "intent": "VAGUE",
            "has_promise": False,
            "payment_window_days": 0,
            "message_length": 10,
            "exclamation_count": 0,
            "question_count": 0,
            "caps_ratio": 0.0,
            "dispute_keywords": 0,
            "hostile_keywords": 0,
        })
        assert isinstance(score, float)

    def test_score_in_range(self, scorer):
        """Score is between 0 and 1."""
        score = scorer.score({
            "intent": "LIKELY_PAY",
            "has_promise": True,
            "payment_window_days": 7,
            "message_length": 40,
            "exclamation_count": 0,
            "question_count": 0,
            "caps_ratio": 0.05,
            "dispute_keywords": 0,
            "hostile_keywords": 0,
        })
        assert 0.0 <= score <= 1.0


# ============================================================
# Ordering checks (critical requirement)
# ============================================================

class TestRiskOrdering:
    """Verify risk ordering: LIKELY_PAY < NEEDS_REMINDER < VAGUE < DISPUTE < HIGH_RISK."""

    @pytest.fixture
    def scores(self, scorer):
        """Score all 5 intent classes with representative features."""
        cases = {
            "LIKELY_PAY": {
                "intent": "LIKELY_PAY",
                "has_promise": True,
                "payment_window_days": 7,
                "message_length": 40,
                "exclamation_count": 0,
                "question_count": 0,
                "caps_ratio": 0.05,
                "dispute_keywords": 0,
                "hostile_keywords": 0,
            },
            "NEEDS_REMINDER": {
                "intent": "NEEDS_REMINDER",
                "has_promise": False,
                "payment_window_days": 0,
                "message_length": 20,
                "exclamation_count": 0,
                "question_count": 1,
                "caps_ratio": 0.0,
                "dispute_keywords": 0,
                "hostile_keywords": 0,
            },
            "VAGUE": {
                "intent": "VAGUE",
                "has_promise": False,
                "payment_window_days": 0,
                "message_length": 5,
                "exclamation_count": 0,
                "question_count": 0,
                "caps_ratio": 0.0,
                "dispute_keywords": 0,
                "hostile_keywords": 0,
            },
            "DISPUTE": {
                "intent": "DISPUTE",
                "has_promise": False,
                "payment_window_days": 0,
                "message_length": 60,
                "exclamation_count": 1,
                "question_count": 1,
                "caps_ratio": 0.1,
                "dispute_keywords": 2,
                "hostile_keywords": 0,
            },
            "HIGH_RISK": {
                "intent": "HIGH_RISK",
                "has_promise": False,
                "payment_window_days": 0,
                "message_length": 80,
                "exclamation_count": 3,
                "question_count": 0,
                "caps_ratio": 0.4,
                "dispute_keywords": 0,
                "hostile_keywords": 2,
            },
        }
        return {k: scorer.score(v) for k, v in cases.items()}

    def test_likely_pay_lowest(self, scores):
        """LIKELY_PAY has lowest risk."""
        assert scores["LIKELY_PAY"] < scores["NEEDS_REMINDER"]

    def test_needs_reminder_below_vague(self, scores):
        """NEEDS_REMINDER < VAGUE."""
        assert scores["NEEDS_REMINDER"] < scores["VAGUE"]

    def test_vague_below_dispute(self, scores):
        """VAGUE < DISPUTE."""
        assert scores["VAGUE"] < scores["DISPUTE"]

    def test_dispute_below_high_risk(self, scores):
        """DISPUTE < HIGH_RISK."""
        assert scores["DISPUTE"] < scores["HIGH_RISK"]

    def test_full_ordering(self, scores):
        """Full ordering: LIKELY_PAY < NEEDS_REMINDER < VAGUE < DISPUTE < HIGH_RISK."""
        assert (
            scores["LIKELY_PAY"]
            < scores["NEEDS_REMINDER"]
            < scores["VAGUE"]
            < scores["DISPUTE"]
            < scores["HIGH_RISK"]
        ), f"Ordering violated: {scores}"

    def test_likely_pay_below_half(self, scores):
        """LIKELY_PAY should score below 0.5."""
        assert scores["LIKELY_PAY"] < 0.5

    def test_high_risk_above_half(self, scores):
        """HIGH_RISK should score above 0.5."""
        assert scores["HIGH_RISK"] > 0.5


# ============================================================
# Risk band mapping
# ============================================================

class TestRiskBands:
    """Risk band classification tests."""

    def test_low_band(self, scorer):
        """Score 0.15 is 'low'."""
        assert scorer.get_risk_band(0.15) == "low"

    def test_medium_band(self, scorer):
        """Score 0.45 is 'medium'."""
        assert scorer.get_risk_band(0.45) == "medium"

    def test_high_band(self, scorer):
        """Score 0.70 is 'high'."""
        assert scorer.get_risk_band(0.70) == "high"

    def test_critical_band(self, scorer):
        """Score 0.90 is 'critical'."""
        assert scorer.get_risk_band(0.90) == "critical"

    def test_boundary_low_medium(self, scorer):
        """Score 0.3 is 'medium' (boundary)."""
        assert scorer.get_risk_band(0.3) == "medium"

    def test_boundary_medium_high(self, scorer):
        """Score 0.6 is 'high' (boundary)."""
        assert scorer.get_risk_band(0.6) == "high"

    def test_boundary_high_critical(self, scorer):
        """Score 0.8 is 'critical' (boundary)."""
        assert scorer.get_risk_band(0.8) == "critical"


# ============================================================
# Feature extraction helper
# ============================================================

class TestFeatureExtraction:
    """Test the static helper for extracting features from text."""

    def test_extract_basic(self):
        """Extract features from a simple message."""
        from pipeline.risk_scorer import RiskScorer

        features = RiskScorer.extract_features_from_text(
            text="kal kar dunga payment!!!",
            intent="LIKELY_PAY",
            promise_result={"promise_to_pay": True, "payment_window_days": 1},
        )
        assert features["intent"] == "LIKELY_PAY"
        assert features["has_promise"] is True
        assert features["payment_window_days"] == 1
        assert features["exclamation_count"] == 3
        assert features["message_length"] == len("kal kar dunga payment!!!")

    def test_extract_hostile(self):
        """Extract features from a hostile message."""
        from pipeline.risk_scorer import RiskScorer

        features = RiskScorer.extract_features_from_text(
            text="I will report to police and call my lawyer",
            intent="HIGH_RISK",
            promise_result={"promise_to_pay": False, "payment_window_days": None},
        )
        assert features["hostile_keywords"] >= 2  # "police" + "lawyer"
        assert features["has_promise"] is False

    def test_extract_no_promise(self):
        """No promise result produces 0 window."""
        from pipeline.risk_scorer import RiskScorer

        features = RiskScorer.extract_features_from_text(
            text="ok",
            intent="VAGUE",
            promise_result={"promise_to_pay": False, "payment_window_days": None},
        )
        assert features["payment_window_days"] == 0


# ============================================================
# Batch scoring
# ============================================================

class TestBatchScoring:
    """Test batch scoring."""

    def test_batch_returns_list(self, scorer):
        """Batch scoring returns a list of scores."""
        features_list = [
            {
                "intent": "LIKELY_PAY", "has_promise": True,
                "payment_window_days": 1, "message_length": 30,
                "exclamation_count": 0, "question_count": 0,
                "caps_ratio": 0.0, "dispute_keywords": 0, "hostile_keywords": 0,
            },
            {
                "intent": "HIGH_RISK", "has_promise": False,
                "payment_window_days": 0, "message_length": 60,
                "exclamation_count": 2, "question_count": 0,
                "caps_ratio": 0.3, "dispute_keywords": 0, "hostile_keywords": 1,
            },
        ]
        scores = scorer.score_batch(features_list)
        assert len(scores) == 2
        assert all(0.0 <= s <= 1.0 for s in scores)
        assert scores[0] < scores[1]  # LIKELY_PAY < HIGH_RISK


# ============================================================
# Edge cases
# ============================================================

class TestEdgeCases:
    """Edge cases and robustness tests."""

    def test_unknown_intent(self, scorer):
        """Unknown intent defaults to VAGUE encoding."""
        score = scorer.score({
            "intent": "NONEXISTENT_CLASS",
            "has_promise": False,
            "payment_window_days": 0,
            "message_length": 10,
            "exclamation_count": 0,
            "question_count": 0,
            "caps_ratio": 0.0,
            "dispute_keywords": 0,
            "hostile_keywords": 0,
        })
        assert 0.0 <= score <= 1.0

    def test_zero_length_message(self, scorer):
        """Zero-length message doesn't crash."""
        score = scorer.score({
            "intent": "VAGUE",
            "has_promise": False,
            "payment_window_days": 0,
            "message_length": 0,
            "exclamation_count": 0,
            "question_count": 0,
            "caps_ratio": 0.0,
            "dispute_keywords": 0,
            "hostile_keywords": 0,
        })
        assert 0.0 <= score <= 1.0

    def test_extreme_hostile(self, scorer):
        """Extremely hostile features should produce high score."""
        score = scorer.score({
            "intent": "HIGH_RISK",
            "has_promise": False,
            "payment_window_days": 0,
            "message_length": 200,
            "exclamation_count": 10,
            "question_count": 0,
            "caps_ratio": 0.8,
            "dispute_keywords": 3,
            "hostile_keywords": 5,
        })
        assert score > 0.5

    def test_window_capped_at_90(self, scorer):
        """Large payment window is handled without error."""
        score = scorer.score({
            "intent": "LIKELY_PAY",
            "has_promise": True,
            "payment_window_days": 365,
            "message_length": 50,
            "exclamation_count": 0,
            "question_count": 0,
            "caps_ratio": 0.0,
            "dispute_keywords": 0,
            "hostile_keywords": 0,
        })
        assert 0.0 <= score <= 1.0

    def test_feature_importance_has_all_features(self, scorer):
        """Feature importance dict has all 9 features."""
        importance = scorer.get_feature_importance()
        assert len(importance) == 9
        for feat in [
            "intent_encoded", "has_promise", "payment_window_days",
            "message_length", "exclamation_count", "question_count",
            "caps_ratio", "dispute_keywords", "hostile_keywords",
        ]:
            assert feat in importance

#!/usr/bin/env python3
"""
RecoveryBench — Agent Evaluator Tests (Phase 6)

Tests for pipeline/evaluator.py covering:
  - Basic evaluation
  - All 4 rubrics
  - Compliance cross-check with ComplianceChecker
  - Edge cases (empty response, one-word, language mismatch)
  - Consistency testing
  - Intent-specific scoring
"""

import sys
import pytest
from pathlib import Path

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.evaluator import AgentEvaluator, RUBRIC_WEIGHTS, RUBRIC_NAMES


# ─── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def evaluator():
    """Create a single evaluator instance for all tests."""
    return AgentEvaluator()


# ─── Basic Functionality ─────────────────────────────────────────────

class TestBasicFunctionality:
    """Tests for core evaluator functionality."""

    def test_evaluator_initializes(self, evaluator):
        """Evaluator should initialize with a valid backend."""
        assert evaluator.backend is not None
        assert evaluator.backend in ("ollama", "huggingface", "claude", "groq", "rule_based")

    def test_evaluate_returns_required_keys(self, evaluator):
        """Evaluation result must contain all required keys."""
        result = evaluator.evaluate(
            borrower_message="kal kar dunga payment",
            intent="LIKELY_PAY",
            confidence=0.85,
            agent_response="Thank you for confirming. We will follow up next week.",
        )
        required_keys = {
            "intent_accuracy", "tone_score", "compliance_score",
            "escalation_score", "overall_score", "suggested_improvement",
        }
        assert required_keys.issubset(result.keys()), f"Missing keys: {required_keys - set(result.keys())}"

    def test_scores_in_valid_range(self, evaluator):
        """All scores must be in [0, 10]."""
        result = evaluator.evaluate(
            borrower_message="I will pay by next Friday",
            intent="LIKELY_PAY",
            confidence=0.92,
            agent_response="Great, we've noted your commitment. Your EMI of Rs 5000 is due.",
        )
        for rubric in RUBRIC_NAMES:
            assert 0 <= result[rubric] <= 10, f"{rubric} = {result[rubric]} is out of range"
        assert 0 <= result["overall_score"] <= 10

    def test_overall_score_is_weighted_average(self, evaluator):
        """Overall score must equal the weighted average of rubric scores."""
        result = evaluator.evaluate(
            borrower_message="paise nahi hain abhi",
            intent="VAGUE",
            confidence=0.65,
            agent_response="We understand. Please let us know when you can make a payment. Here are your options.",
        )
        expected = round(
            sum(result[k] * w for k, w in RUBRIC_WEIGHTS.items()), 2
        )
        assert abs(result["overall_score"] - expected) < 0.1, (
            f"overall_score={result['overall_score']}, expected={expected}"
        )

    def test_suggested_improvement_is_string(self, evaluator):
        """Suggested improvement must be a non-empty string."""
        result = evaluator.evaluate(
            borrower_message="dekhte hain",
            intent="VAGUE",
            confidence=0.55,
            agent_response="Please pay your dues.",
        )
        assert isinstance(result["suggested_improvement"], str)
        assert len(result["suggested_improvement"]) > 10


# ─── Compliance Detection ────────────────────────────────────────────

class TestComplianceDetection:
    """Tests that the evaluator correctly penalizes compliance violations."""

    def test_legal_threat_scores_low(self, evaluator):
        """Agent threatening legal action must get compliance_score < 5."""
        result = evaluator.evaluate(
            borrower_message="Bhai salary nahi aayi abhi, next week kar dunga",
            intent="LIKELY_PAY",
            confidence=0.88,
            agent_response="Your account is seriously overdue. Pay immediately or legal action will be taken.",
        )
        assert result["compliance_score"] < 5, (
            f"Legal threat should penalize compliance. Got: {result['compliance_score']}"
        )

    def test_police_threat_scores_low(self, evaluator):
        """Agent threatening police must get compliance_score < 5."""
        result = evaluator.evaluate(
            borrower_message="I will pay next month",
            intent="LIKELY_PAY",
            confidence=0.80,
            agent_response="If you don't pay by tomorrow, police will come to your house.",
        )
        assert result["compliance_score"] < 5

    def test_arrest_threat_scores_low(self, evaluator):
        """Agent threatening arrest must get compliance_score < 5."""
        result = evaluator.evaluate(
            borrower_message="Amount galat hai check karo",
            intent="DISPUTE",
            confidence=0.75,
            agent_response="Pay now or we will arrest you. You have no choice.",
        )
        assert result["compliance_score"] < 5

    def test_compliant_message_scores_high(self, evaluator):
        """A fully compliant message should score >= 7 on compliance."""
        result = evaluator.evaluate(
            borrower_message="kal kar dunga bhai",
            intent="LIKELY_PAY",
            confidence=0.90,
            agent_response="We appreciate your commitment to pay. We've noted your timeline. Please feel free to reach out if you need any help with payment options.",
        )
        assert result["compliance_score"] >= 7, (
            f"Compliant message should score high. Got: {result['compliance_score']}"
        )

    def test_harassment_scores_low(self, evaluator):
        """Agent mentioning family/employer should get compliance_score < 5."""
        result = evaluator.evaluate(
            borrower_message="paise nahi hain",
            intent="HIGH_RISK",
            confidence=0.70,
            agent_response="We will inform your employer about your loan default. Your neighbours will also know.",
        )
        assert result["compliance_score"] < 5

    def test_compliance_checker_cross_check(self, evaluator):
        """If ComplianceChecker flags a violation, evaluator must score < 5."""
        try:
            from pipeline.compliance import ComplianceChecker
            checker = ComplianceChecker()
        except Exception:
            pytest.skip("ComplianceChecker not available for cross-check test")

        # Test message that ComplianceChecker would flag
        agent_msg = "If you don't pay by tomorrow police will come to your house"
        checker_result = checker.check(agent_msg)

        if not checker_result["compliant"]:
            eval_result = evaluator.evaluate(
                borrower_message="I can't pay right now",
                intent="HIGH_RISK",
                confidence=0.72,
                agent_response=agent_msg,
            )
            assert eval_result["compliance_score"] < 5, (
                f"ComplianceChecker flagged violation but evaluator gave {eval_result['compliance_score']}"
            )


# ─── Edge Cases ──────────────────────────────────────────────────────

class TestEdgeCases:
    """Tests for edge case handling."""

    def test_empty_agent_response(self, evaluator):
        """Empty agent response should score 1 on all rubrics."""
        result = evaluator.evaluate(
            borrower_message="kal payment kar dunga",
            intent="LIKELY_PAY",
            confidence=0.85,
            agent_response="",
        )
        assert result["intent_accuracy"] <= 2
        assert result["tone_score"] <= 2
        assert result["overall_score"] <= 2

    def test_one_word_response(self, evaluator):
        """One-word response like 'OK' should score low."""
        result = evaluator.evaluate(
            borrower_message="I will pay next week",
            intent="LIKELY_PAY",
            confidence=0.80,
            agent_response="OK",
        )
        assert result["intent_accuracy"] < 4
        assert result["tone_score"] < 4
        assert result["overall_score"] < 5

    def test_very_long_response(self, evaluator):
        """Very long response should not crash."""
        long_response = "We understand your situation. " * 100
        result = evaluator.evaluate(
            borrower_message="dekhte hain",
            intent="VAGUE",
            confidence=0.55,
            agent_response=long_response,
        )
        assert "overall_score" in result
        assert 0 <= result["overall_score"] <= 10

    def test_special_characters(self, evaluator):
        """Response with special characters should not crash."""
        result = evaluator.evaluate(
            borrower_message="😡😡😡 stop calling!!!",
            intent="HIGH_RISK",
            confidence=0.95,
            agent_response="We apologize for the inconvenience. ₹5,000 is your outstanding amount.",
        )
        assert "overall_score" in result

    def test_hindi_borrower_english_agent(self, evaluator):
        """Hindi borrower with English agent response should work fine."""
        result = evaluator.evaluate(
            borrower_message="bhai abhi paisa nahi hai, kal kar dunga",
            intent="LIKELY_PAY",
            confidence=0.88,
            agent_response="Thank you for confirming. We will follow up tomorrow regarding your payment.",
        )
        assert "overall_score" in result
        assert result["overall_score"] > 3  # Should be reasonable, not terrible


# ─── Intent-Specific Scoring ────────────────────────────────────────

class TestIntentSpecificScoring:
    """Tests that scoring aligns with intent context."""

    def test_likely_pay_good_response(self, evaluator):
        """Good response to LIKELY_PAY borrower should score high."""
        result = evaluator.evaluate(
            borrower_message="salary aane do, next week kar dunga payment",
            intent="LIKELY_PAY",
            confidence=0.90,
            agent_response="Thank you for confirming your commitment. We've noted your payment timeline for next week. Your outstanding amount is ₹5,000. Please feel free to reach out if you need help.",
        )
        assert result["overall_score"] >= 6

    def test_likely_pay_bad_response(self, evaluator):
        """Threatening response to LIKELY_PAY borrower should score low."""
        result = evaluator.evaluate(
            borrower_message="salary aane do, next week kar dunga payment",
            intent="LIKELY_PAY",
            confidence=0.90,
            agent_response="This is your FINAL warning. Pay immediately or legal action will be taken. We will arrest you.",
        )
        assert result["overall_score"] < 4
        assert result["compliance_score"] < 5

    def test_dispute_good_response(self, evaluator):
        """Good response to DISPUTE should acknowledge and offer verification."""
        result = evaluator.evaluate(
            borrower_message="yeh amount galat hai, check karo records",
            intent="DISPUTE",
            confidence=0.78,
            agent_response="We take your concern seriously. Let us review your records and verify the amount. Our team will investigate and get back to you within 48 hours.",
        )
        assert result["intent_accuracy"] >= 6

    def test_high_risk_with_escalation(self, evaluator):
        """HIGH_RISK with proper escalation should score well on escalation."""
        result = evaluator.evaluate(
            borrower_message="STOP CALLING ME! I'll report you to consumer forum!",
            intent="HIGH_RISK",
            confidence=0.95,
            agent_response="I understand your frustration, and I apologize for any inconvenience. Let me connect you with our senior resolution specialist who can better address your concerns.",
        )
        assert result["escalation_score"] >= 7

    def test_high_risk_without_escalation(self, evaluator):
        """HIGH_RISK without escalation should score lower on escalation."""
        result = evaluator.evaluate(
            borrower_message="band karo phone! harass mat karo!",
            intent="HIGH_RISK",
            confidence=0.92,
            agent_response="Your EMI is overdue. Please pay soon.",
        )
        assert result["escalation_score"] < 6

    def test_needs_reminder_with_details(self, evaluator):
        """NEEDS_REMINDER with specific details should score well."""
        result = evaluator.evaluate(
            borrower_message="haan yaad hai, kitna dena hai?",
            intent="NEEDS_REMINDER",
            confidence=0.82,
            agent_response="Your outstanding EMI amount is ₹5,000. The due date was June 1st. You can pay via UPI, NEFT, or visit our website. Would you like help setting up a payment?",
        )
        assert result["intent_accuracy"] >= 5


# ─── Consistency Testing ─────────────────────────────────────────────

class TestConsistencyTesting:
    """Tests for the consistency testing feature."""

    def test_consistency_test_runs(self, evaluator):
        """Consistency test should run without errors."""
        test_cases = [
            {
                "borrower_message": "kal kar dunga payment",
                "intent": "LIKELY_PAY",
                "confidence": 0.85,
                "agent_response": "Thank you for confirming. We will follow up.",
            },
        ]
        result = evaluator.run_consistency_test(test_cases, runs=2)
        assert "per_case_results" in result
        assert "aggregate_variance" in result
        assert "flags" in result
        assert len(result["per_case_results"]) == 1

    def test_rule_based_has_zero_variance(self, evaluator):
        """Rule-based backend should produce identical results across runs."""
        if evaluator.backend != "rule_based":
            pytest.skip("Test only relevant for rule_based backend")

        test_cases = [
            {
                "borrower_message": "I will pay tomorrow",
                "intent": "LIKELY_PAY",
                "confidence": 0.90,
                "agent_response": "Please pay immediately or face consequences.",
            },
        ]
        result = evaluator.run_consistency_test(test_cases, runs=3)
        for rubric, var in result["aggregate_variance"].items():
            assert var == 0.0, f"Rule-based should have zero variance. {rubric} variance = {var}"


# ─── Evaluator Metadata ─────────────────────────────────────────────

class TestEvaluatorMetadata:
    """Tests for evaluator stats and metadata."""

    def test_get_stats(self, evaluator):
        """get_stats should return valid metadata."""
        stats = evaluator.get_stats()
        assert "backend" in stats
        assert "backend_model" in stats
        assert "api_calls" in stats

    def test_get_cost_per_1000(self, evaluator):
        """get_cost_per_1000 should return a string."""
        cost = evaluator.get_cost_per_1000()
        assert isinstance(cost, str)
        assert len(cost) > 0

    def test_repr(self, evaluator):
        """repr should return informative string."""
        r = repr(evaluator)
        assert "AgentEvaluator" in r
        assert evaluator.backend in r


# ─── Compliance Consistency Check ────────────────────────────────────

class TestComplianceConsistency:
    """
    If ComplianceChecker flags a violation, evaluator compliance_score
    must be below 5. Test with multiple violation types.
    """

    VIOLATION_MESSAGES = [
        "If you don't pay, police will come to your house",
        "We will tell your employer about your loan default",
        "You are a fraud and a cheat, pay up now",
        "Borrow from your relatives to pay us back immediately",
        "A fake court order has been issued in your name",
    ]

    @pytest.mark.parametrize("agent_msg", VIOLATION_MESSAGES)
    def test_violation_scores_below_5(self, evaluator, agent_msg):
        """Each known violation must score compliance < 5."""
        result = evaluator.evaluate(
            borrower_message="I can't pay right now",
            intent="HIGH_RISK",
            confidence=0.75,
            agent_response=agent_msg,
        )
        assert result["compliance_score"] < 5, (
            f"Agent msg '{agent_msg[:50]}...' should score compliance < 5, "
            f"got {result['compliance_score']}"
        )
